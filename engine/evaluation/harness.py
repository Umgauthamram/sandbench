import time
import json
import logging
from typing import List, Dict, Any, Optional

from scoring import registry as task_registry
from scoring import score as scorer
from analysis import patch_apply
from adapters.base import ModelAdapter
from evaluation.models import EvaluationConfig, TaskResult, EvaluationResult
from evaluation.estimator import pass_at_k

logger = logging.getLogger(__name__)

def _build_evaluation_prompt(code: str, error_output: Optional[str]) -> str:
    return (
        "You are an expert security and code quality review agent for SandBench.\n"
        "Analyze the following user-submitted code and its runtime/test stderr output (if any).\n"
        "Provide a structured code review identifying the top issues/bugs and suggest a unified-diff format patch to fix them.\n\n"
        f"--- USER SOURCE CODE ---\n{code}\n\n"
        f"--- RUNTIME STDERR ---\n{error_output or 'None (Code ran or is being reviewed statically)'}\n\n"
        "Format your output as a JSON object matching this structure:\n"
        "{\n"
        "  \"review_text\": \"Description of the main bugs, logic errors, or style issues found.\",\n"
        "  \"patch\": \"Unified diff string showing changes to apply, starting with +++ and --- lines, or empty string if no patch is needed.\"\n"
        "}"
    )

def evaluate_suite(
    suite_id: str,
    adapter: ModelAdapter,
    k: int = 1,
    n: int = 5,
    task_ids: Optional[List[str]] = None,
    timeout_overrides: Optional[Dict[str, int]] = None,
) -> EvaluationResult:
    """Core evaluation orchestrator:
    
    1. Discovers tasks matching the suite.
    2. Runs a baseline scoring run to get test output/stderr.
    3. Drives the repair loop n times per task.
    4. Applies model patches and scores the repaired code.
    5. Computes pass@k.
    """
    t_start = time.time()
    
    # 1. Discover tasks
    all_tasks = task_registry.load_tasks()
    suite_tasks = [t for t in all_tasks.values() if t.suite == suite_id]
    if task_ids is not None:
        suite_tasks = [t for t in suite_tasks if t.id in task_ids]

    task_results = {}
    total_tokens = 0
    total_cost = 0.0
    passed_tasks_count = 0

    config = EvaluationConfig(
        suite_id=suite_id,
        adapter_name=adapter.name,
        provider=adapter.provider,
        k=k,
        n=n,
        timeout_overrides=timeout_overrides
    )

    for task in suite_tasks:
        logger.info("Evaluating task %s in suite %s", task.id, suite_id)
        
        # 2. Get baseline run
        baseline_res = scorer.score_submission(task.broken_code, task)
        baseline_score = baseline_res.get("score", 0.0)
        baseline_output = baseline_res.get("raw_output", "")

        # Optional: apply timeout override if specified for this task
        gen_kwargs: Dict[str, Any] = {
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        if timeout_overrides and task.id in timeout_overrides:
            gen_kwargs["timeout_s"] = timeout_overrides[task.id]

        scores = []
        durations_ms = []
        token_usages = []
        errors = []
        correct_runs = 0

        # 3. Repair loop n times
        for i in range(n):
            prompt = _build_evaluation_prompt(task.broken_code, baseline_output)
            
            # Run model adapter generate
            gen_res = adapter.generate(prompt, **gen_kwargs)
            durations_ms.append(gen_res.duration_ms)
            
            usage = gen_res.usage or {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0
            }
            token_usages.append(usage)
            total_tokens += usage.get("total_tokens", 0)
            total_cost += usage.get("estimated_cost", 0.0)

            if not gen_res.ok:
                scores.append(baseline_score)
                errors.append(gen_res.error or "Generation failed")
                continue

            # Parse JSON
            try:
                parsed = json.loads(gen_res.content)
                patch = parsed.get("patch", "") or ""
            except Exception as e:
                scores.append(baseline_score)
                errors.append(f"JSONDecodeError: {type(e).__name__}")
                continue

            if not patch.strip():
                scores.append(baseline_score)
                errors.append("No patch suggested by model")
                continue

            # Apply patch
            patched_code, method = patch_apply.apply_patch(task.broken_code, patch)
            if patched_code is None:
                scores.append(baseline_score)
                errors.append(f"PatchApplyError: {method}")
                continue

            # Score in sandbox
            # If there's task specific timeout override, wait, we can pass it when we update score.py.
            # For now, score_submission will take task.resource_overrides.
            score_res = scorer.score_submission(patched_code, task)
            score_after = score_res.get("score", 0.0)
            scores.append(score_after)
            
            if score_after >= 1.0:
                correct_runs += 1
                
            errors.append(None)

        p_at_k = pass_at_k(n, correct_runs, k)
        if correct_runs > 0:
            passed_tasks_count += 1

        task_results[task.id] = TaskResult(
            task_id=task.id,
            n=n,
            c=correct_runs,
            pass_at_k=p_at_k,
            scores=scores,
            durations_ms=durations_ms,
            token_usages=token_usages,
            errors=errors
        )

    duration_ms = int((time.time() - t_start) * 1000)
    
    total_tasks = len(suite_tasks)
    avg_pass_at_k = sum(r.pass_at_k for r in task_results.values()) / total_tasks if total_tasks > 0 else 0.0

    return EvaluationResult(
        suite_id=suite_id,
        config=config,
        total_tasks=total_tasks,
        passed_tasks=passed_tasks_count,
        average_pass_at_k=avg_pass_at_k,
        total_tokens=total_tokens,
        total_cost=total_cost,
        duration_ms=duration_ms,
        task_results=task_results
    )
