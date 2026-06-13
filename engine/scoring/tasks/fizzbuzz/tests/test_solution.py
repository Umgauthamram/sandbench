"""Hidden test suite for the FizzBuzz benchmark task.

These tests are PRIVATE — copied into the sandbox at scoring time
and NEVER returned to the user or exposed via API.
"""
import importlib.util
import sys

import pytest


def _load_solution():
    """Load the user's solution module from /workspace/solution.py."""
    spec = importlib.util.spec_from_file_location("solution", "/workspace/solution.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["solution"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def solution():
    return _load_solution()


def test_multiples_of_3(solution):
    """Multiples of 3 (but not 5) should produce 'Fizz'."""
    result = solution.fizzbuzz(15)
    for i in [3, 6, 9, 12]:
        assert result[i - 1] == "Fizz", f"fizzbuzz(15)[{i - 1}] should be 'Fizz', got {result[i - 1]}"


def test_multiples_of_5(solution):
    """Multiples of 5 (but not 3) should produce 'Buzz'."""
    result = solution.fizzbuzz(15)
    for i in [5, 10]:
        assert result[i - 1] == "Buzz", f"fizzbuzz(15)[{i - 1}] should be 'Buzz', got {result[i - 1]}"


def test_multiples_of_15(solution):
    """Multiples of 15 should produce 'FizzBuzz'."""
    result = solution.fizzbuzz(15)
    assert result[14] == "FizzBuzz", f"fizzbuzz(15)[14] should be 'FizzBuzz', got {result[14]}"


def test_plain_numbers(solution):
    """Non-multiples of 3 or 5 should be the integer itself."""
    result = solution.fizzbuzz(15)
    for i in [1, 2, 4, 7, 8, 11, 13, 14]:
        assert result[i - 1] == i, f"fizzbuzz(15)[{i - 1}] should be {i}, got {result[i - 1]}"


def test_full_sequence(solution):
    """Full 1..15 sequence check."""
    expected = [
        1, 2, "Fizz", 4, "Buzz",
        "Fizz", 7, 8, "Fizz", "Buzz",
        11, "Fizz", 13, 14, "FizzBuzz",
    ]
    result = solution.fizzbuzz(15)
    assert result == expected, f"fizzbuzz(15) mismatch: got {result}"
