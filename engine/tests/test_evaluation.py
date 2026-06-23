import os
import json
import csv
import pytest
from pydantic import ValidationError

from evaluation.estimator import pass_at_k
from evaluation.models import EvaluationConfig, TaskResult, EvaluationResult
from evaluation.export import export_to_jsonl, export_to_csv, export_to_markdown
from scoring.schema import ResourceOverrides, TaskDefinition
from sandbox.runner import _clamp_mem

def test_pass_at_k():
    # Basic cases
    assert pass_at_k(5, 0, 1) == 0.0
    assert pass_at_k(5, 5, 1) == 1.0
    assert pass_at_k(5, 2, 1) == 0.4
    
    # Numerical validation of Codex paper formula: pass@k = 1 - C(n-c, k)/C(n, k)
    # n=5, c=2, k=2: C(3, 2)/C(5, 2) = 3 / 10 = 0.3. pass@k = 1 - 0.3 = 0.7
    assert abs(pass_at_k(5, 2, 2) - 0.7) < 1e-9
    
    # n=10, c=3, k=3: C(7, 3)/C(10, 3) = 35 / 120 = 7/24. pass@k = 1 - 7/24 = 17/24 = 0.708333...
    assert abs(pass_at_k(10, 3, 3) - 17.0/24.0) < 1e-9

    # Edge cases
    assert pass_at_k(0, 0, 1) == 0.0
    assert pass_at_k(5, -1, 1) == 0.0
    assert pass_at_k(5, 2, 0) == 0.0
    
    # k > n: if c > 0, pass@k is 1.0, otherwise 0.0
    assert pass_at_k(2, 1, 3) == 1.0
    assert pass_at_k(2, 0, 3) == 0.0
    
    # n - c < k: should be 1.0 (since all samples of size k must include at least one correct)
    assert pass_at_k(5, 4, 2) == 1.0 # 5 - 4 = 1 < 2

def test_resource_overrides_validation():
    # Valid configurations
    ro = ResourceOverrides(timeout_seconds=30, mem_limit="512m", cpus=1.0)
    assert ro.timeout_seconds == 30
    assert ro.mem_limit == "512m"
    assert ro.cpus == 1.0

    # Test validator ranges
    with pytest.raises(ValidationError):
        ResourceOverrides(timeout_seconds=90) # max 60s
    with pytest.raises(ValidationError):
        ResourceOverrides(cpus=5.0) # max 2.0
    with pytest.raises(ValidationError):
        ResourceOverrides(mem_limit="2g") # exceeds 1GB
    with pytest.raises(ValidationError):
        ResourceOverrides(mem_limit="1025m") # exceeds 1GB
    with pytest.raises(ValidationError):
        ResourceOverrides(mem_limit="invalid") # invalid format

def test_runner_mem_clamping():
    assert _clamp_mem("512m") == "512m"
    assert _clamp_mem("2g") == "1024m"
    assert _clamp_mem("1024m") == "1024m"

def test_evaluation_exports(tmp_path):
    # Set up mock EvaluationResult
    config = EvaluationConfig(
        suite_id="test-suite",
        adapter_name="test-model",
        provider="test-provider",
        k=1,
        n=5
    )
    
    task_res1 = TaskResult(
        task_id="task-1",
        n=5,
        c=2,
        pass_at_k=0.4,
        scores=[0.0, 1.0, 0.0, 1.0, 0.0],
        durations_ms=[500, 600, 500, 600, 500],
        token_usages=[{"total_tokens": 100}] * 5,
        errors=[None, None, None, None, None]
    )
    
    task_res2 = TaskResult(
        task_id="task-2",
        n=5,
        c=0,
        pass_at_k=0.0,
        scores=[0.0, 0.0, 0.0, 0.0, 0.0],
        durations_ms=[400, 400, 400, 400, 400],
        token_usages=[{"total_tokens": 80}] * 5,
        errors=["PatchApplyError", "PatchApplyError", "PatchApplyError", "PatchApplyError", "PatchApplyError"]
    )

    eval_result = EvaluationResult(
        suite_id="test-suite",
        config=config,
        total_tasks=2,
        passed_tasks=1,
        average_pass_at_k=0.2,
        total_tokens=900,
        total_cost=0.00018,
        duration_ms=5000,
        task_results={"task-1": task_res1, "task-2": task_res2}
    )

    # 1. JSONL Export
    jsonl_file = tmp_path / "result.jsonl"
    export_to_jsonl(eval_result, str(jsonl_file))
    assert jsonl_file.is_file()
    
    with open(jsonl_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        data1 = json.loads(lines[0])
        assert data1["task_id"] == "task-1"
        assert data1["pass_at_k"] == 0.4
        data2 = json.loads(lines[1])
        assert data2["task_id"] == "task-2"
        assert data2["pass_at_k"] == 0.0

    # 2. CSV Export
    csv_file = tmp_path / "result.csv"
    export_to_csv(eval_result, str(csv_file))
    assert csv_file.is_file()
    
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) == 3
        assert rows[0] == ["task_id", "score", "pass_at_k", "tokens", "duration"]
        # task-1 mean score = 0.4, pass@k = 0.4, mean tokens = 100, mean duration = 540
        assert rows[1][0] == "task-1"
        assert rows[1][1] == "0.4000"
        assert rows[1][2] == "0.4000"
        assert rows[1][3] == "100"
        assert rows[1][4] == "540"

    # 3. Markdown Export
    md_file = tmp_path / "result.md"
    export_to_markdown(eval_result, str(md_file))
    assert md_file.is_file()
    
    md_content = md_file.read_text(encoding="utf-8")
    assert "SandBench Evaluation Report" in md_content
    assert "Passed Tasks" in md_content
    assert "1 / 2" in md_content
