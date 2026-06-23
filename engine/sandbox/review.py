"""LLM review and patch suggestion engine for SandBench.

Supports a provider switch (gemini vs local) to allow transparently replacing
the hosted Gemini API with a local fine-tuned model (e.g., via llama.cpp/Ollama)
without modifying client code.
"""
import json
import logging
from typing import Dict, Any, Optional

import requests

from config import LLM_PROVIDER, GEMINI_API_KEY, MODEL_ENDPOINT_URL

logger = logging.getLogger(__name__)


def review_code(code: str, error_output: Optional[str] = None, score_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyze code and any associated runtime error outputs to generate a code review and patch.

    Args:
        code: The source code submission to analyze.
        error_output: Optional test failure traceback or runtime error string.
        score_info: Optional dict with keys 'score', 'passed', 'total', 'raw_output'
                    from the hidden test suite scoring run.

    Returns:
        A dictionary containing:
            - review_text: The textual code review / issues identified.
            - patch: A unified-diff style code patch suggestion, if applicable.
    """
    logger.info("Starting LLM code review using provider: %s", LLM_PROVIDER)

    # Build the scoring context block if test results are available
    score_block = ""
    if score_info:
        passed = score_info.get("passed", 0)
        total = score_info.get("total", 0)
        score_val = score_info.get("score", 0.0)
        raw = score_info.get("raw_output", "")
        score_block = (
            f"\n--- HIDDEN TEST RESULTS ---\n"
            f"Score: {score_val:.0%} ({passed}/{total} tests passed)\n"
        )
        if raw:
            # Include up to 2000 chars of test output for context
            score_block += f"Test output:\n{raw[:2000]}\n"
        score_block += "\n"

    prompt = (
        "You are an expert security and code quality review agent for SandBench.\n"
        "Analyze the following user-submitted code, its runtime/test stderr output (if any), "
        "and the hidden test suite results (if provided).\n"
        "Provide a structured code review identifying the top issues/bugs and suggest a unified-diff format patch to fix them.\n"
        "IMPORTANT: If hidden test results show failing tests, focus your review on WHY the tests are failing and how to fix the code. "
        "Do NOT say the code 'looks good' if tests are failing.\n\n"
        f"--- USER SOURCE CODE ---\n{code}\n\n"
        f"--- RUNTIME STDERR ---\n{error_output or 'None (Code ran or is being reviewed statically)'}\n"
        f"{score_block}"
        "Format your output as a JSON object matching this structure:\n"
        "{\n"
        "  \"review_text\": \"Description of the main bugs, logic errors, or style issues found.\",\n"
        "  \"patch\": \"Unified diff string showing changes to apply, starting with +++ and --- lines, or empty string if no patch is needed.\"\n"
        "}"
    )

    from adapters.registry import create_adapter

    if LLM_PROVIDER.lower() == "local":
        adapter = create_adapter(
            provider="local",
            api_key="local-key",
            model_name="fine-tuned-coder",
            endpoint=MODEL_ENDPOINT_URL
        )
    else:
        adapter = create_adapter(
            provider="gemini",
            api_key=GEMINI_API_KEY,
            model_name="gemini-2.5-flash"
        )

    res = adapter.generate(
        prompt=prompt,
        response_format={"type": "json_object"},
        timeout_s=30
    )

    if not res.ok:
        return {
            "ok": False,
            "review_text": res.error or "Error calling model API",
            "patch": ""
        }

    try:
        parsed = json.loads(res.content)
        parsed["ok"] = True
        # Ensure review_text and patch are present
        if "review_text" not in parsed:
            parsed["review_text"] = res.content
        if "patch" not in parsed:
            parsed["patch"] = ""
        return parsed
    except json.JSONDecodeError:
        return {
            "ok": True,
            "review_text": res.content,
            "patch": ""
        }
