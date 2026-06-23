"""Hidden test suite for the config-parser benchmark task.

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


def test_simple_section(solution):
    """Single section with key-value pairs."""
    text = "[database]\nhost = localhost\nport = 5432"
    result = solution.parse_ini(text)
    assert result == {"database": {"host": "localhost", "port": "5432"}}


def test_multiple_sections(solution):
    """Multiple sections parsed correctly."""
    text = "[db]\nhost = localhost\n\n[cache]\nttl = 300"
    result = solution.parse_ini(text)
    assert "db" in result
    assert "cache" in result
    assert result["db"]["host"] == "localhost"
    assert result["cache"]["ttl"] == "300"


def test_comments_ignored(solution):
    """Lines starting with ; or # are comments."""
    text = "; this is a comment\n# another comment\n[app]\nname = test"
    result = solution.parse_ini(text)
    assert result == {"app": {"name": "test"}}


def test_empty_lines_skipped(solution):
    """Empty lines should not affect parsing."""
    text = "\n\n[section]\n\nkey = value\n\n"
    result = solution.parse_ini(text)
    assert result == {"section": {"key": "value"}}


def test_whitespace_stripping(solution):
    """Keys and values should have whitespace stripped."""
    text = "[section]\n  key  =  value with spaces  "
    result = solution.parse_ini(text)
    assert result["section"]["key"] == "value with spaces"


def test_global_keys(solution):
    """Keys before any section go under __global__."""
    text = "global_key = global_value\n[section]\nkey = value"
    result = solution.parse_ini(text)
    assert result["__global__"]["global_key"] == "global_value"
    assert result["section"]["key"] == "value"


def test_empty_input(solution):
    """Empty string returns empty dict."""
    result = solution.parse_ini("")
    assert result == {}


def test_value_with_equals(solution):
    """Values containing = should be handled correctly."""
    text = "[math]\nequation = a=b+c"
    result = solution.parse_ini(text)
    assert result["math"]["equation"] == "a=b+c"
