from scoring import registry


def test_task_registry_has_benchmark_metadata():
    tasks = registry.load_tasks()

    assert {"fizzbuzz", "json-flatten", "rate-limiter"}.issubset(tasks)
    assert len(tasks) == len({task.id for task in tasks.values()})

    for task in tasks.values():
        assert task.suite
        assert task.capability
        assert task.tags
        assert task.source
        assert task.version
        assert task.hidden_test_files > 0
        assert task.human_baseline_minutes is None or task.human_baseline_minutes > 0
        assert task.language in registry.SUPPORTED_LANGUAGES
        assert task.difficulty in registry.SUPPORTED_DIFFICULTIES
        assert not task.entrypoint.startswith("/")
        assert ".." not in task.entrypoint.replace("\\", "/").split("/")
        assert any("/workspace/tests" in arg for arg in task.test_command)


def test_public_task_shape_hides_internal_paths():
    public_tasks = registry.load_public_tasks()

    assert public_tasks
    for task in public_tasks:
        assert "tests_dir" not in task
        assert "hidden_test_files" in task
        assert "benchmark_ready" in task
        assert isinstance(task["tags"], list)
