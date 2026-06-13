"""Benchmark scoring engine for SandBench.

Runs the task's hidden test suite against a user submission INSIDE
a hardened sandbox container and computes a [0.0, 1.0] fraction score.
"""
import logging
import os
import re
from typing import Any, Dict

from scoring.registry import Task
from sandbox import runner

logger = logging.getLogger(__name__)

# Regex to parse pytest -q summary line, e.g. "3 passed, 2 failed in 0.12s"
_PYTEST_SUMMARY_RE = re.compile(
    r"(?:(\d+)\s+passed)?"
    r"(?:,?\s*(\d+)\s+failed)?"
    r"(?:,?\s*(\d+)\s+error)?"
)


def _parse_pytest_fraction(output: str) -> Dict[str, Any]:
    """Parse pytest -q output and return {score, passed, total}.

    Looks for the summary line pattern in the output. Falls back to 0.0
    if no recognizable summary is found.
    """
    passed = 0
    failed = 0
    errors = 0

    # Scan lines from the end for the summary
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue

        # Match patterns like "5 passed", "3 passed, 2 failed", "1 error"
        p = re.search(r"(\d+)\s+passed", line)
        f = re.search(r"(\d+)\s+failed", line)
        e = re.search(r"(\d+)\s+error", line)

        if p or f or e:
            passed = int(p.group(1)) if p else 0
            failed = int(f.group(1)) if f else 0
            errors = int(e.group(1)) if e else 0
            break

    total = passed + failed + errors
    if total == 0:
        return {"score": 0.0, "passed": 0, "total": 0}

    score = max(0.0, min(1.0, passed / total))
    return {"score": score, "passed": passed, "total": total}


def score_submission(code: str, task: Task) -> Dict[str, Any]:
    """Run the task's hidden test suite against the submission and score it.

    Args:
        code: The user-submitted source code.
        task: The Task definition (includes test_command, tests_dir, etc.).

    Returns:
        Dictionary with keys: score (float 0-1), passed (int), total (int),
        raw_output (str, truncated to 4000 chars).
        On any failure returns score 0.0 with an error note.
    """
    try:
        # Build extra_files: map each file under task.tests_dir into
        # /workspace/tests/<relative_path>
        extra_files: Dict[str, str] = {}
        tests_dir = task.tests_dir

        if tests_dir.is_dir():
            for root, _dirs, files in os.walk(tests_dir):
                for fname in files:
                    file_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(file_path, tests_dir)
                    # Normalize path separators for the container (Linux)
                    container_path = "/workspace/tests/" + rel_path.replace("\\", "/")
                    with open(file_path, "r", encoding="utf-8") as f:
                        extra_files[container_path] = f.read()
        else:
            logger.warning("Tests directory not found for task %s: %s", task.id, tests_dir)
            return {
                "score": 0.0,
                "passed": 0,
                "total": 0,
                "raw_output": f"Tests directory not found: {tests_dir}",
            }

        if not extra_files:
            logger.warning("No test files found for task %s", task.id)
            return {
                "score": 0.0,
                "passed": 0,
                "total": 0,
                "raw_output": "No test files found",
            }

        logger.info(
            "Scoring submission for task %s: %d test file(s), command=%s",
            task.id, len(extra_files), task.test_command,
        )

        # Run the test suite inside a fresh hardened sandbox
        run_res = runner.run(
            code,
            task.language,
            extra_files=extra_files,
            command=task.test_command,
        )

        # Combine stdout + stderr for parsing (pytest may write to either)
        raw_output = (run_res.stdout + "\n" + run_res.stderr).strip()
        truncated = raw_output[:4000]

        result = _parse_pytest_fraction(raw_output)
        result["raw_output"] = truncated

        logger.info(
            "Scoring result for task %s: %d/%d passed, score=%.2f",
            task.id, result["passed"], result["total"], result["score"],
        )
        return result

    except Exception as exc:
        logger.exception("Scoring failed for task %s: %s", task.id, exc)
        return {
            "score": 0.0,
            "passed": 0,
            "total": 0,
            "raw_output": f"Scoring error: {type(exc).__name__}",
        }
