"""Host-side client for a user-supplied, OpenAI-compatible model endpoint.

Phase 2 (model evaluation): the user brings their own /chat/completions
endpoint + API key. SandBench calls it HOST-SIDE only — the sandbox stays
network_mode=none and never sees the endpoint or key.

KEY SAFETY: the api_key, the Authorization header, and the raw endpoint are
NEVER logged or returned in any string. On any error we surface only the
exception type name. This mirrors the error-scrubbing in sandbox/review.py.
"""
import json
import logging
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter

from sandbox import ssrf_guard

logger = logging.getLogger(__name__)


class PinnedIPAdapter(HTTPAdapter):
    """Custom HTTPAdapter that forces socket connections to a pinned IP address.

    Ensures that DNS is resolved only once (during ssrf_guard check) and prevents
    TOCTOU / DNS-rebinding attacks by bypass-resolving the hostname to the pinned IP.
    For HTTPS, it preserves SNI and verifies the certificate against the original hostname.
    """
    def __init__(self, pinned_ip: str, original_host: str, *args, **kwargs):
        self.pinned_ip = pinned_ip
        self.original_host = original_host
        super().__init__(*args, **kwargs)

    def get_connection(self, url, proxies=None):
        conn = super().get_connection(url, proxies)
        conn.host = self.pinned_ip
        return conn

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        conn = super().get_connection_with_tls_context(request, verify, proxies, cert)
        conn.host = self.pinned_ip
        if conn.scheme == "https":
            conn.assert_hostname = self.original_host
            if not conn.conn_kw:
                conn.conn_kw = {}
            conn.conn_kw["server_hostname"] = self.original_host
        return conn


def call_user_model(
    endpoint: str,
    api_key: str,
    prompt: str,
    timeout_s: int = 30,
    max_response_bytes: int = 262144,
) -> tuple[bool, str]:
    """Call the user's model endpoint. Returns (ok, content) or (False, safe_error).

    Performs an SSRF check and pins DNS resolution BEFORE any network activity;
    on rejection makes no request at all.
    """
    # 1. SSRF guard & DNS resolution — resolved once on host to prevent DNS rebinding.
    hostname, validated_ips, reason = ssrf_guard.resolve_safe(endpoint)
    if not hostname or not validated_ips:
        return (False, f"endpoint rejected: {reason}")

    pinned_ip = validated_ips[0]

    # 2. Normalize to an OpenAI-compatible completions URL.
    base = endpoint.rstrip("/")
    if base.endswith("/chat/completions"):
        url = base
    elif base.endswith("/v1"):
        url = base + "/chat/completions"
    else:
        url = base + "/v1/chat/completions"

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": "user-model",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    # 3. Pin connection to the resolved IP
    session = requests.Session()
    adapter = PinnedIPAdapter(pinned_ip=pinned_ip, original_host=hostname)
    parsed = urlparse(endpoint)
    scheme = (parsed.scheme or "https").lower()
    session.mount(f"{scheme}://{hostname}", adapter)

    try:
        response = session.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout_s,
            allow_redirects=False,
            stream=True,  # Stream content to enforce limit before reading all into memory
        )

        # Do not follow redirects — they could point at an internal address.
        if 300 <= response.status_code < 400:
            return (False, "redirects not allowed")

        response.raise_for_status()

        # Cap the body we read/parse incrementally.
        content_bytes = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=8192):
                content_bytes.extend(chunk)
                if len(content_bytes) > max_response_bytes:
                    response.close()
                    return (False, "response too large")
        finally:
            response.close()

        body = bytes(content_bytes)
        data = json.loads(body)

        choices = data.get("choices", [])
        if not choices:
            return (False, "model response had no choices")

        content = choices[0].get("message", {}).get("content", "")
        return (True, content)

    except Exception as e:
        # NEVER log the key, header, endpoint, or response body.
        logger.error("user model call failed: %s", type(e).__name__)
        return (False, f"error: {type(e).__name__}")