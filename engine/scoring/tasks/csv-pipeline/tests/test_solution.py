"""Hidden test suite for the CSV pipeline benchmark task."""
import importlib.util
import sys

import pytest


def _load_solution():
    spec = importlib.util.spec_from_file_location("solution", "/workspace/solution.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["solution"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def solution():
    return _load_solution()


SAMPLE_CSV = """name,department,salary
Alice,Engineering,95000
Bob,Engineering,88000
Carol,Marketing,72000
Dave,Marketing,78000
Eve,Engineering,102000"""


def test_department_count(solution):
    result = solution.transform_csv(SAMPLE_CSV)
    assert result["departments"]["Engineering"]["count"] == 3
    assert result["departments"]["Marketing"]["count"] == 2


def test_department_total_salary(solution):
    result = solution.transform_csv(SAMPLE_CSV)
    assert result["departments"]["Engineering"]["total_salary"] == 285000
    assert result["departments"]["Marketing"]["total_salary"] == 150000


def test_department_avg_salary(solution):
    result = solution.transform_csv(SAMPLE_CSV)
    assert result["departments"]["Engineering"]["avg_salary"] == 95000.0
    assert result["departments"]["Marketing"]["avg_salary"] == 75000.0


def test_department_employees(solution):
    result = solution.transform_csv(SAMPLE_CSV)
    assert set(result["departments"]["Engineering"]["employees"]) == {"Alice", "Bob", "Eve"}


def test_total_employees(solution):
    result = solution.transform_csv(SAMPLE_CSV)
    assert result["total_employees"] == 5


def test_highest_paid(solution):
    result = solution.transform_csv(SAMPLE_CSV)
    assert result["highest_paid"]["name"] == "Eve"
    assert result["highest_paid"]["salary"] == 102000.0


def test_empty_csv(solution):
    result = solution.transform_csv("")
    assert result["departments"] == {}
    assert result["total_employees"] == 0


def test_single_row(solution):
    csv_text = "name,department,salary\nAlice,Engineering,90000"
    result = solution.transform_csv(csv_text)
    assert result["total_employees"] == 1
    assert result["highest_paid"]["name"] == "Alice"
    assert result["departments"]["Engineering"]["avg_salary"] == 90000.0
