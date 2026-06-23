"""Hidden test suite for the LRU cache benchmark task."""
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


def test_basic_get_put(solution):
    cache = solution.LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1


def test_eviction(solution):
    cache = solution.LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(3, 3)  # evicts key 1
    assert cache.get(1) == -1
    assert cache.get(3) == 3


def test_get_updates_recency(solution):
    cache = solution.LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.get(1)      # makes key 1 recently used
    cache.put(3, 3)   # should evict key 2, not 1
    assert cache.get(2) == -1
    assert cache.get(1) == 1


def test_update_existing_key(solution):
    cache = solution.LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(1, 10)  # update value
    assert cache.get(1) == 10
    cache.put(3, 3)   # evicts key 2 (1 was recently updated)
    assert cache.get(2) == -1


def test_missing_key_returns_negative_one(solution):
    cache = solution.LRUCache(1)
    assert cache.get(42) == -1


def test_capacity_one(solution):
    cache = solution.LRUCache(1)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == -1
    assert cache.get(2) == 2


def test_large_sequence(solution):
    cache = solution.LRUCache(3)
    for i in range(100):
        cache.put(i, i * 10)
    # Only last 3 should survive
    assert cache.get(99) == 990
    assert cache.get(98) == 980
    assert cache.get(97) == 970
    assert cache.get(96) == -1
