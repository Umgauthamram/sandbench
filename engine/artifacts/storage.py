"""Artifact storage backends.

Phase 4 starts with local filesystem storage for development. The interface is
small enough that an S3/R2 backend can replace it without changing the worker.
"""
from __future__ import annotations

import hmac
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from config import ARTIFACT_SIGNING_SECRET, ARTIFACT_STORAGE_DIR


@dataclass(frozen=True)
class SignedArtifactURL:
    path: str
    expires_at: int
    url: str


class LocalArtifactStorage:
    """Local filesystem artifact storage."""

    def __init__(self, root: str | None = None, signing_secret: str | None = None):
        self.root = _resolve_root(root or ARTIFACT_STORAGE_DIR)
        self.signing_secret = signing_secret or ARTIFACT_SIGNING_SECRET
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        safe_run_id = "".join(ch for ch in run_id if ch.isalnum() or ch in ("_", "-"))
        if not safe_run_id:
            safe_run_id = "run"
        return self.root / safe_run_id

    def signed_url(self, bundle_hash: str, relative_path: str, ttl_seconds: int = 3600) -> SignedArtifactURL:
        expires_at = int(time.time()) + ttl_seconds
        payload = f"{bundle_hash}:{relative_path}:{expires_at}".encode("utf-8")
        signature = hmac.new(
            self.signing_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        query = urlencode({"path": relative_path, "expires": expires_at, "sig": signature})
        return SignedArtifactURL(
            path=relative_path,
            expires_at=expires_at,
            url=f"local-artifact://{bundle_hash}?{query}",
        )


def _resolve_root(root: str) -> Path:
    path = Path(root)
    if path.is_absolute():
        return path
    engine_dir = Path(__file__).resolve().parents[1]
    return (engine_dir / path).resolve()
