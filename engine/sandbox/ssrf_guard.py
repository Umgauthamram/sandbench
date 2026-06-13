"""SSRF guard for host-side outbound calls (Phase 2 model evaluation).

The ONLY outbound network call in SandBench is the host-side call to a user's
own model endpoint (see sandbox/model_client.py). Before that call is made, the
endpoint is validated here.

The real defense is NOT a regex on the URL string — a hostname can resolve to
127.0.0.1 or to the cloud metadata IP (169.254.169.254). Instead we resolve the
hostname via DNS and reject if ANY resolved IP is non-public. This opens no
connection.
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def resolve_safe(url: str) -> tuple[str | None, list[str], str]:
    """Resolve the URL's hostname and validate its IP addresses.

    Allows only http/https URLs whose hostname resolves EXCLUSIVELY to public
    IP addresses. Blocks loopback, private, link-local (incl. the cloud
    metadata range 169.254.0.0/16 and fe80::/10), multicast, reserved and
    unspecified addresses.

    Returns:
        (hostname, [validated_public_ips], "ok") on success.
        (None, [], error_reason) on failure or rejection.
    """
    try:
        try:
            parsed = urlparse(url)
        except Exception:
            return (None, [], "validation error")

        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            return (None, [], "scheme not allowed")

        host = parsed.hostname
        if not host:
            return (None, [], "no host")

        # Resolve ALL addresses for the host. No connection is opened.
        try:
            infos = socket.getaddrinfo(host, None)
        except Exception:
            return (None, [], "host did not resolve to a public address")

        validated_ips = []
        found_public = False
        for info in infos:
            sockaddr = info[4]
            if not sockaddr:
                continue
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) so the checks
            # below see the real IPv4 address rather than a "public" v6 wrapper.
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                ip = ip.ipv4_mapped

            if (
                ip.is_loopback
                or ip.is_private
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                return (None, [], "host resolves to a non-public address")

            found_public = True
            if ip_str not in validated_ips:
                validated_ips.append(ip_str)

        if not found_public or not validated_ips:
            return (None, [], "host did not resolve to a public address")

        return (host, validated_ips, "ok")
    except Exception:
        # Fail closed on anything unexpected; never leak details, never raise.
        return (None, [], "validation error")


def is_safe_url(url: str) -> tuple[bool, str]:
    """Return (ok, reason). Never raises.

    Kept for backwards-compatibility. Thin wrapper over resolve_safe().
    """
    host, ips, reason = resolve_safe(url)
    if host is not None and len(ips) > 0:
        return (True, "ok")
    return (False, reason)