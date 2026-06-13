"""Integration tests for SandBench Verdict Engine.

Requires a running Docker daemon.
Run with: pytest -m integration engine/tests/test_verdict.py
"""
import pytest
import docker
import tempfile
from typing import Tuple, List

from sandbox import runner, static_gate, monitor
from sandbox.rules import Severity, Flag

# Initialize Docker client for checks in tests
client = docker.from_env()


def run_pipeline(code: str, language: str = "python") -> Tuple[str, List[Flag], bool]:
    """Execute the pipeline (static gate -> runner -> monitor).

    Returns:
        Tuple of (verdict, list of flags, container_was_created).
    """
    container_created = False
    
    # 1. Static gate
    with tempfile.TemporaryDirectory() as tmpdir:
        flags = static_gate.scan(code, language, tmpdir)

    if any(f.severity == Severity.HIGH for f in flags):
        return "malicious", flags, container_created

    # 2. Run container
    container_created = True
    run_res = runner.run(code, language)

    # 3. Monitor collection
    monitor_flags = monitor.collect(
        run_res.container_attrs,
        run_res.fs_diff,
        run_res.stdout,
        run_res.stderr,
        run_res.timed_out
    )
    flags.extend(monitor_flags)

    # 4. Compute verdict
    if any(f.severity == Severity.HIGH for f in flags):
        verdict = "malicious"
    elif run_res.exit_code != 0 or run_res.timed_out:
        verdict = "broken"
    else:
        verdict = "clean"

    return verdict, flags, container_created


@pytest.mark.integration
def test_fizzbuzz_clean():
    """1. print-based FizzBuzz -> verdict 'clean', flags == []"""
    code = """
def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out

print(fizzbuzz(15))
"""
    verdict, flags, created = run_pipeline(code, "python")
    assert created is True
    assert verdict == "clean"
    assert len(flags) == 0


@pytest.mark.integration
def test_division_by_zero_broken():
    """2. '1/0' -> verdict 'broken', no HIGH flags"""
    code = "1 / 0"
    verdict, flags, created = run_pipeline(code, "python")
    assert created is True
    assert verdict == "broken"
    assert not any(f.severity == Severity.HIGH for f in flags)


@pytest.mark.integration
def test_network_egress_malicious():
    """3. socket.create_connection(('1.2.3.4', 4444), timeout=3) -> verdict 'malicious', NET_EGRESS_ATTEMPT present"""
    code = """
import socket
try:
    socket.create_connection(("1.2.3.4", 4444), timeout=3)
except Exception as e:
    print(f"Socket connection exception: {e}")
"""
    verdict, flags, created = run_pipeline(code, "python")
    assert created is True
    assert verdict == "malicious"
    assert any(f.rule_id == "NET_EGRESS_ATTEMPT" for f in flags)


@pytest.mark.integration
def test_base64_exec_quarantined():
    """4. import base64; exec(base64.b64decode('cHJpbnQoMSk=')) -> verdict 'malicious' from STATIC GATE, assert no container created"""
    code = "import base64; exec(base64.b64decode('cHJpbnQoMSk='))"
    
    # Get active container count before execution
    initial_containers = client.containers.list(all=True, filters={"label": "sandbench=1"})
    
    verdict, flags, created = run_pipeline(code, "python")
    
    # Verify no container was created
    assert created is False
    assert verdict == "malicious"
    assert any(f.rule_id == "YARA_MATCH" for f in flags)
    
    # Assert via docker client that no new containers with label sandbench=1 were created or ran
    post_containers = client.containers.list(all=True, filters={"label": "sandbench=1"})
    assert len(post_containers) == len(initial_containers)


@pytest.mark.integration
def test_fork_bomb_malicious():
    """5. os.fork() in a while True loop -> verdict 'malicious', FORK_BOMB present, container destroyed"""
    code = """
import os
while True:
    os.fork()
"""
    # Get initial containers list
    initial_containers = client.containers.list(all=True, filters={"label": "sandbench=1"})
    
    verdict, flags, created = run_pipeline(code, "python")
    
    assert created is True
    assert verdict == "malicious"
    assert any(f.rule_id == "FORK_BOMB" for f in flags)
    
    # Assert that all containers created during the run were destroyed
    post_containers = client.containers.list(all=True, filters={"label": "sandbench=1"})
    assert len(post_containers) == len(initial_containers)
