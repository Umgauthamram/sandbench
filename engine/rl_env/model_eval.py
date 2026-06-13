"""Model-evaluation loop (Phase 2).

Runs a USER-SUPPLIED model as the repair agent against a benchmark task:

  1. Build the same review prompt the analysis engine uses.
  2. Call the user's model HOST-SIDE (guarded by ssrf_guard). On any failure,
     nothing is run in the sandbox.
  3. Drive the EXISTING SandbenchRepairEnv: reset() scores the baseline, then
     step(submit_patch) applies the model's patch inside the hardened sandbox
     and returns reward = score_after - score_before.

The sandbox stays network_mode=none throughout — only the model call (step 2)
touches the network, and it never happens inside the container.

KEY SAFETY: api_key is passed only to model_client and is never logged, never
placed in the returned dict, and not retained after the call.
"""
import json
import logging
from typing import Any, Dict

from scoring import registry as task_registry
from sandbox import model_client
from rl_env.env import SandbenchRepairEnv

logger = logging.getLogger(__name__)


def _build_review_prompt(code: str, error_output: str | None) -> str:
    """Replicate sandbox/review.py's review prompt verbatim.

    review.py builds this string inline inside review_code(); since that module
    must not be modified, the exact format is mirrored here.
    """
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


def run_model_eval(
    task_id: str,
    broken_code: str,
    endpoint: str,
    api_key: str,
    model_name: str = "user-model",
) -> Dict[str, Any]:
    """Run the user's model as a repair agent and score the improvement.

    Returns a dict; never contains api_key.
    """
    task = task_registry.get_task(task_id)
    if task is None:
        return {"status": "error", "reason": "unknown task", "reward": None}

    # Build the SAME review prompt the analysis engine uses. The baseline test
    # output is not yet known (the sandbox is not run before the model call, so
    # that "run NOTHING in the sandbox on failure" holds), so error_output=None.
    prompt = _build_review_prompt(broken_code, None)

    ok, content = model_client.call_user_model(
        endpoint,
        api_key,
        prompt,
        model_name=model_name,
    )
    # api_key is no longer needed past this point and is never retained.
    if not ok:
        return {
            "status": "quarantined",
            "reason": content,
            "reward": None,
            "score_before": None,
            "score_after": None,
            "patch_applied": False,
        }

    # Parse the model's JSON response; fall back to treating the whole content
    # as review text with no patch.
    review_text = ""
    patch = ""
    try:
        parsed = json.loads(content)
        patch = parsed.get("patch", "") or ""
        review_text = parsed.get("review_text", "") or ""
    except Exception:
        review_text = content
        patch = ""

    # Drive the EXISTING environment. reset() scores the baseline inside the
    # hardened sandbox; step(submit_patch) applies the patch and re-scores.
    env = SandbenchRepairEnv()
    env.reset(task_id, broken_code)
    score_before = env.score_before
    obs, reward, done, info = env.step({"type": "submit_patch", "patch": patch})
    score_after = obs["score"]

    patch_applied = info.get("method") is not None and "error" not in info

    return {
        "status": "done",
        "score_before": score_before,
        "score_after": score_after,
        "reward": round(reward, 4),
        "patch_applied": patch_applied,
        "method": info.get("method", "none"),
        "model_review_text": review_text[:2000],
    }