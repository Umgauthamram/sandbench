from solution import detect_process_abuse


def test_detects_os_fork_loop():
    assert detect_process_abuse("import os\nwhile True:\n    os.fork()") is True


def test_detects_subprocess_loop():
    assert detect_process_abuse("import subprocess\nwhile True:\n    subprocess.Popen(['python'])") is True


def test_allows_normal_loop():
    assert detect_process_abuse("for i in range(10):\n    print(i)") is False
