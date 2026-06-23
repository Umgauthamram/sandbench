"""Build a redacted fine-tuning dataset from SandBench trace logs.

Output format is chat-style JSONL:
  {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}], "metadata": {...}}
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analysis.redaction import sanitize_trace

SYSTEM_PROMPT = (
    "You are an expert SandBench repair agent. Review submitted code, explain the "
    "main issue, and return JSON with review_text and a unified diff patch. If no "
    "patch is needed, use an empty patch string."
)

SKIP_REVIEW_MARKERS = (
    "error calling",
    "client error",
    "unauthorized",
    "api key",
    "generatecontent?key=",
)


def _stable_validation_split(trace_id: str, validation_ratio: float) -> bool:
    digest = hashlib.sha256(trace_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < validation_ratio


def _is_usable_trace(trace: dict[str, Any]) -> bool:
    code = trace.get("broken_code")
    review_text = trace.get("review_text")
    if not isinstance(code, str) or not code.strip():
        return False
    if not isinstance(review_text, str) or not review_text.strip():
        return False

    lowered_review = review_text.lower()
    return not any(marker in lowered_review for marker in SKIP_REVIEW_MARKERS)


def _build_user_prompt(trace: dict[str, Any]) -> str:
    fields = [
        f"Task ID: {trace.get('task_id', '')}",
        f"Language: {trace.get('language', '')}",
        f"Verdict: {trace.get('verdict', '')}",
    ]

    score_before = trace.get("score_before")
    if isinstance(score_before, (int, float)):
        fields.append(f"Score before: {score_before}")

    error_output = trace.get("error_output") or "None"
    code = trace.get("broken_code") or ""

    return (
        "\n".join(fields)
        + "\n\n--- RUNTIME OR TEST OUTPUT ---\n"
        + str(error_output)
        + "\n\n--- SUBMITTED CODE ---\n"
        + str(code)
    )


def _build_example(trace: dict[str, Any]) -> dict[str, Any]:
    assistant_payload = {
        "review_text": trace.get("review_text", ""),
        "patch": trace.get("patch", "") or "",
    }
    metadata = {
        "trace_id": trace.get("trace_id", ""),
        "task_id": trace.get("task_id", ""),
        "language": trace.get("language", ""),
        "verdict": trace.get("verdict", ""),
        "model": trace.get("model", ""),
        "created_at": trace.get("created_at", ""),
        "score_before": trace.get("score_before"),
        "score_after": trace.get("score_after"),
        "reward": trace.get("reward"),
        "patch_applied": trace.get("patch_applied"),
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(trace)},
            {"role": "assistant", "content": json.dumps(assistant_payload, ensure_ascii=False)},
        ],
        "metadata": metadata,
    }


def _iter_traces(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                trace = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(trace, dict):
                sanitized = sanitize_trace(trace)
                if isinstance(sanitized, dict):
                    sanitized["_source_line"] = line_number
                    yield sanitized


def build_dataset(input_path: Path, output_dir: Path, validation_ratio: float) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.jsonl"
    validation_path = output_dir / "validation.jsonl"
    manifest_path = output_dir / "manifest.json"

    train_count = 0
    validation_count = 0
    skipped_count = 0
    task_counts: dict[str, int] = {}

    with train_path.open("w", encoding="utf-8") as train_out, validation_path.open(
        "w", encoding="utf-8"
    ) as validation_out:
        for trace in _iter_traces(input_path):
            if not _is_usable_trace(trace):
                skipped_count += 1
                continue

            example = _build_example(trace)
            trace_id = str(trace.get("trace_id") or f"line-{trace.get('_source_line', '')}")
            line = json.dumps(example, ensure_ascii=False) + "\n"

            if _stable_validation_split(trace_id, validation_ratio):
                validation_out.write(line)
                validation_count += 1
            else:
                train_out.write(line)
                train_count += 1

            task_id = str(trace.get("task_id") or "unknown")
            task_counts[task_id] = task_counts.get(task_id, 0) + 1

    manifest = {
        "schema": "sandbench.chat_finetune.v0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(input_path),
        "redacted": True,
        "validation_ratio": validation_ratio,
        "counts": {
            "train": train_count,
            "validation": validation_count,
            "skipped": skipped_count,
            "total_exported": train_count + validation_count,
        },
        "tasks": task_counts,
        "files": {
            "train": str(train_path),
            "validation": str(validation_path),
            "manifest": str(manifest_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build redacted SandBench training JSONL.")
    parser.add_argument("--input", type=Path, default=Path("traces.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("../datasets/sandbench-traces-v0"))
    parser.add_argument("--validation-ratio", type=float, default=0.1)
    args = parser.parse_args()

    manifest = build_dataset(args.input, args.output, args.validation_ratio)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
