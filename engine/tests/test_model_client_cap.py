"""Unit tests for model_client response size capping and connection pinning.

No real network calls are made.
"""
import json
import socket
import pytest
from unittest.mock import MagicMock, patch

from sandbox.model_client import call_user_model
import urllib3.util.connection as urllib3_connection

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


def test_model_client_pins_connection():
    """Verify that the socket connection is made to the pinned IP address, not the hostname."""
    endpoint = "https://api.openai.com/v1"

    called_addresses = []

    def mock_create_connection(address, *args, **kwargs):
        called_addresses.append(address)
        raise ConnectionRefusedError("Simulated connection refusal")

    with patch("urllib3.util.connection.create_connection", new=mock_create_connection):
        ok, res = call_user_model(endpoint, "test-key", "test-prompt")

    assert ok is False
    # Verify that create_connection was called with the pinned IP ('104.18.32.7', 443)
    # and NOT the hostname ('api.openai.com', 443)
    assert len(called_addresses) > 0
    assert called_addresses[0] == ("104.18.32.7", 443)
