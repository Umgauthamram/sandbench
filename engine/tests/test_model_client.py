"""Unit tests for model_client.py.

Tests URL normalization, response size capping via chunked streaming,
redirection rejection, and error handling. Uses mocking to avoid real network calls.
"""
import json
import socket
import pytest
from unittest.mock import MagicMock, patch

from sandbox.model_client import call_user_model


# Mock DNS to resolve cleanly for test hosts
_NAME_MAP = {
    "api.openai.com": "104.18.32.7",
    "badhost.com": "104.18.32.8",
}

def _fake_getaddrinfo(host, *args, **kwargs):
    if host in _NAME_MAP:
        ip = _NAME_MAP[host]
        family = socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (ip, 0))]
    raise socket.gaierror("Name or service not known")


@pytest.fixture(autouse=True)
def _patch_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)


def test_url_normalization():
    """Verify that user-supplied endpoints are correctly normalized to /chat/completions."""
    # Define test cases: (input_endpoint, expected_called_url)
    test_cases = [
        ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
        ("https://api.openai.com/v1/", "https://api.openai.com/v1/chat/completions"),
        ("https://api.openai.com", "https://api.openai.com/v1/chat/completions"),
        ("https://api.openai.com/", "https://api.openai.com/v1/chat/completions"),
        ("https://api.openai.com/chat/completions", "https://api.openai.com/chat/completions"),
        ("https://api.openai.com/chat/completions/", "https://api.openai.com/chat/completions"),
    ]

    for endpoint, expected_url in test_cases:
        with patch("requests.Session.send") as mock_send:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.iter_content.return_value = [
                json.dumps({
                    "choices": [{"message": {"content": "hello"}}]
                }).encode("utf-8")
            ]
            mock_send.return_value = mock_resp

            ok, res = call_user_model(endpoint, "test-key", "test-prompt")
            assert ok is True
            assert res == "hello"

            # Verify the exact URL that was posted to
            mock_send.assert_called_once()
            called_req = mock_send.call_args[0][0]
            assert called_req.url == expected_url


def test_response_size_capping():
    """Verify that responses exceeding max_response_bytes are aborted and rejected."""
    endpoint = "https://api.openai.com/v1"

    # 1. Exact limit response: should succeed
    max_bytes = 20
    # Mock return body that parses as valid JSON choices structure within max_bytes
    valid_json = {"choices": [{"message": {"content": "x"}}]}
    valid_bytes = json.dumps(valid_json).encode("utf-8")

    with patch("requests.Session.send") as mock_send:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [valid_bytes]
        mock_send.return_value = mock_resp

        ok, res = call_user_model(
            endpoint, "test-key", "test-prompt", max_response_bytes=len(valid_bytes)
        )
        assert ok is True
        assert res == "x"

    # 2. Exceed limit: should fail before downloading the whole content
    # Let's yield chunks such that total size exceeds the limit.
    chunks = [b"a" * 10, b"b" * 15, b"c" * 5]  # total 30 bytes

    with patch("requests.Session.send") as mock_send:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Mocking a generator/iterable for chunks
        mock_resp.iter_content.return_value = chunks
        mock_send.return_value = mock_resp

        ok, res = call_user_model(
            endpoint, "test-key", "test-prompt", max_response_bytes=15
        )
        assert ok is False
        assert "response too large" in res


def test_reject_redirects():
    """Verify we return an error and do not follow redirects (to protect against SSRF redirect bypasses)."""
    endpoint = "https://api.openai.com/v1"

    with patch("requests.Session.send") as mock_send:
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_send.return_value = mock_resp

        ok, res = call_user_model(endpoint, "test-key", "test-prompt")
        assert ok is False
        assert "redirects not allowed" in res


def test_error_scrubbing_and_exceptions():
    """Verify that exceptions are caught, and api keys/headers are never leaked in logs/verdicts."""
    endpoint = "https://api.openai.com/v1"

    # Simulating a connection error
    with patch("requests.Session.send", side_effect=Exception("sensitive internal details or keys like test-key")):
        ok, res = call_user_model(endpoint, "test-key", "test-prompt")
        assert ok is False
        # Should scrub details and only return Exception type name
        assert "error: Exception" in res
        assert "test-key" not in res
