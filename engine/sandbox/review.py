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

    if LLM_PROVIDER.lower() == "local":
        return _call_local_provider(prompt)
    else:
        # Default is Gemini
        return _call_gemini_provider(prompt)


def _call_gemini_provider(prompt: str) -> Dict[str, Any]:
    """Call the hosted Google Gemini API directly using requests."""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY environment variable is not set")
        return {
            "ok": False,
            "review_text": "Error: Gemini API key is missing. Cannot perform code review.",
            "patch": ""
        }

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        res_json = response.json()
        
        # Extract response text from Gemini format
        candidates = res_json.get("candidates", [])
        if not candidates:
            return {"ok": False, "review_text": "Error: No review candidates returned from Gemini API.", "patch": ""}
            
        content_parts = candidates[0].get("content", {}).get("parts", [])
        if not content_parts:
            return {"ok": False, "review_text": "Error: Empty content parts returned from Gemini API.", "patch": ""}
            
        text = content_parts[0].get("text", "")
        
        # Parse the structured JSON response
        try:
            parsed = json.loads(text)
            parsed["ok"] = True
            return parsed
        except json.JSONDecodeError:
            # Fallback if model did not return valid JSON despite configuration
            return {
                "ok": True,
                "review_text": text,
                "patch": ""
            }

    except Exception as e:
        logger.exception("Gemini API call failed: %s", e)
        return {
            "ok": False,
            "review_text": f"Error calling Gemini API: {type(e).__name__}",
            "patch": ""
        }


def _call_local_provider(prompt: str) -> Dict[str, Any]:
    """Call the OpenAI-compatible local model completions endpoint (e.g. llama.cpp or Ollama)."""
    if not MODEL_ENDPOINT_URL:
        logger.error("MODEL_ENDPOINT_URL environment variable is not set for local provider")
        return {
            "ok": False,
            "review_text": "Error: Local model endpoint URL is missing. Cannot perform code review.",
            "patch": ""
        }

    # Normalize endpoint URL to ensure OpenAI-compatible completions endpoint
    base_url = MODEL_ENDPOINT_URL.rstrip("/")
    url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    payload = {
        "model": "fine-tuned-coder",  # Placeholder identifier for fine-tuned coder
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        res_json = response.json()

        # Extract OpenAI compatible completions format
        choices = res_json.get("choices", [])
        if not choices:
            return {"ok": False, "review_text": "Error: No completions returned from local model endpoint.", "patch": ""}

        content = choices[0].get("message", {}).get("content", "")
        
        # Parse the structured JSON response
        try:
            parsed = json.loads(content)
            parsed["ok"] = True
            return parsed
        except json.JSONDecodeError:
            return {
                "ok": True,
                "review_text": content,
                "patch": ""
            }

    except Exception as e:
        logger.exception("Local model endpoint API call failed: %s", e)
        return {
            "ok": False,
            "review_text": f"Error calling local model endpoint: {type(e).__name__}",
            "patch": ""
        }
