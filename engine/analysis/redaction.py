"""Redaction helpers for training traces and exported datasets."""
from __future__ import annotations

import re
from typing import Any

SECRET_PATTERNS = [
    # Query-string secrets, e.g. ?key=... or &access_token=...
    (
        re.compile(
            r"(?i)([?&](?:api[_-]?key|key|token|access[_-]?token|client[_-]?secret)=)([^&\s]+)"
        ),
        r"\1[REDACTED]",
    ),
    # Authorization headers and bearer snippets.
    (
        re.compile(r"(?i)\b(authorization\s*[:=]\s*bearer\s+)([A-Za-z0-9._~+/=-]+)"),
        r"\1[REDACTED]",
    ),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    # Common provider keys.
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bAQ\.[0-9A-Za-z_-]{12,}\b"), "[REDACTED_API_KEY]"),
    # Environment-style secret assignments.
    (
        re.compile(
            r"(?i)\b((?:OPENAI|GEMINI|ANTHROPIC|GROQ|HF|HUGGINGFACE|MODEL)_?(?:API_)?KEY\s*=\s*)(\S+)"
        ),
        r"\1[REDACTED]",
    ),
]


def redact_sensitive_text(value: str) -> str:
    """Redact likely API keys, bearer tokens, and secret query parameters."""
    redacted = value
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def sanitize_trace(value: Any) -> Any:
    """Recursively sanitize a trace-like JSON value."""
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [sanitize_trace(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_trace(item) for key, item in value.items()}
    return value
