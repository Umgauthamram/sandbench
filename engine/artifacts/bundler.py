"""Replayable artifact bundle creation for completed SandBench runs."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from analysis.redaction import sanitize_trace
from artifacts.storage import LocalArtifactStorage


MAX_TEXT_ARTIFACT_CHARS = 65536


@dataclass(frozen=True)
class ArtifactBundle:
    run_id: str
    bundle_dir: str
    bundle_hash: str
    artifact_hashes: Dict[str, str] = field(default_factory=dict)
    signed_urls: Dict[str, str] = field(default_factory=dict)


def create_artifact_bundle(
    *,
    run_id: str,
    manifest: Dict[str, Any],
    submitted_files: Optional[Mapping[str, str]] = None,
    stdout: str = "",
    stderr: str = "",
    score_breakdown: Optional[Dict[str, Any]] = None,
    flags: Optional[list[Dict[str, Any]]] = None,
    repair_patch: str = "",
    storage: Optional[LocalArtifactStorage] = None,
) -> ArtifactBundle:
    """Create a sealed local artifact bundle and return its integrity hashes."""
    storage = storage or LocalArtifactStorage()
    bundle_dir = storage.run_dir(run_id)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    artifact_hashes: Dict[str, str] = {}

    _write_json(bundle_dir / "manifest.json", sanitize_trace(manifest), artifact_hashes, "manifest.json")
    _write_text(bundle_dir / "stdout.txt", stdout[:MAX_TEXT_ARTIFACT_CHARS], artifact_hashes, "stdout.txt")
    _write_text(bundle_dir / "stderr.txt", stderr[:MAX_TEXT_ARTIFACT_CHARS], artifact_hashes, "stderr.txt")
    _write_json(bundle_dir / "score_breakdown.json", score_breakdown or {}, artifact_hashes, "score_breakdown.json")
    _write_json(bundle_dir / "flags.json", flags or [], artifact_hashes, "flags.json")
    if repair_patch:
        _write_text(bundle_dir / "repair_patch.diff", repair_patch[:MAX_TEXT_ARTIFACT_CHARS], artifact_hashes, "repair_patch.diff")

    submitted_root = bundle_dir / "submitted_code"
    submitted_root.mkdir(exist_ok=True)
    for container_path, contents in (submitted_files or {}).items():
        rel_path = _safe_submission_path(container_path)
        target = submitted_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_text(
            target,
            str(sanitize_trace(contents))[:MAX_TEXT_ARTIFACT_CHARS],
            artifact_hashes,
            f"submitted_code/{rel_path.as_posix()}",
        )

    bundle_hash = _bundle_hash(artifact_hashes)
    _write_json(
        bundle_dir / "bundle.json",
        {"run_id": run_id, "bundle_hash": bundle_hash, "artifact_hashes": artifact_hashes},
        artifact_hashes,
        "bundle.json",
    )

    signed_urls = {
        "manifest": storage.signed_url(bundle_hash, "manifest.json").url,
        "bundle": storage.signed_url(bundle_hash, "bundle.json").url,
    }

    return ArtifactBundle(
        run_id=run_id,
        bundle_dir=str(bundle_dir),
        bundle_hash=bundle_hash,
        artifact_hashes=dict(artifact_hashes),
        signed_urls=signed_urls,
    )


def _write_json(path: Path, data: Any, hashes: Dict[str, str], name: str) -> None:
    raw = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    _write_text(path, raw, hashes, name)


def _write_text(path: Path, text: str, hashes: Dict[str, str], name: str) -> None:
    sanitized = str(sanitize_trace(text))
    path.write_text(sanitized, encoding="utf-8")
    hashes[name] = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()


def _bundle_hash(artifact_hashes: Dict[str, str]) -> str:
    payload = json.dumps(artifact_hashes, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_submission_path(container_path: str) -> Path:
    normalized = container_path.replace("\\", "/").strip("/")
    if normalized.startswith("workspace/"):
        normalized = normalized[len("workspace/"):]
    if not normalized:
        normalized = "solution.txt"
    parts = [part for part in normalized.split("/") if part and part not in (".", "..")]
    if not parts:
        parts = ["solution.txt"]
    return Path(*parts)
