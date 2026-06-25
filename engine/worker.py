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
from sandbox.archive import extract_archive
from sandbox.rules import Severity, Flag
from analysis import trace_log, patch_apply
from artifacts import create_artifact_bundle
from leaderboard import upsert_versioned_leaderboard
from scoring import registry as task_registry
from scoring import score as scorer
from scoring.schema import RunManifest, ScoreBreakdown, RepairResult, SecurityFlag

# Initialize logging as required
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

JOBS_KEY = "sandbench:jobs"

# Initialize Redis client using the centralized config
r = redis.from_url(UPSTASH_REDIS_URL, decode_responses=True)


def _handle_model_eval(job: dict, run_id: str, run_key: str, run_data, language: str) -> None:
    """Phase 2 branch: evaluate a user-supplied model as the repair agent.

    The model is called host-side (guarded by ssrf_guard); the sandbox only
    scores code. Maps run_model_eval()'s result into the SAME run_data / result
    shape the repair path writes.

    KEY SAFETY: api_key is read from the job, passed only to run_model_eval, and
    is NEVER written to run:{id}, sandbench:run:{id}, traces, the leaderboard,
    or any log. trace_log is intentionally NOT called for model_eval runs.
    """
    from rl_env.model_eval import run_model_eval
    from sandbox import providers

    task_id = job.get("taskId") or ""
    broken_code = job.get("payload") or job.get("code") or ""
    endpoint = job.get("modelEndpoint") or ""
    api_key = job.get("modelApiKey") or ""
    provider = job.get("provider") or "openai"
    model_name = job.get("modelName") or "user-model"

    if not endpoint.strip():
        resolved_url = providers.get_base_url(provider)
        if resolved_url is not None:
            endpoint = resolved_url

    if run_data:
        run_data["logs"].append(f"[model-eval] calling {provider}/{model_name} model...")
        r.set(run_key, json.dumps(run_data))

    eval_res = run_model_eval(task_id, broken_code, endpoint, api_key, model_name=model_name)
    # api_key is no longer needed and is not retained.
    del api_key

    finished_at = datetime.now(timezone.utc).isoformat() + "Z"

    if eval_res.get("status") == "done":
        score_after = eval_res.get("score_after")
        score = score_after if isinstance(score_after, (int, float)) else 0.0
        method = eval_res.get("method", "none")
        patch_applied = bool(eval_res.get("patch_applied"))
        reward = eval_res.get("reward")
        review_text = eval_res.get("model_review_text") or ""

        repair = {
            "attempted": True,
            "applied": patch_applied,
            "method": method,
            "score_before": eval_res.get("score_before"),
            "score_after": score_after,
            "reward": reward,
        }
        suggestions = []
        if review_text:
            suggestions.append({
                "id": "sug_model_review",
                "category": "tests",
                "message": review_text[:2000],
            })

        result = {
            "run_id": run_id,
            "status": "done",
            "verdict": "clean",
            "score": score,
            "flags": [],
            "suggestions": suggestions,
            "repair": repair,
            "stdout": "",
            "stderr": "",
            "duration_ms": 0,
            "exit_code": 0,
            "finished_at": finished_at,
        }
        if run_data:
            run_data["status"] = "done"
            run_data["verdict"] = "clean"
            run_data["score"] = score
            run_data["finishedAt"] = finished_at
            run_data["suggestions"] = suggestions
            run_data["repair"] = repair
            run_data["logs"].append(f"[model-eval] patch applied ({method})")
            if isinstance(reward, (int, float)):
                run_data["logs"].append(f"[model-eval] reward = {reward:+.4f}")
            else:
                run_data["logs"].append("[model-eval] reward = n/a")
            r.set(run_key, json.dumps(run_data))
        r.set(f"sandbench:run:{run_id}", json.dumps(result))
        logger.info("Model-eval job %s completed (clean, reward=%s)", run_id, reward)
        return

    # Failure path (SSRF rejection / model call error / unknown task): quarantine,
    # run NOTHING in the sandbox. The reason is guaranteed key-free by model_eval.
    reason = eval_res.get("reason") or "model evaluation failed"
    result = {
        "run_id": run_id,
        "status": "quarantined",
        "verdict": "malicious",
        "score": 0.0,
        "flags": [
            {
                "rule_id": "MODEL_ENDPOINT_REJECTED",
                "source": "worker",
                "location": "model-endpoint",
                "severity": "high",
                "detail": f"[model-eval] endpoint rejected: {reason}",
            }
        ],
        "stdout": "",
        "stderr": f"[model-eval] endpoint rejected: {reason}",
        "duration_ms": 0,
        "exit_code": 0,
        "finished_at": finished_at,
    }
    if run_data:
        run_data["status"] = "quarantined"
        run_data["verdict"] = "malicious"
        run_data["score"] = 0.0
        run_data["finishedAt"] = finished_at
        run_data["flags"] = [
            {
                "id": "MODEL_ENDPOINT_REJECTED",
                "source": "worker",
                "rule": "MODEL_ENDPOINT_REJECTED",
                "severity": "high",
                "detail": f"[model-eval] endpoint rejected: {reason}",
            }
        ]
        run_data["logs"].append(f"[model-eval] endpoint rejected: {reason}")
        r.set(run_key, json.dumps(run_data))
    r.set(f"sandbench:run:{run_id}", json.dumps(result))
    logger.warning("Model-eval job %s quarantined: %s", run_id, reason)
    return


def handle(job: dict) -> None:
    """Process a single sandboxed execution job.

    Args:
        job: Dictionary containing runId/id, payload/code, and language/task details.
    """
    run_id = job.get("runId") or job.get("id")
    if not run_id:
        logger.error("Job missing run ID")
        return

    code = job.get("payload") or job.get("code") or ""
    language = job.get("language") or "python"

    task_id = job.get("taskId") or ""
    task = task_registry.get_task(task_id)

    logger.info("Processing job %s (language: %s, task: %s)", run_id, language, task_id)

    # 1. Fetch current run details from Redis key run:{run_id} to enrich frontend state if present
    run_key = f"run:{run_id}"
    run_raw = r.get(run_key)
    run_data = json.loads(run_raw) if run_raw else None

    if run_data:
        run_data["status"] = "running"
        run_data["logs"].append("[worker] starting analysis pipeline...")
        r.set(run_key, json.dumps(run_data))

    # Phase 2: model-evaluation jobs run the user's own model HOST-SIDE as the
    # repair agent. The sandbox is never given the endpoint or key. Handled in
    # a parallel branch that returns before the static-gate sandbox flow.
    if job.get("type") == "model_eval":
        _handle_model_eval(job, run_id, run_key, run_data, language)
        return

    user_files = None
    if job.get("type") == "files":
        archive_b64 = job.get("archiveB64") or ""
        archive_kind = job.get("archiveKind") or ""
        
        from config import MAX_UNCOMPRESSED
        max_b64_len = int((MAX_UNCOMPRESSED * 2) * 4 / 3) + 4
        
        if not archive_b64 or not archive_kind:
            reason = "missing archive payload or kind"
        elif len(archive_b64) > max_b64_len:
            reason = "archive size exceeds maximum uncompressed limit before decoding"
        else:
            reason = None
            
        if reason:
            logger.warning("Archive rejected for run %s: %s", run_id, reason)
            result = {
                "run_id": run_id,
                "status": "quarantined",
                "verdict": "malicious",
                "score": 0.0,
                "flags": [
                    {
                        "rule_id": "ARCHIVE_REJECTED",
                        "source": "worker",
                        "location": "archive",
                        "severity": "high",
                        "detail": f"[archive] rejected: {reason}"
                    }
                ],
                "stdout": "",
                "stderr": f"[archive] rejected: {reason}",
                "duration_ms": 0,
                "exit_code": 0,
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
            }
            if run_data:
                run_data["status"] = "quarantined"
                run_data["verdict"] = "malicious"
                run_data["score"] = 0.0
                run_data["finishedAt"] = result["finished_at"]
                run_data["flags"] = [
                    {
                        "id": "ARCHIVE_REJECTED",
                        "source": "worker",
                        "rule": "ARCHIVE_REJECTED",
                        "severity": "high",
                        "detail": f"[archive] rejected: {reason}"
                    }
                ]
                run_data["logs"].append(f"[archive] rejected: {reason}")
                r.set(run_key, json.dumps(run_data))
            r.set(f"sandbench:run:{run_id}", json.dumps(result))
            return

        import base64
        try:
            raw_bytes = base64.b64decode(archive_b64)
        except Exception as exc:
            reason = f"failed to decode base64: {str(exc)}"
            result = {
                "run_id": run_id,
                "status": "quarantined",
                "verdict": "malicious",
                "score": 0.0,
                "flags": [
                    {
                        "rule_id": "ARCHIVE_REJECTED",
                        "source": "worker",
                        "location": "archive",
                        "severity": "high",
                        "detail": f"[archive] rejected: {reason}"
                    }
                ],
                "stdout": "",
                "stderr": f"[archive] rejected: {reason}",
                "duration_ms": 0,
                "exit_code": 0,
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
            }
            if run_data:
                run_data["status"] = "quarantined"
                run_data["verdict"] = "malicious"
                run_data["score"] = 0.0
                run_data["finishedAt"] = result["finished_at"]
                run_data["flags"] = [
                    {
                        "id": "ARCHIVE_REJECTED",
                        "source": "worker",
                        "rule": "ARCHIVE_REJECTED",
                        "severity": "high",
                        "detail": f"[archive] rejected: {reason}"
                    }
                ]
                run_data["logs"].append(f"[archive] rejected: {reason}")
                r.set(run_key, json.dumps(run_data))
            r.set(f"sandbench:run:{run_id}", json.dumps(result))
            return

        # --- rawfile: single source file uploaded directly ---
        if archive_kind == "rawfile":
            try:
                file_content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                reason = "uploaded file is not valid UTF-8 text"
                result = {
                    "run_id": run_id,
                    "status": "quarantined",
                    "verdict": "malicious",
                    "score": 0.0,
                    "flags": [{"rule_id": "ARCHIVE_REJECTED", "source": "worker", "location": "archive", "severity": "high", "detail": f"[archive] rejected: {reason}"}],
                    "stdout": "",
                    "stderr": f"[archive] rejected: {reason}",
                    "duration_ms": 0,
                    "exit_code": 0,
                    "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
                }
                if run_data:
                    run_data["status"] = "quarantined"
                    run_data["verdict"] = "malicious"
                    run_data["score"] = 0.0
                    run_data["finishedAt"] = result["finished_at"]
                    run_data["flags"] = [{"id": "ARCHIVE_REJECTED", "source": "worker", "rule": "ARCHIVE_REJECTED", "severity": "high", "detail": f"[archive] rejected: {reason}"}]
                    run_data["logs"].append(f"[archive] rejected: {reason}")
                    r.set(run_key, json.dumps(run_data))
                r.set(f"sandbench:run:{run_id}", json.dumps(result))
                return

            entrypoint_filename = task.entrypoint if task else ("solution.js" if language == "node" else "solution.py")
            entrypoint_key = f"/workspace/{entrypoint_filename}"
            user_files = {entrypoint_key: file_content}
            code = file_content
            if run_data:
                run_data["logs"].append("[worker] raw file validated successfully (1 file)")
                r.set(run_key, json.dumps(run_data))

        else:
            user_files, extract_reason = extract_archive(raw_bytes, archive_kind)
            
            if user_files is None:
                logger.warning("Archive validation failed for run %s: %s", run_id, extract_reason)
                result = {
                    "run_id": run_id,
                    "status": "quarantined",
                    "verdict": "malicious",
                    "score": 0.0,
                    "flags": [
                        {
                            "rule_id": "ARCHIVE_REJECTED",
                            "source": "worker",
                            "location": "archive",
                            "severity": "high",
                            "detail": f"[archive] rejected: {extract_reason}"
                        }
                    ],
                    "stdout": "",
                    "stderr": f"[archive] rejected: {extract_reason}",
                    "duration_ms": 0,
                    "exit_code": 0,
                    "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
                }
                if run_data:
                    run_data["status"] = "quarantined"
                    run_data["verdict"] = "malicious"
                    run_data["score"] = 0.0
                    run_data["finishedAt"] = result["finished_at"]
                    run_data["flags"] = [
                        {
                            "id": "ARCHIVE_REJECTED",
                            "source": "worker",
                            "rule": "ARCHIVE_REJECTED",
                            "severity": "high",
                            "detail": f"[archive] rejected: {extract_reason}"
                        }
                    ]
                    run_data["logs"].append(f"[archive] rejected: {extract_reason}")
                    r.set(run_key, json.dumps(run_data))
                r.set(f"sandbench:run:{run_id}", json.dumps(result))
                return

            entrypoint_filename = task.entrypoint if task else ("solution.js" if language == "node" else "solution.py")
            entrypoint_key = f"/workspace/{entrypoint_filename}"
            
            if entrypoint_key not in user_files:
                # Try to resolve a candidate from the uploaded files to act as the entrypoint
                ext = ".js" if language == "node" else ".py"
                candidates = [k for k in user_files.keys() if k.endswith(ext)]
                if candidates:
                    root_candidates = [c for c in candidates if c.count("/") == 2]
                    selected_candidate = None
                    if root_candidates:
                        main_names = {"/workspace/main.py", "/workspace/index.js", f"/workspace/{task_id}{ext}"}
                        for name in main_names:
                            if name in root_candidates:
                                selected_candidate = name
                                break
                        if not selected_candidate:
                            selected_candidate = root_candidates[0]
                    else:
                        selected_candidate = candidates[0]
                    
                    if selected_candidate:
                        logger.info("Aliasing entrypoint from %s to %s", selected_candidate, entrypoint_key)
                        user_files[entrypoint_key] = user_files[selected_candidate]
            
            if entrypoint_key not in user_files:
                available_files = [k.replace("/workspace/", "") for k in user_files.keys()]
                error_msg = f"[archive] entrypoint {entrypoint_filename} not found. Found files: {', '.join(available_files) if available_files else 'none'}"
                logger.warning("Entrypoint %s not found in user files. Available: %s", entrypoint_key, available_files)
                result = {
                    "run_id": run_id,
                    "status": "done",
                    "verdict": "broken",
                    "score": 0.0,
                    "flags": [],
                    "stdout": "",
                    "stderr": error_msg,
                    "duration_ms": 0,
                    "exit_code": -1,
                    "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
                }
                if run_data:
                    run_data["status"] = "done"
                    run_data["verdict"] = "broken"
                    run_data["score"] = 0.0
                    run_data["finishedAt"] = result["finished_at"]
                    run_data["logs"].append(error_msg)
                    r.set(run_key, json.dumps(run_data))
                r.set(f"sandbench:run:{run_id}", json.dumps(result))
                return

            code = user_files[entrypoint_key]
            if run_data:
                run_data["logs"].append(f"[worker] archive validated successfully ({len(user_files)} extra files found)")
                r.set(run_key, json.dumps(run_data))

    try:
        flags = []
        run_res = None
        score_res = None
        suggestions = []
        repair_data = None
        with tempfile.TemporaryDirectory() as tmpdir:
            if user_files:
                for file_path, file_content in user_files.items():
                    try:
                        file_flags = static_gate.scan(file_content, language, tmpdir)
                        rel_path = file_path.replace("/workspace/", "")
                        for flag in file_flags:
                            if flag.location and ":" in flag.location:
                                loc_parts = flag.location.split(":", 1)
                                flag.location = f"{rel_path}:{loc_parts[1]}"
                            else:
                                flag.location = rel_path
                        flags.extend(file_flags)
                    except Exception as scan_err:
                        logger.warning("Failed to scan file %s in static gate: %s", file_path, scan_err)
            else:
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

            run_res = runner.run(
                code,
                language,
                extra_files=user_files,
                is_safety_task=bool(task and task.suite == "safety"),
            )

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
            has_high = any(f.severity == Severity.HIGH for f in flags)
            has_medium = any(f.severity == Severity.MEDIUM for f in flags)
            if has_high:
                verdict, status, score = "malicious", "quarantined", 0.0
            elif run_res.exit_code != 0 or run_res.timed_out:
                verdict, status, score = "broken", "done", None
            elif has_medium:
                verdict, status, score = "suspicious", "done", None
            else:
                verdict, status, score = "clean", "done", None

            # D) Score clean/suspicious runs against hidden test suite
            score_res = None  # will be passed to review engine
            if verdict in ("clean", "suspicious"):
                task_id = job.get("taskId") or ""
                task = task_registry.get_task(task_id)
                if task and task.language == language:
                    try:
                        if run_data:
                            run_data["logs"].append("[scoring] running hidden test suite...")
                            r.set(run_key, json.dumps(run_data))

                        score_res = scorer.score_submission(code, task, project_files=user_files)
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

                        # Check for security flags from the scoring container
                        scoring_flags = score_res.get("flags", [])
                        if scoring_flags:
                            flags.extend(scoring_flags)
                            if any(f.severity == Severity.HIGH for f in scoring_flags):
                                verdict = "malicious"
                                status = "quarantined"
                                score = 0.0
                                if run_data:
                                    run_data["logs"].append("[worker] quarantined by dynamic analysis during scoring")
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
            if verdict in ("clean", "suspicious", "broken"):
                try:
                    error_output = (run_res.stderr or "")[:4000]
                    if verdict in ("clean", "suspicious") and not error_output:
                        error_output = None
                    
                    review_res = review.review_code(code, error_output, score_info=score_res)
                    
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
                        
                        # --- WP5 REPAIR LOOP ---
                        attempted = False
                        applied = False
                        method_str = "none"
                        score_before_val = score if score is not None else 0.0
                        score_after_val = None
                        reward_val = None
                        
                        task_id = job.get("taskId") or ""
                        task = task_registry.get_task(task_id)
                        has_room_to_improve = (verdict == "broken") or (verdict in ("clean", "suspicious") and score is not None and score < 1.0)
                        
                        if has_room_to_improve and patch and patch.strip() and task:
                            attempted = True
                            try:
                                logger.info("Starting repair-and-rescore loop for run %s", run_id)
                                patched_code, method_str = patch_apply.apply_patch(code, patch)
                                
                                if patched_code is None:
                                    logger.info("[repair] patch did not apply: %s", method_str)
                                    repair_data = {
                                        "attempted": True,
                                        "applied": False,
                                        "method": method_str,
                                        "score_before": score_before_val,
                                        "score_after": None,
                                        "reward": None
                                    }
                                else:
                                    applied = True
                                    logger.info("[repair] patch applied successfully via %s", method_str)
                                    if run_data:
                                        run_data["logs"].append(f"[repair] patch applied ({method_str})")
                                        r.set(run_key, json.dumps(run_data))
                                    
                                    score_after_res = scorer.score_submission(patched_code, task, project_files=user_files)
                                    score_after_val = score_after_res["score"]
                                    passed_after = score_after_res.get("passed", 0)
                                    total_after = score_after_res.get("total", 0)
                                    reward_val = round(score_after_val - score_before_val, 4)
                                    
                                    logger.info(
                                        "[repair] re-scored patched code: %d/%d passed, score=%.2f, reward=%+.2f",
                                        passed_after, total_after, score_after_val, reward_val
                                    )
                                    if run_data:
                                        run_data["logs"].append(
                                            f"[repair] re-scored patched code: {passed_after}/{total_after} (score {score_after_val:.2f})"
                                        )
                                        run_data["logs"].append(f"[repair] reward = {reward_val:+.2f}")
                                        r.set(run_key, json.dumps(run_data))
                                    
                                    repair_data = {
                                        "attempted": True,
                                        "applied": True,
                                        "method": method_str,
                                        "score_before": score_before_val,
                                        "score_after": score_after_val,
                                        "reward": reward_val
                                    }
                            except Exception as repair_err:
                                logger.exception("Error in repair loop for run %s: %s", run_id, repair_err)
                                repair_data = {
                                    "attempted": True,
                                    "applied": False,
                                    "method": f"error: {type(repair_err).__name__}",
                                    "score_before": score_before_val,
                                    "score_after": None,
                                    "reward": None
                                }
                        
                        # Log fine-tuning trace (now containing reward fields)
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
                                "created_at": datetime.now(timezone.utc).isoformat() + "Z",
                                # WP5 fields:
                                "score_before": score_before_val if attempted else None,
                                "score_after": score_after_val,
                                "reward": reward_val,
                                "patch_applied": applied
                            }
                            trace_log.log_trace(trace)
                        except Exception as trace_err:
                            logger.exception("Failed to write training trace: %s", trace_err)
                    else:
                        error_msg = review_res.get("review_text", "unknown")
                        logger.warning("Analysis engine unavailable for run %s: %s", run_id, error_msg)
                        suggestions.append({
                            "id": "sug_review_unavailable",
                            "category": "system",
                            "message": f"**Analysis Engine Unavailable**: {error_msg}"
                        })
                except Exception as analysis_err:
                    logger.exception("Analysis engine execution failed for run %s: %s", run_id, analysis_err)
                    suggestions.append({
                        "id": "sug_review_failed",
                        "category": "system",
                        "message": f"**Analysis Engine Error**: {type(analysis_err).__name__}"
                    })
            
            result = {
                "run_id": run_id,
                "status": status,
                "verdict": verdict,
                "score": score,
                "flags": [f.to_dict() for f in flags],
                "suggestions": suggestions,
                "stdout": run_res.stdout if run_res is not None else "",
                "stderr": run_res.stderr if run_res is not None else "",
                "duration_ms": run_res.duration_ms if run_res is not None else 0,
                "exit_code": run_res.exit_code if run_res is not None else -1,
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z"
            }
            if repair_data:
                result["repair"] = repair_data
            
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
                if repair_data:
                    run_data["repair"] = repair_data
                if run_res is not None:
                    run_data["logs"].append(f"[worker] container finished with exit code {run_res.exit_code}")
                if run_res is not None and run_res.stdout:
                    run_data["logs"].append("--- stdout ---")
                    run_data["logs"].extend(run_res.stdout.splitlines())
                if run_res is not None and run_res.stderr:
                    run_data["logs"].append("--- stderr ---")
                    run_data["logs"].extend(run_res.stderr.splitlines())
                medium_flags = [f for f in flags if f.severity in (Severity.MEDIUM, Severity.LOW)]
                flag_note = f", {len(medium_flags)} security flag(s) recorded" if medium_flags else ""
                run_data["logs"].append(f"[analysis] review complete ({len(suggestions)} suggestions{flag_note})")
                r.set(run_key, json.dumps(run_data))

        # Write exact JSON contract back to Redis
        r.set(f"sandbench:run:{run_id}", json.dumps(result))
        logger.info("Job %s completed with status %s and verdict %s", run_id, result["status"], result["verdict"])

        # Build and store RunManifest for structured audit trail
        try:
            task_id = job.get("taskId") or ""
            task = task_registry.get_task(task_id)
            manifest_flags = []
            for f in flags:
                manifest_flags.append(SecurityFlag(
                    rule_id=f.rule_id,
                    source=f.source,
                    location=f.location,
                    severity=f.severity.value.lower() if hasattr(f.severity, 'value') else str(f.severity),
                    detail=f.evidence if hasattr(f, 'evidence') else "",
                    cwe=getattr(f, "cwe", ""),
                    category=getattr(f, "category", ""),
                ))

            manifest_repair = None
            if repair_data:
                manifest_repair = RepairResult(
                    attempted=repair_data.get("attempted", False),
                    applied=repair_data.get("applied", False),
                    method=repair_data.get("method", "none"),
                    score_before=repair_data.get("score_before"),
                    score_after=repair_data.get("score_after"),
                    reward=repair_data.get("reward"),
                )

            manifest_breakdown = None
            if score_res:
                manifest_breakdown = ScoreBreakdown(
                    passed=score_res.get("passed", 0),
                    total=score_res.get("total", 0),
                    score=score_res.get("score", 0.0),
                    raw_output=score_res.get("raw_output", "")[:2000],
                )

            manifest = RunManifest(
                run_id=run_id,
                task_id=task_id,
                task_version=task.version if task else "0.1.0",
                suite=task.suite if task else "core",
                language=language,
                status=result.get("status", "done"),
                verdict=result.get("verdict"),
                score=result.get("score"),
                score_breakdown=manifest_breakdown,
                flags=manifest_flags,
                monitorability_traces=monitor.trace(
                    run_res.container_attrs if run_res is not None else {},
                    run_res.fs_diff if run_res is not None else [],
                    run_res.stdout if run_res is not None else "",
                    run_res.stderr if run_res is not None else "",
                    run_res.timed_out if run_res is not None else False,
                ),
                duration_ms=result.get("duration_ms", 0),
                finished_at=result.get("finished_at"),
                repair=manifest_repair,
                user_id=job.get("userId"),
                user_name=job.get("userName"),
                submission_type=job.get("type", "code"),
            )

            submitted_files = user_files or {f"/workspace/{task.entrypoint if task else ('solution.js' if language == 'node' else 'solution.py')}": code}
            repair_patch = ""
            for suggestion in suggestions:
                if suggestion.get("patchDiff"):
                    repair_patch = suggestion["patchDiff"]
                    break

            artifact_bundle = create_artifact_bundle(
                run_id=run_id,
                manifest=manifest.to_redis_dict(),
                submitted_files=submitted_files,
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                score_breakdown=manifest_breakdown.model_dump(mode="json") if manifest_breakdown else {},
                flags=[flag.model_dump(mode="json") for flag in manifest_flags],
                repair_patch=repair_patch,
            )
            manifest.artifact_hashes = {
                **artifact_bundle.artifact_hashes,
                "bundle": artifact_bundle.bundle_hash,
            }
            r.set(f"sandbench:manifest:{run_id}", json.dumps(manifest.to_redis_dict()))
            r.set(
                f"sandbench:artifact:{run_id}",
                json.dumps({
                    "run_id": run_id,
                    "bundle_dir": artifact_bundle.bundle_dir,
                    "bundle_hash": artifact_bundle.bundle_hash,
                    "artifact_hashes": artifact_bundle.artifact_hashes,
                    "signed_urls": artifact_bundle.signed_urls,
                }),
            )
            result["artifact"] = {
                "bundleHash": artifact_bundle.bundle_hash,
                "manifestUrl": artifact_bundle.signed_urls.get("manifest"),
                "bundleUrl": artifact_bundle.signed_urls.get("bundle"),
            }
            if run_data is not None:
                run_data["artifact"] = result["artifact"]
                r.set(run_key, json.dumps(run_data))
            r.set(f"sandbench:run:{run_id}", json.dumps(result))
            logger.info("RunManifest stored for %s", run_id)
        except Exception as manifest_err:
            logger.warning("Failed to store RunManifest for %s: %s", run_id, manifest_err)

        # Write leaderboard entry for scored clean runs
        if result.get("verdict") in ("clean", "suspicious") and isinstance(result.get("score"), (int, float)):
            try:
                entry = {
                    "rank": 0,  # will be recalculated on read
                    "user": job.get("userName") or "anon",
                    "userId": job.get("userId") or "",
                    "submissionId": run_data.get("submissionId", f"sub_{run_id[4:]}") if run_data else f"sub_{run_id[4:]}",
                    "taskId": job.get("taskId") or "",
                    "taskTitle": run_data.get("taskTitle", job.get("taskId", "")) if run_data else job.get("taskId", ""),
                    "score": result["score"],
                    "verdict": result["verdict"],
                    "createdAt": result["finished_at"],
                    "suite": task.suite if task else "core",
                    "taskVersion": task.version if task else "0.1.0",
                    "artifactBundleHash": result.get("artifact", {}).get("bundleHash", ""),
                }
                versioned_entry = upsert_versioned_leaderboard(
                    r,
                    run_id=run_id,
                    user=entry["user"],
                    user_id=entry["userId"],
                    submission_id=entry["submissionId"],
                    suite=entry["suite"],
                    task_id=entry["taskId"],
                    task_title=entry["taskTitle"],
                    task_version=entry["taskVersion"],
                    score=result["score"],
                    verdict=result["verdict"],
                    created_at=result["finished_at"],
                    artifact_bundle_hash=entry["artifactBundleHash"],
                )
                entry["submissionHash"] = versioned_entry.submission_hash
                # Upsert leaderboard entry: keep the higher score per (user, taskId)
                lb_raw = r.get("leaderboard")
                lb: list = json.loads(lb_raw) if lb_raw else []
                
                existing_idx = -1
                for idx, e in enumerate(lb):
                    e_uid = e.get("userId")
                    entry_uid = entry.get("userId") 
                    if e_uid and entry_uid:
                        user_match = e_uid == entry_uid
                    else:
                        user_match = e.get("user") == entry["user"]

                    if user_match and e.get("taskId") == entry["taskId"]:
                        existing_idx = idx
                        break
                
                if existing_idx != -1:
                    if entry["score"] > lb[existing_idx].get("score", 0.0):
                        lb[existing_idx] = entry
                        logger.info("Leaderboard entry updated (new high score %.2f)", entry["score"])
                    else:
                        logger.info(
                            "Leaderboard entry not updated (existing score %.2f >= %.2f)",
                            lb[existing_idx].get("score", 0.0), entry["score"]
                        )
                else:
                    lb.append(entry)
                    logger.info("New leaderboard entry appended")
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
    client = docker.from_env()

    # Run orphan cleanup on startup
    runner.cleanup_orphans(client)
    
    # Pre-pull required sandbox images
    for img in ["python:3.11-slim", "node:20-slim"]:
        try:
            logger.info("Checking sandbox image: %s", img)
            client.images.get(img)
        except docker.errors.ImageNotFound:
            logger.info("Sandbox image %s not found locally. Pulling...", img)
            try:
                client.images.pull(img)
                logger.info("Successfully pulled sandbox image: %s", img)
            except Exception as pull_err:
                logger.warning("Failed to pull sandbox image %s: %s", img, pull_err)
        except Exception as e:
            logger.warning("Failed to verify sandbox image %s: %s", img, e)

    # Publish real task registry to Redis on startup
    try:
        public_list = task_registry.load_public_tasks()
        r.set("tasks", json.dumps(public_list))
        logger.info("[worker] published %d tasks to Redis", len(public_list))
    except Exception as exc:
        logger.exception("[worker] failed to publish task registry: %s", exc)
    
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
