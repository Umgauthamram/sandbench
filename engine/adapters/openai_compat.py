import json
import time
import logging
import requests
from typing import Dict, Any, Optional

from adapters.base import ModelAdapter, GenerationResult, AdapterCapabilities
from sandbox import ssrf_guard

logger = logging.getLogger(__name__)

def estimate_openai_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    # rates per 1,000 tokens
    rates = {
        "gpt-4o-mini": (0.00015, 0.00060),
        "gpt-4o": (0.00500, 0.01500),
        "gpt-3.5-turbo": (0.00050, 0.00150),
    }
    model_lower = model_name.lower()
    rate = (0.00015, 0.00060)  # default fallback
    for k, v in rates.items():
        if k in model_lower:
            rate = v
            break
    return (prompt_tokens / 1000.0 * rate[0]) + (completion_tokens / 1000.0 * rate[1])

class OpenAICompatAdapter(ModelAdapter):
    def __init__(self, name: str, api_key: str, endpoint: Optional[str] = None, provider: str = "openai"):
        super().__init__(name=name, provider=provider)
        self.api_key = api_key
        # If no endpoint is provided, default to OpenAI's official endpoint
        self.endpoint = endpoint or "https://api.openai.com/v1"
        
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
        temperature = kwargs.get("temperature", 0.2)
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
                error=f"endpoint rejected: {reason}"
            )

        # 2. Normalize url
        base = self.endpoint.rstrip("/")
        if base.endswith("/chat/completions"):
            url = base
        elif base.endswith("/openai"):
            url = base + "/chat/completions"
        elif base.endswith("/v1"):
            url = base + "/chat/completions"
        else:
            url = base + "/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

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

            choices = data.get("choices", [])
            if not choices:
                self.error_categories["Other"] += 1
                duration_ms = int((time.time() - t0) * 1000)
                return GenerationResult(
                    ok=False,
                    content="",
                    duration_ms=duration_ms,
                    error="model response had no choices"
                )

            content = choices[0].get("message", {}).get("content", "")
            
            # Token usage & Cost estimation
            usage_data = data.get("usage", {})
            prompt_tokens = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)
            total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)
            
            cost = estimate_openai_cost(self.name, prompt_tokens, completion_tokens)
            
            # Update instance stats
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
                error=f"error: {type(e).__name__}"
            )
        except Exception as e:
            self.error_categories["Other"] += 1
            duration_ms = int((time.time() - t0) * 1000)
            logger.error("OpenAICompatAdapter generate failed: %s", type(e).__name__)
            return GenerationResult(
                ok=False,
                content="",
                duration_ms=duration_ms,
                error=f"error: {type(e).__name__}"
            )

    def get_capabilities(self) -> AdapterCapabilities:
        # Most OpenAI compat endpoints support JSON mode and streaming
        return AdapterCapabilities(
            supports_json_mode=True,
            supports_streaming=True,
            max_context_tokens=128000
        )
