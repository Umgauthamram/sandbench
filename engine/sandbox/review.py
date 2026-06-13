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


def review_code(code: str, error_output: Optional[str] = None) -> Dict[str, Any]:
    """Analyze code and any associated runtime error outputs to generate a code review and patch.

    Args:
        code: The source code submission to analyze.
        error_output: Optional test failure traceback or runtime error string.

    Returns:
        A dictionary containing:
            - review_text: The textual code review / issues identified.
            - patch: A unified-diff style code patch suggestion, if applicable.
    """
    logger.info("Starting LLM code review using provider: %s", LLM_PROVIDER)

    prompt = (
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
            "review_text": "Error: Gemini API key is missing. Cannot perform code review.",
            "patch": ""
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
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
            return {"review_text": "Error: No review candidates returned from Gemini API.", "patch": ""}
            
        content_parts = candidates[0].get("content", {}).get("parts", [])
        if not content_parts:
            return {"review_text": "Error: Empty content parts returned from Gemini API.", "patch": ""}
            
        text = content_parts[0].get("text", "")
        
        # Parse the structured JSON response
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback if model did not return valid JSON despite configuration
            return {
                "review_text": text,
                "patch": ""
            }

    except Exception as e:
        logger.exception("Gemini API call failed: %s", e)
        return {
            "review_text": f"Error calling Gemini API for code review: {str(e)}",
            "patch": ""
        }


def _call_local_provider(prompt: str) -> Dict[str, Any]:
    """Call the OpenAI-compatible local model completions endpoint (e.g. llama.cpp or Ollama)."""
    if not MODEL_ENDPOINT_URL:
        logger.error("MODEL_ENDPOINT_URL environment variable is not set for local provider")
        return {
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
            return {"review_text": "Error: No completions returned from local model endpoint.", "patch": ""}

        content = choices[0].get("message", {}).get("content", "")
        
        # Parse the structured JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "review_text": content,
                "patch": ""
            }

    except Exception as e:
        logger.exception("Local model endpoint API call failed: %s", e)
        return {
            "review_text": f"Error calling local model endpoint: {str(e)}",
            "patch": ""
        }
