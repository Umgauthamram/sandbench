from typing import List, Dict, Any, Optional

from adapters.base import ModelAdapter
from adapters.openai_compat import OpenAICompatAdapter
from adapters.gemini import GeminiAdapter

class AdapterRegistry:
    def __init__(self):
        self.adapters: List[ModelAdapter] = []

    def create_adapter(
        self,
        provider: str,
        api_key: str,
        model_name: str,
        endpoint: Optional[str] = None
    ) -> ModelAdapter:
        """Factory method to instantiate a model adapter by provider name."""
        provider_lower = provider.lower()
        if provider_lower == "gemini":
            adapter = GeminiAdapter(name=model_name, api_key=api_key, endpoint=endpoint)
        elif provider_lower in ("openai", "groq", "huggingface", "custom"):
            adapter = OpenAICompatAdapter(name=model_name, api_key=api_key, endpoint=endpoint, provider=provider_lower)
        else:
            # Fallback to OpenAICompat
            adapter = OpenAICompatAdapter(name=model_name, api_key=api_key, endpoint=endpoint, provider=provider_lower)
        
        self.adapters.append(adapter)
        return adapter

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Aggregate usage statistics across all created adapters."""
        total_calls = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cost = 0.0
        error_categories = {
            "SSRFRejection": 0,
            "HTTPError": 0,
            "Timeout": 0,
            "JSONDecodeError": 0,
            "Other": 0
        }

        for adapter in self.adapters:
            # Check if adapter has the tracking attributes
            request_count = getattr(adapter, "request_count", 0)
            total_calls += request_count
            total_prompt_tokens += getattr(adapter, "total_prompt_tokens", 0)
            total_completion_tokens += getattr(adapter, "total_completion_tokens", 0)
            total_cost += getattr(adapter, "total_estimated_cost", 0.0)
            
            adapter_errors = getattr(adapter, "error_categories", {})
            for k, v in adapter_errors.items():
                if k in error_categories:
                    error_categories[k] += v
                else:
                    error_categories[k] = v

        total_errors = sum(error_categories.values())
        error_rate = (total_errors / total_calls) if total_calls > 0 else 0.0

        return {
            "total_calls": total_calls,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "total_cost": total_cost,
            "error_rate": error_rate,
            "error_categories": error_categories
        }

# Global registry instance for convenience
registry = AdapterRegistry()

def create_adapter(
    provider: str,
    api_key: str,
    model_name: str,
    endpoint: Optional[str] = None
) -> ModelAdapter:
    return registry.create_adapter(provider, api_key, model_name, endpoint)
