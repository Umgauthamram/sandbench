"""Hidden test suite for the SQL injection fix benchmark task."""
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


def test_simple_select(solution):
    qb = solution.SafeQueryBuilder("users")
    query, params = qb.build()
    assert query == "SELECT * FROM users"
    assert params == []


def test_select_columns(solution):
    qb = solution.SafeQueryBuilder("users").select(["name", "email"])
    query, params = qb.build()
    assert query == "SELECT name, email FROM users"


def test_where_clause(solution):
    qb = solution.SafeQueryBuilder("users").where({"status": "active"})
    query, params = qb.build()
    assert "WHERE status = ?" in query
    assert "active" in params


def test_uses_placeholders_not_values(solution):
    qb = solution.SafeQueryBuilder("users").where({"name": "'; DROP TABLE users; --"})
    query, params = qb.build()
    assert "DROP" not in query
    assert "?" in query
    assert "'; DROP TABLE users; --" in params


def test_order_by(solution):
    qb = solution.SafeQueryBuilder("products").order_by("price", "DESC")
    query, params = qb.build()
    assert "ORDER BY price DESC" in query


def test_limit(solution):
    qb = solution.SafeQueryBuilder("logs").limit(10)
    query, params = qb.build()
    assert "LIMIT ?" in query
    assert 10 in params


def test_chained_query(solution):
    qb = (
        solution.SafeQueryBuilder("orders")
        .select(["id", "total"])
        .where({"status": "paid"})
        .order_by("total", "DESC")
        .limit(5)
    )
    query, params = qb.build()
    assert "SELECT id, total FROM orders" in query
    assert "WHERE status = ?" in query
    assert "ORDER BY total DESC" in query
    assert "LIMIT ?" in query


def test_injection_in_table_name_raises(solution):
    with pytest.raises(ValueError):
        solution.SafeQueryBuilder("users; DROP TABLE users")


def test_injection_in_column_name_raises(solution):
    with pytest.raises(ValueError):
        solution.SafeQueryBuilder("users").select(["name; DROP TABLE"])


def test_invalid_direction_raises(solution):
    with pytest.raises(ValueError):
        solution.SafeQueryBuilder("users").order_by("name", "SIDEWAYS")


def test_negative_limit_raises(solution):
    with pytest.raises(ValueError):
        solution.SafeQueryBuilder("users").limit(-1)


def test_multiple_where_conditions(solution):
    qb = solution.SafeQueryBuilder("users").where({"role": "admin", "active": True})
    query, params = qb.build()
    assert query.count("?") == 2
    assert len(params) == 2
