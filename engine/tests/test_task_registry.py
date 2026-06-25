"""Tests for the task registry — validates all tasks load and pass metadata checks."""
from scoring import registry


# All expected task IDs (3 original + 7 new)
EXPECTED_TASK_IDS = {
    "fizzbuzz",
    "json-flatten",
    "rate-limiter",
    "config-parser",
    "lru-cache",
    "csv-pipeline",
    "jwt-validator",
    "rest-api-parser",
    "sql-injection-fix",
    "async-rate-limiter",
}


def test_all_tasks_loaded():
    """Registry must contain all expected tasks."""
    tasks = registry.load_tasks()
    assert EXPECTED_TASK_IDS.issubset(set(tasks.keys())), (
        f"Missing tasks: {EXPECTED_TASK_IDS - set(tasks.keys())}"
    )


def test_minimum_task_count():
    """We must have at least 10 benchmark tasks."""
    tasks = registry.load_tasks()
    assert len(tasks) >= 10, f"Only {len(tasks)} tasks found, expected >= 10"


def test_task_registry_has_benchmark_metadata():
    """Every task must have complete benchmark metadata."""
    tasks = registry.load_tasks()

    assert len(tasks) == len({task.id for task in tasks.values()})

    for task in tasks.values():
        assert task.suite, f"{task.id}: missing suite"
        assert task.capability, f"{task.id}: missing capability"
        assert task.tags, f"{task.id}: missing tags"
        assert task.source, f"{task.id}: missing source"
        assert task.version, f"{task.id}: missing version"
        assert task.hidden_test_files > 0, f"{task.id}: no hidden test files"
        assert task.human_baseline_minutes is None or task.human_baseline_minutes > 0
        assert task.language in registry.SUPPORTED_LANGUAGES
        assert task.difficulty in registry.SUPPORTED_DIFFICULTIES
        assert not task.entrypoint.startswith("/")
        assert ".." not in task.entrypoint.replace("\\", "/").split("/")
        assert any("/workspace/tests" in arg for arg in task.test_command)


def test_public_task_shape_hides_internal_paths():
    """Public task representation must not expose internal filesystem paths."""
    public_tasks = registry.load_public_tasks()

    assert public_tasks
    for task in public_tasks:
        assert "tests_dir" not in task
        assert "hidden_test_files" in task
        assert "benchmark_ready" in task
        assert "safety_reviewed" in task
        assert "deterministic_scoring" in task
        assert isinstance(task["tags"], list)


def test_benchmark_ready_tasks_have_reference_solutions():
    """Tasks marked benchmark_ready must have reference solution hashes."""
    tasks = registry.load_tasks()
    ready_tasks = {tid: t for tid, t in tasks.items() if t.benchmark_ready}

    assert len(ready_tasks) > 0, "No benchmark-ready tasks found"

    for task in ready_tasks.values():
        assert task.reference_solution_hash is not None, (
            f"{task.id}: benchmark_ready but no reference solution hash"
        )
        assert task.human_baseline_minutes is not None, (
            f"{task.id}: benchmark_ready but no human_baseline_minutes"
        )
        assert task.safety_reviewed is True, (
            f"{task.id}: benchmark_ready but safety_reviewed is not true"
        )
        assert task.deterministic_scoring is True, (
            f"{task.id}: benchmark_ready but deterministic_scoring is not true"
        )


def test_validate_all_returns_no_issues():
    """validate_all() should report no issues for the current registry."""
    issues = registry.validate_all(strict=False)
    assert issues == [], f"Registry validation issues: {issues}"


def test_validate_all_strict():
    """Strict validation should pass for benchmark-ready tasks."""
    issues = registry.validate_all(strict=True)
    assert issues == [], f"Strict validation issues: {issues}"


def test_difficulty_distribution():
    """Registry should have tasks across multiple difficulty levels."""
    tasks = registry.load_tasks()
    difficulties = {t.difficulty for t in tasks.values()}
    assert "easy" in difficulties, "No easy tasks found"
    assert "medium" in difficulties, "No medium tasks found"
    assert "hard" in difficulties, "No hard tasks found"


def test_capability_diversity():
    """Registry should have tasks across multiple capability categories."""
    tasks = registry.load_tasks()
    capabilities = {t.capability for t in tasks.values()}
    assert len(capabilities) >= 5, f"Only {len(capabilities)} capability categories, expected >= 5"


def test_no_duplicate_task_ids():
    """All task IDs must be unique."""
    tasks = registry.load_tasks()
    ids = [t.id for t in tasks.values()]
    assert len(ids) == len(set(ids)), f"Duplicate task IDs found: {set(x for x in ids if ids.count(x) > 1)}"
