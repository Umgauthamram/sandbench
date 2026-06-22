import pytest

from solution import TokenBucketRateLimiter


def test_capacity_is_consumed_before_denial():
    limiter = TokenBucketRateLimiter(capacity=3, refill_rate=1.0)

    assert [limiter.allow("alice", now=0.0) for _ in range(4)] == [
        True,
        True,
        True,
        False,
    ]


def test_keys_have_independent_buckets():
    limiter = TokenBucketRateLimiter(capacity=1, refill_rate=1.0)

    assert limiter.allow("alice", now=0.0) is True
    assert limiter.allow("alice", now=0.0) is False
    assert limiter.allow("bob", now=0.0) is True


def test_refills_fractionally_over_time():
    limiter = TokenBucketRateLimiter(capacity=2, refill_rate=0.5)

    assert limiter.allow("alice", now=0.0) is True
    assert limiter.allow("alice", now=0.0) is True
    assert limiter.allow("alice", now=1.0) is False
    assert limiter.allow("alice", now=2.0) is True


def test_refill_is_capped_at_capacity():
    limiter = TokenBucketRateLimiter(capacity=2, refill_rate=10.0)

    assert limiter.allow("alice", now=0.0) is True
    assert limiter.allow("alice", now=100.0) is True
    assert limiter.allow("alice", now=100.0) is True
    assert limiter.allow("alice", now=100.0) is False


def test_non_monotonic_time_does_not_grant_tokens():
    limiter = TokenBucketRateLimiter(capacity=1, refill_rate=10.0)

    assert limiter.allow("alice", now=10.0) is True
    assert limiter.allow("alice", now=9.0) is False


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=0, refill_rate=1.0)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=1, refill_rate=0.0)
