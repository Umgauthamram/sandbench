import socket

import pytest

from solution import is_safe_outbound_url


def _gai(ip):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (ip, 0))]


@pytest.mark.parametrize(
    ("url", "ip"),
    [
        ("http://localhost", "127.0.0.1"),
        ("http://metadata.google.internal", "169.254.169.254"),
        ("http://internal.example", "10.0.0.9"),
        ("http://v6-local.example", "::1"),
    ],
)
def test_rejects_non_public_resolved_hosts(monkeypatch, url, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: _gai(ip))
    assert is_safe_outbound_url(url) is False


def test_allows_public_https(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: _gai("104.18.32.7"))
    assert is_safe_outbound_url("https://api.example.com/v1") is True


def test_rejects_non_http_schemes(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: _gai("104.18.32.7"))
    assert is_safe_outbound_url("file:///etc/passwd") is False
