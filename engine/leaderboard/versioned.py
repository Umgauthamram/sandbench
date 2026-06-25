"""Versioned leaderboard and immutable submission records."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class VersionedLeaderboardEntry:
    rank: int
    user: str
    user_id: str
    submission_id: str
    submission_hash: str
    run_id: str
    suite: str
    task_id: str
    task_title: str
    task_version: str
    score: float
    verdict: str
    created_at: str
    artifact_bundle_hash: str = ""


def submission_hash(payload: Dict[str, Any], previous_hash: str = "") -> str:
    record = {"previous_hash": previous_hash, "payload": payload}
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_versioned_leaderboard(
    redis_client: Any,
    *,
    run_id: str,
    user: str,
    user_id: str,
    submission_id: str,
    suite: str,
    task_id: str,
    task_title: str,
    task_version: str,
    score: float,
    verdict: str,
    created_at: str,
    artifact_bundle_hash: str = "",
) -> VersionedLeaderboardEntry:
    """Update versioned score/history keys and store an immutable submission record."""
    score_key = f"sandbench:lb:{suite}:{task_version}:scores"
    history_key = f"sandbench:lb:{suite}:{task_version}:history:{user_id or user}"
    latest_hash_key = f"sandbench:submission:latest:{user_id or user}"

    previous_hash = redis_client.get(latest_hash_key) or ""
    payload = {
        "run_id": run_id,
        "user": user,
        "user_id": user_id,
        "submission_id": submission_id,
        "suite": suite,
        "task_id": task_id,
        "task_title": task_title,
        "task_version": task_version,
        "score": score,
        "verdict": verdict,
        "created_at": created_at,
        "artifact_bundle_hash": artifact_bundle_hash,
    }
    sub_hash = submission_hash(payload, previous_hash)
    immutable_record = {
        "hash": sub_hash,
        "previous_hash": previous_hash,
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        **payload,
    }
    redis_client.set(f"sandbench:submission:{sub_hash}", json.dumps(immutable_record))
    redis_client.set(latest_hash_key, sub_hash)
    redis_client.lpush(history_key, json.dumps(immutable_record))

    member = _member(user_id, user, task_id)
    current_score = redis_client.zscore(score_key, member)
    if current_score is None or score > float(current_score):
        redis_client.zadd(score_key, {member: score})
        redis_client.hset(f"{score_key}:entries", member, json.dumps(immutable_record))

    entries = _ranked_entries(redis_client, score_key)
    rank = next((idx + 1 for idx, item in enumerate(entries) if item.get("hash") == sub_hash), 0)
    return VersionedLeaderboardEntry(
        rank=rank,
        user=user,
        user_id=user_id,
        submission_id=submission_id,
        submission_hash=sub_hash,
        run_id=run_id,
        suite=suite,
        task_id=task_id,
        task_title=task_title,
        task_version=task_version,
        score=score,
        verdict=verdict,
        created_at=created_at,
        artifact_bundle_hash=artifact_bundle_hash,
    )


def _member(user_id: str, user: str, task_id: str) -> str:
    return f"{user_id or user}:{task_id}"


def _ranked_entries(redis_client: Any, score_key: str) -> list[Dict[str, Any]]:
    try:
        members = redis_client.zrevrange(score_key, 0, -1)
    except Exception:
        return []
    results = []
    for member in members:
        raw = redis_client.hget(f"{score_key}:entries", member)
        if raw:
            try:
                results.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return results
