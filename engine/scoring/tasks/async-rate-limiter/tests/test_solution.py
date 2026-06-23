"""Hidden test suite for the async sliding window rate limiter benchmark task."""
import asyncio
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


@pytest.mark.asyncio
async def test_allows_within_limit(solution):
    limiter = solution.SlidingWindowLimiter(max_requests=3, window_seconds=10.0)
    assert await limiter.is_allowed("alice", now=0.0) is True
    assert await limiter.is_allowed("alice", now=1.0) is True
    assert await limiter.is_allowed("alice", now=2.0) is True


@pytest.mark.asyncio
async def test_denies_over_limit(solution):
    limiter = solution.SlidingWindowLimiter(max_requests=2, window_seconds=10.0)
    assert await limiter.is_allowed("alice", now=0.0) is True
    assert await limiter.is_allowed("alice", now=1.0) is True
    assert await limiter.is_allowed("alice", now=2.0) is False


@pytest.mark.asyncio
async def test_window_slides(solution):
    limiter = solution.SlidingWindowLimiter(max_requests=2, window_seconds=5.0)
    assert await limiter.is_allowed("alice", now=0.0) is True
    assert await limiter.is_allowed("alice", now=1.0) is True
    assert await limiter.is_allowed("alice", now=3.0) is False
    # After the window passes, old entries drop off
    assert await limiter.is_allowed("alice", now=6.0) is True


@pytest.mark.asyncio
async def test_independent_keys(solution):
    limiter = solution.SlidingWindowLimiter(max_requests=1, window_seconds=10.0)
    assert await limiter.is_allowed("alice", now=0.0) is True
    assert await limiter.is_allowed("alice", now=1.0) is False
    assert await limiter.is_allowed("bob", now=1.0) is True


@pytest.mark.asyncio
async def test_invalid_max_requests_raises(solution):
    with pytest.raises(ValueError):
        solution.SlidingWindowLimiter(max_requests=0, window_seconds=1.0)


@pytest.mark.asyncio
async def test_invalid_window_raises(solution):
    with pytest.raises(ValueError):
        solution.SlidingWindowLimiter(max_requests=1, window_seconds=0)


@pytest.mark.asyncio
async def test_burst_then_recovery(solution):
    limiter = solution.SlidingWindowLimiter(max_requests=3, window_seconds=2.0)
    # Burst at t=0
    assert await limiter.is_allowed("alice", now=0.0) is True
    assert await limiter.is_allowed("alice", now=0.1) is True
    assert await limiter.is_allowed("alice", now=0.2) is True
    assert await limiter.is_allowed("alice", now=0.3) is False
    # After full window, all should be allowed again
    assert await limiter.is_allowed("alice", now=3.0) is True
    assert await limiter.is_allowed("alice", now=3.1) is True
    assert await limiter.is_allowed("alice", now=3.2) is True
    assert await limiter.is_allowed("alice", now=3.3) is False
