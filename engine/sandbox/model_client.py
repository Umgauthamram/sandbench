"""Host-side client for a user-supplied, OpenAI-compatible model endpoint.

Phase 2 (model evaluation): the user brings their own /chat/completions
endpoint + API key. SandBench calls it HOST-SIDE only — the sandbox stays
network_mode=none and never sees the endpoint or key.

KEY SAFETY: the api_key, the Authorization header, and the raw endpoint are
NEVER logged or returned in any string. On any error we surface only the
exception type name. This mirrors the error-scrubbing in sandbox/review.py.

DNS REBINDING NOTE:
The authoritative defense against DNS rebinding (TOCTOU) in production is a
NETWORK EGRESS policy on the host (firewall/iptables blocking outbound to
private/link-local/metadata ranges). The ssrf_guard validation here catches the
obvious cases and gives good error UX; it is not rebinding-proof on its own,
by design — the network policy is.
"""
import json
import logging

import requests

from sandbox import ssrf_guard

logger = logging.getLogger(__name__)


def call_user_model(
    endpoint: str,
    api_key: str,
    prompt: str,
    timeout_s: int = 30,
    max_response_bytes: int = 262144,
    model_name: str = "user-model",
) -> tuple[bool, str]:
    """Call the user's model endpoint. Returns (ok, content) or (False, safe_error).

    Performs an SSRF check BEFORE any network activity; on rejection makes no
    request at all.
    """
    # 1. SSRF guard & DNS resolution — resolved on host to prevent obvious SSRF cases.
    hostname, validated_ips, reason = ssrf_guard.resolve_safe(endpoint)
    if not hostname or not validated_ips:
        return (False, f"endpoint rejected: {reason}")

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
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    # 3. Dispatches the request via standard Session to support CDN-fronted hosts
    session = requests.Session()

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