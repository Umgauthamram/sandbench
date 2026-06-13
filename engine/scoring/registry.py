"""Task registry for SandBench benchmark scoring.

Scans engine/scoring/tasks/*/task.yaml at module load time and exposes
a cached dictionary of Task objects keyed by task id.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

TASKS_DIR = Path(__file__).parent / "tasks"


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
            task = Task(
                id=data["id"],
                title=data["title"],
                language=data["language"],
                difficulty=data["difficulty"],
                description=data.get("description", ""),
                entrypoint=data.get("entrypoint", "solution.py"),
                test_command=data["test_command"],
                scorer=data.get("scorer", "pytest_fraction"),
                tests_dir=entry / "tests",
            )
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


def get_task(task_id: str) -> Optional[Task]:
    """Look up a single task by id. Returns None if not found."""
    return _registry.get(task_id)


def reload() -> None:
    """Re-scan the tasks directory. Useful during development."""
    global _registry
    _registry = _scan_tasks()
