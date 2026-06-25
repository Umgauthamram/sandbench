"""Tests for the Pydantic schema models in scoring.schema."""
import pytest
from scoring.schema import (
    TaskDefinition,
    RunManifest,
    ScoreBreakdown,
    RepairResult,
    SecurityFlag,
    TaskSuite,
    validate_benchmark_readiness,
    BenchmarkReadinessError,
)


# ---------------------------------------------------------------------------
# TaskDefinition tests
# ---------------------------------------------------------------------------


def test_valid_task_definition():
    """A fully populated TaskDefinition should validate."""
    td = TaskDefinition(
        id="test-task",
        title="Test Task",
        language="python",
        difficulty="medium",
        description="A test task for validation purposes.",
        entrypoint="solution.py",
        test_command=["python", "-m", "pytest", "/workspace/tests/"],
        suite="core",
        capability="code_generation",
        tags=["python", "test"],
        human_baseline_minutes=10,
    )
    assert td.id == "test-task"
    assert td.language == "python"


def test_task_id_must_be_kebab_case():
    """Task IDs must be kebab-case."""
    with pytest.raises(ValueError, match="kebab-case"):
        TaskDefinition(
            id="Invalid_Task_ID",
            title="Test",
            language="python",
            difficulty="easy",
            description="A test task for validation",
            test_command=["pytest", "/workspace/tests/"],
        )


def test_task_id_allows_valid_kebab():
    """Valid kebab-case IDs should pass."""
    td = TaskDefinition(
        id="my-cool-task-123",
        title="Test",
        language="python",
        difficulty="easy",
        description="A test task for validation",
        test_command=["pytest", "/workspace/tests/"],
    )
    assert td.id == "my-cool-task-123"


def test_entrypoint_rejects_absolute_path():
    """Entrypoint must be a relative path."""
    with pytest.raises(ValueError, match="relative"):
        TaskDefinition(
            id="test-task",
            title="Test",
            language="python",
            difficulty="easy",
            description="A test task for validation",
            test_command=["pytest", "/workspace/tests/"],
            entrypoint="/absolute/path.py",
        )


def test_entrypoint_rejects_path_traversal():
    """Entrypoint must not contain path traversal."""
    with pytest.raises(ValueError, match="relative"):
        TaskDefinition(
            id="test-task",
            title="Test",
            language="python",
            difficulty="easy",
            description="A test task for validation",
            test_command=["pytest", "/workspace/tests/"],
            entrypoint="../escape/path.py",
        )


def test_test_command_must_target_workspace():
    """test_command must include /workspace/tests."""
    with pytest.raises(ValueError, match="workspace/tests"):
        TaskDefinition(
            id="test-task",
            title="Test",
            language="python",
            difficulty="easy",
            description="A test task for validation",
            test_command=["pytest", "/some/other/path/"],
        )


def test_invalid_language_rejected():
    """Unsupported languages should be rejected."""
    with pytest.raises(ValueError):
        TaskDefinition(
            id="test-task",
            title="Test",
            language="rust",
            difficulty="easy",
            description="A test task for validation",
            test_command=["pytest", "/workspace/tests/"],
        )


def test_invalid_difficulty_rejected():
    """Unsupported difficulty levels should be rejected."""
    with pytest.raises(ValueError):
        TaskDefinition(
            id="test-task",
            title="Test",
            language="python",
            difficulty="nightmare",
            description="A test task for validation",
            test_command=["pytest", "/workspace/tests/"],
        )


# ---------------------------------------------------------------------------
# Benchmark readiness tests
# ---------------------------------------------------------------------------


def test_benchmark_readiness_passes():
    """Task with all requirements should pass readiness check."""
    td = TaskDefinition(
        id="ready-task",
        title="Ready Task",
        language="python",
        difficulty="medium",
        description="A sufficiently long description for this task.",
        test_command=["pytest", "/workspace/tests/"],
        tags=["python", "test"],
        human_baseline_minutes=15,
        safety_reviewed=True,
        deterministic_scoring=True,
    )
    reasons = validate_benchmark_readiness(td, hidden_test_count=3, has_reference_solution=True)
    assert reasons == []


def test_benchmark_readiness_fails_no_tests():
    """Readiness should fail without hidden tests."""
    td = TaskDefinition(
        id="no-tests",
        title="No Tests",
        language="python",
        difficulty="easy",
        description="A sufficiently long description for this task.",
        test_command=["pytest", "/workspace/tests/"],
        tags=["test"],
        human_baseline_minutes=5,
        safety_reviewed=True,
        deterministic_scoring=True,
    )
    reasons = validate_benchmark_readiness(td, hidden_test_count=0, has_reference_solution=True)
    assert any("test" in r.lower() for r in reasons)


def test_benchmark_readiness_fails_no_reference():
    """Readiness should fail without reference solution."""
    td = TaskDefinition(
        id="no-ref",
        title="No Ref",
        language="python",
        difficulty="easy",
        description="A sufficiently long description for this task.",
        test_command=["pytest", "/workspace/tests/"],
        tags=["test"],
        human_baseline_minutes=5,
        safety_reviewed=True,
        deterministic_scoring=True,
    )
    reasons = validate_benchmark_readiness(td, hidden_test_count=3, has_reference_solution=False)
    assert any("reference" in r.lower() for r in reasons)


def test_benchmark_readiness_fails_no_baseline():
    """Readiness should fail without human baseline minutes."""
    td = TaskDefinition(
        id="no-baseline",
        title="No Baseline",
        language="python",
        difficulty="easy",
        description="A sufficiently long description for this task.",
        test_command=["pytest", "/workspace/tests/"],
        tags=["test"],
        safety_reviewed=True,
        deterministic_scoring=True,
    )
    reasons = validate_benchmark_readiness(td, hidden_test_count=3, has_reference_solution=True)
    assert any("baseline" in r.lower() for r in reasons)


def test_benchmark_readiness_requires_safety_review():
    """Readiness should fail without an explicit safety review flag."""
    td = TaskDefinition(
        id="no-safety-review",
        title="No Safety Review",
        language="python",
        difficulty="easy",
        description="A sufficiently long description for this task.",
        test_command=["pytest", "/workspace/tests/"],
        tags=["test"],
        human_baseline_minutes=5,
        deterministic_scoring=True,
    )
    reasons = validate_benchmark_readiness(td, hidden_test_count=3, has_reference_solution=True)
    assert any("safety_reviewed" in r for r in reasons)


def test_benchmark_readiness_requires_deterministic_scoring():
    """Readiness should fail without deterministic scoring verification."""
    td = TaskDefinition(
        id="no-determinism",
        title="No Determinism",
        language="python",
        difficulty="easy",
        description="A sufficiently long description for this task.",
        test_command=["pytest", "/workspace/tests/"],
        tags=["test"],
        human_baseline_minutes=5,
        safety_reviewed=True,
    )
    reasons = validate_benchmark_readiness(td, hidden_test_count=3, has_reference_solution=True)
    assert any("deterministic_scoring" in r for r in reasons)


# ---------------------------------------------------------------------------
# RunManifest tests
# ---------------------------------------------------------------------------


def test_run_manifest_creation():
    """A RunManifest should be creatable with minimal fields."""
    manifest = RunManifest(run_id="run_abc123")
    assert manifest.run_id == "run_abc123"
    assert manifest.status == "queued"
    assert manifest.created_at is not None


def test_run_manifest_to_redis_dict():
    """to_redis_dict() should produce JSON-serializable output."""
    manifest = RunManifest(
        run_id="run_test",
        task_id="fizzbuzz",
        score=0.8,
        status="done",
        verdict="clean",
        score_breakdown=ScoreBreakdown(passed=4, total=5, score=0.8),
    )
    d = manifest.to_redis_dict()
    assert d["run_id"] == "run_test"
    assert d["score"] == 0.8
    assert d["score_breakdown"]["passed"] == 4

    # Must be JSON serializable
    import json
    json.dumps(d)


def test_run_manifest_with_repair():
    """Manifest with repair data should serialize correctly."""
    manifest = RunManifest(
        run_id="run_repair",
        repair=RepairResult(
            attempted=True,
            applied=True,
            method="unified_diff",
            score_before=0.4,
            score_after=0.8,
            reward=0.4,
        ),
    )
    d = manifest.to_redis_dict()
    assert d["repair"]["attempted"] is True
    assert d["repair"]["reward"] == 0.4


def test_run_manifest_with_flags():
    """Manifest with security flags should serialize correctly."""
    manifest = RunManifest(
        run_id="run_flagged",
        flags=[
            SecurityFlag(rule_id="SUSPICIOUS_IMPORT", severity="medium", detail="os module used"),
        ],
    )
    d = manifest.to_redis_dict()
    assert len(d["flags"]) == 1
    assert d["flags"][0]["rule_id"] == "SUSPICIOUS_IMPORT"


# ---------------------------------------------------------------------------
# TaskSuite tests
# ---------------------------------------------------------------------------


def test_task_suite_creation():
    """TaskSuite should be creatable with task IDs."""
    suite = TaskSuite(
        id="core",
        name="Core Benchmark Suite",
        version="0.1.0",
        task_ids=["fizzbuzz", "json-flatten", "rate-limiter"],
    )
    assert suite.id == "core"
    assert len(suite.task_ids) == 3
