import json
import pytest
from unittest.mock import patch, MagicMock
import requests

from adapters.registry import create_adapter, registry
from adapters.openai_compat import OpenAICompatAdapter, estimate_openai_cost
from adapters.gemini import GeminiAdapter, estimate_gemini_cost
from adapters.base import GenerationResult

def test_registry_factory():
    # Test creation of Gemini adapter
    gemini = create_adapter("gemini", "test-key", "gemini-2.5-flash")
    assert isinstance(gemini, GeminiAdapter)
    assert gemini.name == "gemini-2.5-flash"
    assert gemini.api_key == "test-key"

    # Test creation of OpenAI compat adapter
    openai = create_adapter("openai", "test-key", "gpt-4o")
    assert isinstance(openai, OpenAICompatAdapter)
    assert openai.name == "gpt-4o"
    assert openai.provider == "openai"

    # Test fallback to OpenAICompat for other providers
    groq = create_adapter("groq", "test-key", "llama3")
    assert isinstance(groq, OpenAICompatAdapter)
    assert groq.provider == "groq"

def test_estimate_openai_cost():
    assert estimate_openai_cost("gpt-4o", 1000, 2000) == (1.0 * 0.00500 + 2.0 * 0.01500)
    assert estimate_openai_cost("gpt-4o-mini", 1000, 2000) == (1.0 * 0.00015 + 2.0 * 0.00060)
    assert estimate_openai_cost("unknown-model", 1000, 2000) == (1.0 * 0.00015 + 2.0 * 0.00060)

def test_estimate_gemini_cost():
    assert estimate_gemini_cost("gemini-2.5-flash", 1000000, 2000000) == (1.0 * 0.075 + 2.0 * 0.30)
    assert estimate_gemini_cost("gemini-1.5-pro", 1000000, 2000000) == (1.0 * 1.25 + 2.0 * 5.00)
    assert estimate_gemini_cost("unknown-gemini", 1000000, 2000000) == (1.0 * 0.075 + 2.0 * 0.30)

@patch("sandbox.ssrf_guard.resolve_safe")
@patch("requests.Session.post")
def test_openai_compat_generate_success(mock_post, mock_resolve):
    mock_resolve.return_value = ("api.openai.com", ["104.18.32.7"], "ok")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [
        json.dumps({
            "choices": [{"message": {"content": '{"review_text": "good", "patch": "diff"}'}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300
            }
        }).encode("utf-8")
    ]
    mock_post.return_value = mock_resp

    adapter = OpenAICompatAdapter(name="gpt-4o", api_key="sk-test")
    res = adapter.generate("test-prompt")
    
    assert res.ok is True
    assert res.content == '{"review_text": "good", "patch": "diff"}'
    assert res.usage["prompt_tokens"] == 100
    assert res.usage["completion_tokens"] == 200
    assert res.usage["estimated_cost"] > 0
    assert adapter.request_count == 1
    assert adapter.total_prompt_tokens == 100

@patch("sandbox.ssrf_guard.resolve_safe")
@patch("requests.Session.post")
def test_openai_compat_generate_failures(mock_post, mock_resolve):
    # 1. SSRF Rejection
    mock_resolve.return_value = (None, [], "unsafe IP")
    adapter = OpenAICompatAdapter(name="gpt-4o", api_key="sk-test")
    res = adapter.generate("prompt")
    assert res.ok is False
    assert "endpoint rejected" in res.error
    assert adapter.error_categories["SSRFRejection"] == 1

    # 2. Redirect
    mock_resolve.return_value = ("api.openai.com", ["104.18.32.7"], "ok")
    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_post.return_value = mock_resp
    res = adapter.generate("prompt")
    assert res.ok is False
    assert "redirects not allowed" in res.error
    assert adapter.error_categories["HTTPError"] == 1

    # 3. Timeout
    mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
    res = adapter.generate("prompt")
    assert res.ok is False
    assert "Timeout" in res.error
    assert adapter.error_categories["Timeout"] == 1

@patch("sandbox.ssrf_guard.resolve_safe")
@patch("requests.Session.post")
def test_gemini_generate_success(mock_post, mock_resolve):
    mock_resolve.return_value = ("generativelanguage.googleapis.com", ["142.250.190.46"], "ok")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [
        json.dumps({
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"review_text": "gemini", "patch": "diff"}'}]
                }
            }],
            "usageMetadata": {
                "promptTokenCount": 50,
                "candidatesTokenCount": 150,
                "totalTokenCount": 200
            }
        }).encode("utf-8")
    ]
    mock_post.return_value = mock_resp

    adapter = GeminiAdapter(name="gemini-2.5-flash", api_key="gem-test")
    res = adapter.generate("test-prompt")
    
    assert res.ok is True
    assert "gemini" in res.content
    assert res.usage["prompt_tokens"] == 50
    assert res.usage["completion_tokens"] == 150
    assert adapter.request_count == 1
    assert adapter.total_prompt_tokens == 50

def test_registry_statistics():
    reg = registry
    # Reset adapters list in registry
    reg.adapters = []

    # Create two adapters and generate mocks
    a1 = reg.create_adapter("openai", "k1", "gpt-4o")
    a2 = reg.create_adapter("gemini", "k2", "gemini-2.5-flash")

    # Simulate some stats
    a1.request_count = 5
    a1.total_prompt_tokens = 500
    a1.total_completion_tokens = 1000
    a1.total_estimated_cost = 0.02
    a1.error_categories["HTTPError"] = 1

    a2.request_count = 3
    a2.total_prompt_tokens = 300
    a2.total_completion_tokens = 700
    a2.total_estimated_cost = 0.005
    a2.error_categories["Timeout"] = 1

    stats = reg.get_usage_statistics()
    assert stats["total_calls"] == 8
    assert stats["total_prompt_tokens"] == 800
    assert stats["total_completion_tokens"] == 1700
    assert stats["total_cost"] == 0.025
    assert stats["error_rate"] == 0.25  # 2 errors out of 8 calls
