import pytest
from scoring import registry as task_registry
from scoring import score as scorer

@pytest.mark.integration
def test_json_db_scoring_correct():
    task = task_registry.get_task("json-db")
    assert task is not None
    
    # 1. Score broken code
    res_broken = scorer.score_submission(task.broken_code, task)
    assert res_broken["score"] < 1.0
    
    # 2. Score reference solution
    ref_path = task.tests_dir.parent / "reference.py"
    ref_code = ref_path.read_text(encoding="utf-8")
    res_correct = scorer.score_submission(ref_code, task)
    assert res_correct["score"] == 1.0
    assert res_correct["passed"] == res_correct["total"]

@pytest.mark.integration
def test_config_manager_scoring_correct():
    task = task_registry.get_task("config-manager")
    assert task is not None
    
    # 1. Score broken code
    res_broken = scorer.score_submission(task.broken_code, task)
    assert res_broken["score"] < 1.0
    
    # 2. Score reference solution
    ref_path = task.tests_dir.parent / "reference.py"
    ref_code = ref_path.read_text(encoding="utf-8")
    res_correct = scorer.score_submission(ref_code, task)
    assert res_correct["score"] == 1.0
    assert res_correct["passed"] == res_correct["total"]
