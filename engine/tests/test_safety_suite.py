from sandbox.rules import make_flag
from safety.monitors import flags_to_trace
from safety.suite import SafetySuite, SafetyTaskResult


EXPECTED_SAFETY_TASKS = {
    "ssrf-exfil-attempt",
    "secret-in-output",
    "filesystem-escape",
    "fork-bomb-detect",
    "prompt-injection-basic",
    "prompt-injection-indirect",
    "code-interpreter-abuse",
    "obfuscated-payload",
    "dependency-confusion",
    "insecure-code-gen",
}


def test_safety_suite_discovers_phase3_tasks():
    suite = SafetySuite()
    task_ids = {task.id for task in suite.tasks()}

    assert EXPECTED_SAFETY_TASKS.issubset(task_ids)
    assert len(task_ids) >= 10


def test_safety_suite_aggregates_binary_scores():
    suite = SafetySuite()
    result = suite.aggregate(
        [
            SafetyTaskResult("safe-task", "network", True, "info"),
            SafetyTaskResult("unsafe-task", "filesystem", False, "high", ["escape"]),
        ]
    )

    assert result.total_tasks == 2
    assert result.passed_tasks == 1
    assert result.safety_score == 0.575
    assert result.severity_breakdown["high"] == 1


def test_flags_include_cwe_and_category_metadata():
    flag = make_flag("NET_EGRESS_ATTEMPT", "Network is unreachable")

    data = flag.to_dict()
    assert data["cwe"] == "CWE-918"
    assert data["category"] == "network"

    trace = flags_to_trace([flag])
    assert trace[0]["cwe"] == "CWE-918"
    assert trace[0]["category"] == "network"
