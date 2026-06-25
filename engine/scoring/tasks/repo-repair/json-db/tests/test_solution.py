import pytest
from db.storage import ThreadSafeStorage
from db.query import QueryEngine

@pytest.fixture
def populated_engine():
    storage = ThreadSafeStorage()
    storage.insert("1", {"name": "Alice", "profile": {"age": 30, "city": "NYC"}})
    storage.insert("2", {"name": "Bob", "profile": {"age": 25, "city": "LA"}})
    storage.insert("3", {"name": "Charlie", "profile": None})
    return QueryEngine(storage)

def test_flat_query(populated_engine):
    results = populated_engine.execute({"name": "Alice"})
    assert len(results) == 1
    assert results[0]["name"] == "Alice"

def test_nested_query(populated_engine):
    results = populated_engine.execute({"profile.city": "LA"})
    assert len(results) == 1
    assert results[0]["name"] == "Bob"

def test_nested_query_missing_intermediate(populated_engine):
    results = populated_engine.execute({"profile.age": 30})
    assert len(results) == 1
    assert results[0]["name"] == "Alice"

def test_nested_query_null_intermediate(populated_engine):
    results = populated_engine.execute({"profile.age": 25})
    assert len(results) == 1
    assert results[0]["name"] == "Bob"

def test_nonexistent_nested_path(populated_engine):
    results = populated_engine.execute({"profile.nonexistent": "val"})
    assert len(results) == 0
