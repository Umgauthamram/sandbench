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
    from adapters.openai_compat import OpenAICompatAdapter
    adapter = OpenAICompatAdapter(name=model_name, api_key=api_key, endpoint=endpoint)
    res = adapter.generate(
        prompt=prompt,
        timeout_s=timeout_s,
        max_response_bytes=max_response_bytes,
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    if res.ok:
        return (True, res.content)
    else:
        return (False, res.error or "error")