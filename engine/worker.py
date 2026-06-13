"""Worker service for SandBench.

Pulls execution jobs from Upstash Redis, runs the static and dynamic analysis
verdict engine, and writes the structured result JSON to Redis.
"""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone

import redis
import docker

from config import UPSTASH_REDIS_URL, LLM_PROVIDER
from sandbox import runner, static_gate, monitor, review
from sandbox.rules import Severity, Flag
from analysis import trace_log
from scoring import registry as task_registry
from scoring import score as scorer

# Initialize logging as required
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

JOBS_KEY = "sandbench:jobs"

# Initialize Redis client using the centralized config
r = redis.from_url(UPSTASH_REDIS_URL, decode_responses=True)
client = docker.from_env()


def handle(job: dict) -> None:
    """Process a single sandboxed execution job.

    Args:
        job: Dictionary containing runId/id, payload/code, and language/task details.
    """
    run_id = job.get("runId") or job.get("id")
    code = job.get("payload") or job.get("code") or ""
    language = job.get("language") or "python"

    if not run_id:
        logger.error("Job missing run ID")
        return

    logger.info("Processing job %s (language: %s)", run_id, language)

    # 1. Fetch current run details from Redis key run:{run_id} to enrich frontend state if present
    run_key = f"run:{run_id}"
    run_raw = r.get(run_key)
    run_data = json.loads(run_raw) if run_raw else None

    if run_data:
        run_data["status"] = "running"
        run_data["logs"].append("[worker] starting analysis pipeline...")
        r.set(run_key, json.dumps(run_data))

    try:
        # A) Static analysis gate (run before container creation)
        with tempfile.TemporaryDirectory() as tmpdir:
            flags = static_gate.scan(code, language, tmpdir)

        is_quarantined = any(f.severity == Severity.HIGH for f in flags)

        if is_quarantined:
            logger.warning("Job %s failed static gate analysis and is quarantined", run_id)
            result = {
                "run_id": run_id,
                "status": "quarantined",
                "verdict": "malicious",
                "score": 0.0,
                "flags": [f.to_dict() for f in flags],
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
                "exit_code": 0,
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
            }
            
            # Enrich and update the frontend representation if available
            if run_data:
                run_data["status"] = "quarantined"
                run_data["verdict"] = "malicious"
                run_data["score"] = 0.0
                run_data["finishedAt"] = result["finished_at"]
                run_data["flags"] = [
                    {
                        "id": f.rule_id,
                        "source": f.source,
                        "rule": f.rule_id,
                        "severity": f.severity.value.lower(),
                        "detail": f.evidence + (f" (at {f.location})" if f.location else "")
                    }
                    for f in flags
                ]
                run_data["logs"].append("[worker] quarantined by static analysis gate")
                r.set(run_key, json.dumps(run_data))

        else:
            # B) Execute code in the hardened container
            logger.info("Spawning hardened sandbox container for job %s", run_id)
            if run_data:
                run_data["logs"].append("[worker] spawning hardened container...")
                r.set(run_key, json.dumps(run_data))

            run_res = runner.run(code, language)

            # C) Monitor analysis of execution results
            monitor_flags = monitor.collect(
                run_res.container_attrs,
                run_res.fs_diff,
                run_res.stdout,
                run_res.stderr,
                run_res.timed_out
            )
            flags.extend(monitor_flags)

            # Determine final verdict and status
            if any(f.severity == Severity.HIGH for f in flags):
                verdict, status, score = "malicious", "quarantined", 0.0
            elif run_res.exit_code != 0 or run_res.timed_out:
                verdict, status, score = "broken", "done", None
            else:
                verdict, status, score = "clean", "done", None

            # D) Score clean runs against hidden test suite
            if verdict == "clean":
                task_id = job.get("taskId") or ""
                task = task_registry.get_task(task_id)
                if task and task.language == language:
                    try:
                        if run_data:
                            run_data["logs"].append("[scoring] running hidden test suite...")
                            r.set(run_key, json.dumps(run_data))

                        score_res = scorer.score_submission(code, task)
                        score = score_res["score"]
                        passed = score_res.get("passed", 0)
                        total = score_res.get("total", 0)
                        logger.info(
                            "Scoring for %s: %d/%d passed, score=%.2f",
                            run_id, passed, total, score,
                        )
                        if run_data:
                            run_data["logs"].append(
                                f"[scoring] {passed}/{total} tests passed (score {score:.2f})"
                            )
                    except Exception as score_err:
                        logger.exception("Scoring failed for run %s: %s", run_id, score_err)
                        score = 0.0
                elif task_id and not task:
                    logger.warning("Unknown taskId '%s' for run %s — scoring skipped", task_id, run_id)
                elif task and task.language != language:
                    logger.warning(
                        "Task %s language mismatch (%s vs %s) for run %s — scoring skipped",
                        task_id, task.language, language, run_id,
                    )
            elif verdict == "broken":
                score = 0.0
            elif verdict == "malicious":
                score = 0.0

            # E) Run analysis engine (WP3) for clean/broken runs
            suggestions = []
            if verdict in ("clean", "broken"):
                try:
                    error_output = (run_res.stderr or "")[:4000]
                    if verdict == "clean" and not error_output:
                        error_output = None
                    
                    review_res = review.review_code(code, error_output)
                    
                    if review_res.get("ok"):
                        review_text = review_res.get("review_text", "")
                        patch = review_res.get("patch", "")
                        
                        sug = {
                            "id": "sug_review",
                            "category": "tests" if verdict == "broken" else "style",
                            "message": review_text[:2000]
                        }
                        if patch and patch.strip():
                            sug["patchDiff"] = patch
                        suggestions.append(sug)
                        
                        # Log fine-tuning trace
                        try:
                            trace = {
                                "trace_id": run_id,
                                "task_id": job.get("taskId") or "",
                                "language": language,
                                "verdict": verdict,
                                "broken_code": code,
                                "error_output": error_output or "",
                                "review_text": review_text,
                                "patch": patch or "",
                                "model": LLM_PROVIDER,
                                "created_at": datetime.now(timezone.utc).isoformat() + "Z"
                            }
                            trace_log.log_trace(trace)
                        except Exception as trace_err:
                            logger.exception("Failed to write training trace: %s", trace_err)
                    else:
                        logger.warning("Analysis engine unavailable for run %s: %s", run_id, review_res.get("review_text", "unknown"))
                except Exception as analysis_err:
                    logger.exception("Analysis engine execution failed for run %s: %s", run_id, analysis_err)

            result = {
                "run_id": run_id,
                "status": status,
                "verdict": verdict,
                "score": score,
                "flags": [f.to_dict() for f in flags],
                "suggestions": suggestions,
                "stdout": run_res.stdout,
                "stderr": run_res.stderr,
                "duration_ms": run_res.duration_ms,
                "exit_code": run_res.exit_code,
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
            }

            # Enrich and update the frontend representation if available
            if run_data:
                run_data["status"] = status
                run_data["verdict"] = verdict
                run_data["score"] = score
                run_data["finishedAt"] = result["finished_at"]
                run_data["flags"] = [
                    {
                        "id": f.rule_id,
                        "source": f.source,
                        "rule": f.rule_id,
                        "severity": f.severity.value.lower(),
                        "detail": f.evidence + (f" (at {f.location})" if f.location else "")
                    }
                    for f in flags
                ]
                run_data["suggestions"] = suggestions
                run_data["logs"].append(f"[worker] container finished with exit code {run_res.exit_code}")
                if run_res.stdout:
                    run_data["logs"].append("--- stdout ---")
                    run_data["logs"].extend(run_res.stdout.splitlines())
                if run_res.stderr:
                    run_data["logs"].append("--- stderr ---")
                    run_data["logs"].extend(run_res.stderr.splitlines())
                run_data["logs"].append(f"[analysis] review complete ({len(suggestions)} suggestions)")
                r.set(run_key, json.dumps(run_data))

        # Write exact JSON contract back to Redis
        r.set(f"sandbench:run:{run_id}", json.dumps(result))
        logger.info("Job %s completed with status %s and verdict %s", run_id, result["status"], result["verdict"])

        # Write leaderboard entry for scored clean runs
        if result.get("verdict") == "clean" and isinstance(result.get("score"), (int, float)):
            try:
                entry = {
                    "rank": 0,  # will be recalculated on read
                    "user": "anon",
                    "submissionId": run_data.get("submissionId", f"sub_{run_id[4:]}") if run_data else f"sub_{run_id[4:]}",
                    "taskId": job.get("taskId") or "",
                    "taskTitle": run_data.get("taskTitle", job.get("taskId", "")) if run_data else job.get("taskId", ""),
                    "score": result["score"],
                    "verdict": "clean",
                    "createdAt": result["finished_at"],
                }
                # Append to leaderboard list in Redis
                lb_raw = r.get("leaderboard")
                lb: list = json.loads(lb_raw) if lb_raw else []
                lb.append(entry)
                # Sort descending by score, re-rank
                lb.sort(key=lambda e: e.get("score", 0), reverse=True)
                for idx, e in enumerate(lb):
                    e["rank"] = idx + 1
                r.set("leaderboard", json.dumps(lb))
                logger.info("Leaderboard entry added for run %s (score %.2f)", run_id, result["score"])
            except Exception as lb_err:
                logger.exception("Failed to update leaderboard for run %s: %s", run_id, lb_err)

    except Exception as e:
        logger.exception("Unexpected error handling job %s: %s", run_id, e)
        error_result = {
            "run_id": run_id,
            "status": "error",
            "verdict": None,
            "score": None,
            "flags": [],
            "stdout": "",
            "stderr": str(e),
            "duration_ms": 0,
            "exit_code": -1,
            "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
        }
        r.set(f"sandbench:run:{run_id}", json.dumps(error_result))
        
        if run_data:
            run_data["status"] = "error"
            run_data["logs"].append(f"[worker] critical failure: {str(e)}")
            r.set(run_key, json.dumps(run_data))


def main() -> None:
    """Worker main loop."""
    # Run orphan cleanup on startup
    runner.cleanup_orphans(client)
    
    logger.info("worker up, waiting for jobs...")
    while True:
        try:
            # BRPOP blocks until a job arrives; returns (key, value)
            _, raw = r.brpop(JOBS_KEY)
            job = json.loads(raw)
            handle(job)
        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error("Error in worker main loop: %s", e)


if __name__ == "__main__":
    main()
