"""Hidden test suite for the JSON-flatten benchmark task.

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


def test_flat_dict(solution):
    """Already-flat dict should pass through unchanged."""
    assert solution.flatten({"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_single_nesting(solution):
    """One level of nesting should produce dot-delimited keys."""
    result = solution.flatten({"a": {"b": 1, "c": 2}})
    assert result == {"a.b": 1, "a.c": 2}


def test_deep_nesting(solution):
    """Multiple levels of nesting."""
    result = solution.flatten({"a": {"b": {"c": {"d": 42}}}})
    assert result == {"a.b.c.d": 42}


def test_list_values(solution):
    """Lists should be flattened using integer indices as key segments."""
    result = solution.flatten({"a": [10, 20, 30]})
    assert result == {"a.0": 10, "a.1": 20, "a.2": 30}


def test_mixed_nesting(solution):
    """Nested dicts and lists together."""
    obj = {"x": {"y": [{"z": 1}, {"z": 2}]}}
    result = solution.flatten(obj)
    assert result == {"x.y.0.z": 1, "x.y.1.z": 2}
