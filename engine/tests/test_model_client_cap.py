"""Unit tests for model_client response size capping and normal requests.

No real network calls are made.
"""
import json
import socket
import pytest
from unittest.mock import MagicMock, patch

from sandbox.model_client import call_user_model

# Mock DNS map
_NAME_MAP = {
    "api.openai.com": "104.18.32.7",
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


def test_model_client_response_too_large():
    """Verify that responses exceeding max_response_bytes return (False, 'response too large')."""
    endpoint = "https://api.openai.com/v1"

    # We yield chunks that total 30 bytes, but set max_response_bytes=15
    chunks = [b"a" * 10, b"b" * 15, b"c" * 5]

    with patch("requests.Session.send") as mock_send:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = chunks
        mock_send.return_value = mock_resp

        ok, res = call_user_model(
            endpoint, "test-key", "test-prompt", max_response_bytes=15
        )
        assert ok is False
        assert res == "response too large"
        # Ensure that response.close() was called to abort downloading
        mock_resp.close.assert_called()


def test_model_client_normal_request():
    """Verify that a normal successful path returns (True, content) and makes a standard request."""
    endpoint = "https://api.openai.com/v1"

    with patch("requests.Session.send") as mock_send:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [
            json.dumps({
                "choices": [{"message": {"content": "normal-response"}}]
            }).encode("utf-8")
        ]
        mock_send.return_value = mock_resp

        ok, res = call_user_model(endpoint, "test-key", "test-prompt")
        assert ok is True
        assert res == "normal-response"
        mock_send.assert_called_once()
