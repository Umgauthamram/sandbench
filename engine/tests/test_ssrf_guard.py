"""Unit tests for the SSRF guard. No network, no Docker.

socket.getaddrinfo is monkeypatched so the DNS resolution is offline and
deterministic. The guard's real defense is the IP check on the RESOLVED
address, so these tests drive that check directly.
"""
import ipaddress
import socket

import pytest

from sandbox.ssrf_guard import is_safe_url


# Hostnames that are not literal IPs resolve via this map.
_NAME_MAP = {
    "localhost": "127.0.0.1",
    "private-only.example.com": "10.4.5.6",
    "api.openai.com": "104.18.32.7",
}


def _gai(ip: str):
    """Build a socket.getaddrinfo-shaped result for a single IP."""
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (ip, 0))]


def _fake_getaddrinfo(host, *args, **kwargs):
    """Resolve literal IPs to themselves; named hosts via _NAME_MAP."""
    try:
        ipaddress.ip_address(host)
        return _gai(host)
    except ValueError:
        return _gai(_NAME_MAP[host])


@pytest.fixture(autouse=True)
def _patch_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)


REJECT_URLS = [
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata (link-local)
    "http://127.0.0.1:6379",                      # loopback
    "http://localhost",                           # resolves to 127.0.0.1
    "http://10.0.0.5",                            # private 10/8
    "http://192.168.1.1",                         # private 192.168/16
    "http://172.16.0.9",                          # private 172.16/12
    "file:///etc/passwd",                         # scheme not allowed
    "ftp://example.com",                          # scheme not allowed
    "http://private-only.example.com",            # resolves only to 10.x
]


@pytest.mark.parametrize("url", REJECT_URLS)
def test_rejects_unsafe_urls(url):
    ok, reason = is_safe_url(url)
    assert ok is False, f"expected rejection for {url} (reason={reason!r})"


def test_allows_public_https():
    ok, reason = is_safe_url("https://api.openai.com")
    assert ok is True, f"expected allow, got reason={reason!r}"