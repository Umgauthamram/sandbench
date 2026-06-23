import json
import time
import logging
import requests
from typing import Dict, Any, Optional

from adapters.base import ModelAdapter, GenerationResult, AdapterCapabilities
from sandbox import ssrf_guard

logger = logging.getLogger(__name__)

def estimate_gemini_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    # rates per 1,000,000 tokens
    rates = {
        "gemini-2.5-flash": (0.075, 0.30),
        "gemini-1.5-flash": (0.075, 0.30),
        "gemini-1.5-pro": (1.25, 5.00),
    }
    model_lower = model_name.lower()
    rate = (0.075, 0.30)  # default fallback
    for k, v in rates.items():
        if k in model_lower:
            rate = v
            break
    return (prompt_tokens / 1000000.0 * rate[0]) + (completion_tokens / 1000000.0 * rate[1])

class GeminiAdapter(ModelAdapter):
    def __init__(self, name: str, api_key: str, endpoint: Optional[str] = None, provider: str = "gemini"):
        super().__init__(name=name, provider=provider)
        self.api_key = api_key
        self.endpoint = endpoint or "https://generativelanguage.googleapis.com"
        
        # Statistics
        self.request_count = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_estimated_cost = 0.0
        self.error_categories = {
            "SSRFRejection": 0,
            "HTTPError": 0,
            "Timeout": 0,
            "JSONDecodeError": 0,
            "Other": 0
        }

    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        self.request_count += 1
        t0 = time.time()
        
        timeout_s = kwargs.get("timeout_s", 30)
        max_response_bytes = kwargs.get("max_response_bytes", 262144)
        response_format = kwargs.get("response_format", {"type": "json_object"})

        # 1. SSRF check on endpoint
        hostname, validated_ips, reason = ssrf_guard.resolve_safe(self.endpoint)
        if not hostname or not validated_ips:
            self.error_categories["SSRFRejection"] += 1
            duration_ms = int((time.time() - t0) * 1000)
            return GenerationResult(
                ok=False,
                content="",
                duration_ms=duration_ms,
                error=f"SSRFRejection: endpoint rejected - {reason}"
            )

        # 2. Construct API URL
        base = self.endpoint.rstrip("/")
        # Gemini url path format: /v1beta/models/{model_name}:generateContent
        # Or if the user already includes v1beta/models in the url, handle it
        if "generateContent" in base:
            url = base
        else:
            url = f"{base}/v1beta/models/{self.name}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
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
            "generationConfig": {}
        }
        
        if response_format and response_format.get("type") == "json_object":
            payload["generationConfig"]["responseMimeType"] = "application/json"

        session = requests.Session()
        try:
            response = session.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout_s,
                allow_redirects=False,
                stream=True
            )

            if 300 <= response.status_code < 400:
                self.error_categories["HTTPError"] += 1
                duration_ms = int((time.time() - t0) * 1000)
                return GenerationResult(
                    ok=False,
                    content="",
                    duration_ms=duration_ms,
                    error="HTTPError: redirects not allowed"
                )

            if response.status_code != 200:
                self.error_categories["HTTPError"] += 1
                duration_ms = int((time.time() - t0) * 1000)
                return GenerationResult(
                    ok=False,
                    content="",
                    duration_ms=duration_ms,
                    error=f"HTTPError: {response.status_code}"
                )

            # Cap response size
            content_bytes = bytearray()
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    content_bytes.extend(chunk)
                    if len(content_bytes) > max_response_bytes:
                        response.close()
                        self.error_categories["Other"] += 1
                        duration_ms = int((time.time() - t0) * 1000)
                        return GenerationResult(
                            ok=False,
                            content="",
                            duration_ms=duration_ms,
                            error="response too large"
                        )
            finally:
                response.close()

            body = bytes(content_bytes)
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                self.error_categories["JSONDecodeError"] += 1
                duration_ms = int((time.time() - t0) * 1000)
                return GenerationResult(
                    ok=False,
                    content="",
                    duration_ms=duration_ms,
                    error=f"JSONDecodeError: {type(e).__name__}"
                )

            candidates = data.get("candidates", [])
            if not candidates:
                self.error_categories["Other"] += 1
                duration_ms = int((time.time() - t0) * 1000)
                return GenerationResult(
                    ok=False,
                    content="",
                    duration_ms=duration_ms,
                    error="model response had no candidates"
                )

            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts:
                self.error_categories["Other"] += 1
                duration_ms = int((time.time() - t0) * 1000)
                return GenerationResult(
                    ok=False,
                    content="",
                    duration_ms=duration_ms,
                    error="model response content parts were empty"
                )

            content = content_parts[0].get("text", "")
            
            # Token usage & Cost estimation
            usage_metadata = data.get("usageMetadata", {})
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", prompt_tokens + completion_tokens)
            
            cost = estimate_gemini_cost(self.name, prompt_tokens, completion_tokens)
            
            # Update stats
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_estimated_cost += cost
            
            duration_ms = int((time.time() - t0) * 1000)
            return GenerationResult(
                ok=True,
                content=content,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost": cost
                },
                duration_ms=duration_ms
            )

        except requests.exceptions.Timeout as e:
            self.error_categories["Timeout"] += 1
            duration_ms = int((time.time() - t0) * 1000)
            return GenerationResult(
                ok=False,
                content="",
                duration_ms=duration_ms,
                error=f"Timeout: {type(e).__name__}"
            )
        except Exception as e:
            self.error_categories["Other"] += 1
            duration_ms = int((time.time() - t0) * 1000)
            logger.error("GeminiAdapter generate failed: %s", type(e).__name__)
            return GenerationResult(
                ok=False,
                content="",
                duration_ms=duration_ms,
                error=f"Other: {type(e).__name__}"
            )

    def get_capabilities(self) -> AdapterCapabilities:
        # Gemini models (2.5 flash, 1.5 pro) support responseMimeType="application/json"
        return AdapterCapabilities(
            supports_json_mode=True,
            supports_streaming=False,  # Not implemented in this direct REST call
            max_context_tokens=1048576  # Gemini 1.5 has 1M+ context window
        )
