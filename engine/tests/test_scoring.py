"""Integration tests for SandBench benchmark scoring.

Requires a running Docker daemon and the sandbench/python:golden image.
Run with: pytest -m integration engine/tests/test_scoring.py
"""
import pytest
from scoring import registry, score

CORRECT_FIZZBUZZ = """
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
            out.append(i)
    return out
"""

PARTIAL_FIZZBUZZ = """
def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        # Incorrectly missing Fizz Buzz logic for 15, 3, 5
        out.append(i)
    return out
"""

BROKEN_FIZZBUZZ = """
def fizzbuzz(n):
    # Syntax error
    return
    def incorrect(
"""

@pytest.mark.integration
def test_score_correct_fizzbuzz():
    task = registry.get_task("fizzbuzz")
    assert task is not None
    res = score.score_submission(CORRECT_FIZZBUZZ, task)
    assert res["score"] == 1.0
    assert res["passed"] == 5
    assert res["total"] == 5

@pytest.mark.integration
def test_score_partial_fizzbuzz():
    task = registry.get_task("fizzbuzz")
    assert task is not None
    res = score.score_submission(PARTIAL_FIZZBUZZ, task)
    # The partial fizzbuzz will fail test_multiples_of_3, test_multiples_of_5, test_multiples_of_15, test_full_sequence.
    # It passes test_plain_numbers.
    assert res["score"] == 0.2
    assert res["passed"] == 1
    assert res["total"] == 5

@pytest.mark.integration
def test_score_broken_fizzbuzz():
    task = registry.get_task("fizzbuzz")
    assert task is not None
    res = score.score_submission(BROKEN_FIZZBUZZ, task)
    assert res["score"] == 0.0
    assert res["passed"] == 0
    assert res["total"] == 5
