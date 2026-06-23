from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class AdapterCapabilities:
    supports_json_mode: bool
    supports_streaming: bool
    max_context_tokens: int

@dataclass
class GenerationResult:
    ok: bool
    content: str
    usage: Dict[str, Any] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost": 0.0
    })
    duration_ms: int = 0
    error: Optional[str] = None

class ModelAdapter(ABC):
    def __init__(self, name: str, provider: str):
        self.name = name
        self.provider = provider

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate a completion for the given prompt.
        
        Supported kwargs can include:
        - temperature (float)
        - response_format (dict, e.g. {"type": "json_object"})
        - timeout_s (int)
        - max_response_bytes (int)
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> AdapterCapabilities:
        """Return the capabilities of this adapter/model."""
        pass
