from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class EvaluationConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    suite_id: str
    adapter_name: str
    provider: str
    k: int = 1
    n: int = 5
    timeout_overrides: Optional[Dict[str, int]] = None

class TaskResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    task_id: str
    n: int
    c: int
    pass_at_k: float
    scores: List[float]
    durations_ms: List[int]
    token_usages: List[Dict[str, Any]]
    errors: List[Optional[str]]

class EvaluationResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    suite_id: str
    config: EvaluationConfig
    total_tasks: int
    passed_tasks: int  # Tasks with c > 0
    average_pass_at_k: float
    total_tokens: int
    total_cost: float
    duration_ms: int
    task_results: Dict[str, TaskResult]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
