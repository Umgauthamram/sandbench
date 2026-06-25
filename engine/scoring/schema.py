"""Strict data contracts for SandBench benchmark tasks and run results.

Provides Pydantic models for:
- TaskDefinition: the full schema each task.yaml must satisfy
- TaskSuite: a named collection of tasks with versioning
- RunManifest: structured metadata produced after every scored run
- ScoreBreakdown: per-test pass/fail details within a run
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Language(str, Enum):
    PYTHON = "python"
    NODE = "node"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Capability(str, Enum):
    """Capability categories for benchmark tasks."""
    CODE_GENERATION = "code_generation"
    FUNCTION_CORRECTNESS = "function_correctness"
    DATA_TRANSFORMATION = "data_transformation"
    STATEFUL_SYSTEM_DESIGN = "stateful_system_design"
    SECURITY_FIX = "security_fix"
    CONCURRENCY = "concurrency"
    FILE_IO = "file_io"
    BACKEND_LOGIC = "backend_logic"
    SECURITY_AUTH = "security_auth"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    QUARANTINED = "quarantined"
    ERROR = "error"


class Verdict(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    BROKEN = "broken"
    MALICIOUS = "malicious"


# ---------------------------------------------------------------------------
# Resource Overrides
# ---------------------------------------------------------------------------

class ResourceOverrides(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=60)
    mem_limit: Optional[str] = Field(default=None)
    cpus: Optional[float] = Field(default=None, ge=0.1, le=2.0)

    @field_validator("mem_limit")
    @classmethod
    def validate_mem_limit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        import re
        match = re.match(r"^(\d+)([bkmg])$", v.lower())
        if not match:
            raise ValueError("mem_limit must be a number followed by b, k, m, or g")
        
        # Enforce max 1024m (1GB) limit
        value, unit = int(match.group(1)), match.group(2)
        bytes_limit = value
        if unit == 'k':
            bytes_limit *= 1024
        elif unit == 'm':
            bytes_limit *= 1024 * 1024
        elif unit == 'g':
            bytes_limit *= 1024 * 1024 * 1024
        
        if bytes_limit > 1024 * 1024 * 1024:
            raise ValueError("mem_limit exceeds maximum allowed ceiling of 1GB")
        
        return v


# ---------------------------------------------------------------------------
# Task Definition
# ---------------------------------------------------------------------------

class TaskDefinition(BaseModel):
    """Schema for a single benchmark task as defined in task.yaml.

    Every task.yaml in the registry MUST validate against this model.
    Fields marked as required will cause a validation error if missing.
    """
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., min_length=1, description="Unique task identifier (kebab-case)")
    title: str = Field(..., min_length=1, description="Human-readable task title")
    language: Language
    difficulty: Difficulty
    description: str = Field(..., min_length=10, description="Task description shown to users")
    entrypoint: str = Field(default="solution.py", description="Relative path to the entrypoint file")
    test_command: List[str] = Field(..., min_length=1, description="Command to run tests inside sandbox")
    scorer: str = Field(default="pytest_fraction", description="Scoring strategy identifier")

    # Benchmark metadata
    suite: str = Field(default="core", min_length=1)
    capability: str = Field(default="code_generation", min_length=1)
    tags: List[str] = Field(default_factory=list)
    source: str = Field(default="sandbench")
    version: str = Field(default="0.1.0")
    human_baseline_minutes: Optional[int] = Field(default=None, ge=1)
    benchmark_ready: bool = Field(default=False)
    safety_reviewed: bool = Field(
        default=False,
        description="True after benchmark maintainers complete a safety/data review.",
    )
    deterministic_scoring: bool = Field(
        default=False,
        description="True when scoring has been verified as deterministic.",
    )

    # RL / broken code seed
    broken_code: str = Field(default="")

    # Reference solution (hash of the known-good solution for integrity)
    reference_solution_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the reference solution file for integrity verification"
    )

    resource_overrides: Optional[ResourceOverrides] = Field(default=None)

    @field_validator("id")
    @classmethod
    def id_must_be_kebab_case(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(f"Task id must be kebab-case, got: {v!r}")
        return v

    @field_validator("entrypoint")
    @classmethod
    def entrypoint_must_be_relative(cls, v: str) -> str:
        normalized = v.replace("\\", "/")
        parts = [p for p in normalized.split("/") if p]
        if normalized.startswith("/") or ".." in parts:
            raise ValueError(f"entrypoint must be a relative workspace path, got: {v!r}")
        return v

    @field_validator("test_command")
    @classmethod
    def test_command_must_target_workspace_tests(cls, v: List[str]) -> List[str]:
        if not any("/workspace/tests" in arg for arg in v):
            raise ValueError("test_command must include a path targeting /workspace/tests")
        return v

    @field_validator("tags")
    @classmethod
    def tags_must_be_non_empty_strings(cls, v: List[str]) -> List[str]:
        cleaned = [tag.strip() for tag in v if tag.strip()]
        return cleaned


# ---------------------------------------------------------------------------
# Benchmark Readiness Validation
# ---------------------------------------------------------------------------

class BenchmarkReadinessError(Exception):
    """Raised when a task is marked benchmark_ready but fails readiness checks."""
    def __init__(self, task_id: str, reasons: List[str]):
        self.task_id = task_id
        self.reasons = reasons
        super().__init__(
            f"Task {task_id!r} fails benchmark-readiness: {'; '.join(reasons)}"
        )


def validate_benchmark_readiness(
    task_def: TaskDefinition,
    hidden_test_count: int,
    has_reference_solution: bool,
) -> List[str]:
    """Check whether a task meets benchmark-readiness requirements.

    Returns a list of failure reasons (empty = ready).
    """
    reasons: List[str] = []

    if hidden_test_count == 0:
        reasons.append("No hidden test files found")

    if not has_reference_solution:
        reasons.append("No reference solution file present")

    if task_def.human_baseline_minutes is None:
        reasons.append("human_baseline_minutes is not set")

    if not task_def.tags:
        reasons.append("No tags specified")

    if len(task_def.description) < 20:
        reasons.append("Description is too short (minimum 20 characters)")

    if not task_def.safety_reviewed:
        reasons.append("safety_reviewed must be true for benchmark-ready tasks")

    if not task_def.deterministic_scoring:
        reasons.append("deterministic_scoring must be true for benchmark-ready tasks")

    return reasons


# ---------------------------------------------------------------------------
# Run Manifest
# ---------------------------------------------------------------------------

class ScoreBreakdown(BaseModel):
    """Per-test pass/fail detail within a scored run."""
    passed: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_output: str = Field(default="", description="Truncated test output")


class RepairResult(BaseModel):
    """Outcome of the repair/re-score loop."""
    attempted: bool = False
    applied: bool = False
    method: str = "none"
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    reward: Optional[float] = None


class SecurityFlag(BaseModel):
    """A single security flag raised during static or dynamic analysis."""
    rule_id: str
    source: str = "static_gate"
    location: Optional[str] = None
    severity: str = "medium"
    detail: str = ""
    cwe: str = ""
    category: str = ""


class RunManifest(BaseModel):
    """Structured metadata produced after every scored run.

    This is the canonical record of a benchmark execution.
    It is stored alongside run results in Redis and used for
    leaderboard entries, artifact bundles, and audit trails.
    """
    run_id: str = Field(..., min_length=1)
    task_id: str = Field(default="")
    task_version: str = Field(default="0.1.0")
    suite: str = Field(default="core")

    # Execution context
    language: str = Field(default="python")
    sandbox_config_hash: Optional[str] = Field(
        default=None,
        description="Hash of the sandbox configuration used for this run"
    )
    model_adapter_name: Optional[str] = Field(
        default=None,
        description="Name of the model/adapter used (if model_eval)"
    )

    # Results
    status: RunStatus = RunStatus.QUEUED
    verdict: Optional[Verdict] = None
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    score_breakdown: Optional[ScoreBreakdown] = None
    flags: List[SecurityFlag] = Field(default_factory=list)
    monitorability_traces: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured runtime signals such as network, filesystem, and resource events",
    )

    # Timing
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: int = Field(default=0, ge=0)

    # Repair
    repair: Optional[RepairResult] = None

    # Submission metadata
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    submission_type: str = Field(default="code", description="code | files | model_eval")

    # Artifact integrity
    artifact_hashes: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of artifact name to SHA-256 hash"
    )

    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z"
    )

    def to_redis_dict(self) -> Dict[str, Any]:
        """Serialize to a dict suitable for Redis JSON storage."""
        return self.model_dump(mode="json", exclude_none=True)


# ---------------------------------------------------------------------------
# Task Suite
# ---------------------------------------------------------------------------

class TaskSuite(BaseModel):
    """A named, versioned collection of benchmark tasks."""
    id: str = Field(..., min_length=1, description="Suite identifier (e.g. 'core')")
    name: str = Field(..., min_length=1, description="Human-readable suite name")
    version: str = Field(default="0.1.0")
    description: str = Field(default="")
    task_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z"
    )
