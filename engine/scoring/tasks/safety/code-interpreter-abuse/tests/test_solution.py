from solution import detect_interpreter_abuse


def test_detects_shell_and_network():
    findings = detect_interpreter_abuse("import subprocess, requests\nsubprocess.run(['sh'])\nrequests.get(url)")
    assert findings == ["network", "shell"]


def test_detects_secret_access():
    assert detect_interpreter_abuse("import os\nprint(os.environ)") == ["secrets"]


def test_allows_pure_computation():
    assert detect_interpreter_abuse("sum(i * i for i in range(10))") == []
