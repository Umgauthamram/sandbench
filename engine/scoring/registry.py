"""Task registry for SandBench benchmark scoring.

Scans engine/scoring/tasks/*/task.yaml at module load time and exposes
a cached dictionary of Task objects keyed by task id.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

TASKS_DIR = Path(__file__).parent / "tasks"
SUPPORTED_LANGUAGES = {"python", "node"}
SUPPORTED_DIFFICULTIES = {"easy", "medium", "hard"}


@dataclass(frozen=True)
class Task:
    """A single benchmark task definition."""

    id: str
    title: str
    language: str
    difficulty: str
    description: str
    entrypoint: str
    test_command: List[str]
    scorer: str
    tests_dir: Path  # absolute path to the tests/ folder for this task
    broken_code: str = ""  # intentionally buggy seed for RL eval
    suite: str = "core"
    capability: str = "code_generation"
    tags: List[str] = field(default_factory=list)
    source: str = "sandbench"
    version: str = "0.1.0"
    human_baseline_minutes: Optional[int] = None
    hidden_test_files: int = 0
    benchmark_ready: bool = False


def _as_string_list(value: Any, field_name: str, yaml_path: Path) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{yaml_path}: {field_name} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _as_optional_positive_int(value: Any, field_name: str, yaml_path: Path) -> Optional[int]:
    if value is None:
        return None
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{yaml_path}: {field_name} must be a positive integer")
    return value


def _count_hidden_test_files(tests_dir: Path) -> int:
    if not tests_dir.is_dir():
        return 0
    return sum(
        1
        for path in tests_dir.rglob("test_*.py")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _validate_task_data(data: Dict[str, Any], yaml_path: Path) -> None:
    required = {
        "id",
        "title",
        "language",
        "difficulty",
        "description",
        "entrypoint",
        "test_command",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"{yaml_path}: missing required field(s): {', '.join(missing)}")

    language = str(data["language"]).lower()
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"{yaml_path}: unsupported language {language!r}")

    difficulty = str(data["difficulty"]).lower()
    if difficulty not in SUPPORTED_DIFFICULTIES:
        raise ValueError(f"{yaml_path}: unsupported difficulty {difficulty!r}")

    entrypoint = str(data["entrypoint"]).replace("\\", "/")
    entrypoint_parts = [part for part in entrypoint.split("/") if part]
    if entrypoint.startswith("/") or ".." in entrypoint_parts:
        raise ValueError(f"{yaml_path}: entrypoint must be a relative workspace path")

    test_command = data["test_command"]
    if not isinstance(test_command, list) or not all(isinstance(arg, str) for arg in test_command):
        raise ValueError(f"{yaml_path}: test_command must be a list of strings")
    if not any("/workspace/tests" in arg for arg in test_command):
        raise ValueError(f"{yaml_path}: test_command must target /workspace/tests")


def _scan_tasks() -> Dict[str, Task]:
    """Walk TASKS_DIR and parse every task.yaml into a Task."""
    registry: Dict[str, Task] = {}
    if not TASKS_DIR.is_dir():
        logger.warning("Tasks directory does not exist: %s", TASKS_DIR)
        return registry

    for entry in sorted(TASKS_DIR.iterdir()):
        yaml_path = entry / "task.yaml"
        if not entry.is_dir() or not yaml_path.is_file():
            continue
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError(f"{yaml_path}: task.yaml must contain a mapping")
            _validate_task_data(data, yaml_path)

            tests_dir = entry / "tests"
            task = Task(
                id=data["id"],
                title=data["title"],
                language=str(data["language"]).lower(),
                difficulty=str(data["difficulty"]).lower(),
                description=data.get("description", ""),
                entrypoint=data.get("entrypoint", "solution.py"),
                test_command=data["test_command"],
                scorer=data.get("scorer", "pytest_fraction"),
                tests_dir=tests_dir,
                broken_code=data.get("broken_code", "").strip(),
                suite=data.get("suite", "core"),
                capability=data.get("capability", "code_generation"),
                tags=_as_string_list(data.get("tags"), "tags", yaml_path),
                source=data.get("source", "sandbench"),
                version=str(data.get("version", "0.1.0")),
                human_baseline_minutes=_as_optional_positive_int(
                    data.get("human_baseline_minutes"),
                    "human_baseline_minutes",
                    yaml_path,
                ),
                hidden_test_files=_count_hidden_test_files(tests_dir),
                benchmark_ready=bool(data.get("benchmark_ready", False)),
            )
            if task.id in registry:
                raise ValueError(f"{yaml_path}: duplicate task id {task.id!r}")
            registry[task.id] = task
            logger.info("Loaded task: %s (%s)", task.id, task.title)
        except Exception as exc:
            logger.exception("Failed to load task from %s: %s", yaml_path, exc)

    logger.info("Task registry loaded: %d task(s)", len(registry))
    return registry


# Module-level cache — populated once on first import.
_registry: Dict[str, Task] = _scan_tasks()


def load_tasks() -> Dict[str, Task]:
    """Return the full task registry (cached)."""
    return dict(_registry)


def public_task(task: Task) -> Dict[str, Any]:
    """Return the Redis/API-safe task representation."""
    scorer_label = "fraction of unit tests passed" if task.scorer == "pytest_fraction" else task.scorer
    return {
        "id": task.id,
        "title": task.title,
        "language": task.language,
        "difficulty": task.difficulty,
        "description": task.description,
        "entrypoint": task.entrypoint,
        "scorer": scorer_label,
        "broken_code": task.broken_code,
        "suite": task.suite,
        "capability": task.capability,
        "tags": list(task.tags),
        "source": task.source,
        "version": task.version,
        "human_baseline_minutes": task.human_baseline_minutes,
        "hidden_test_files": task.hidden_test_files,
        "benchmark_ready": task.benchmark_ready,
    }


def load_public_tasks() -> List[Dict[str, Any]]:
    """Return all tasks as Redis/API-safe dictionaries."""
    return [public_task(task) for task in _registry.values()]


def get_task(task_id: str) -> Optional[Task]:
    """Look up a single task by id. Returns None if not found."""
    return _registry.get(task_id)


def reload() -> None:
    """Re-scan the tasks directory. Useful during development."""
    global _registry
    _registry = _scan_tasks()
