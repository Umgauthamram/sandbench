"""Reference solution for rate-limiter task."""
import time


class TokenBucketRateLimiter:
    def __init__(self, capacity, refill_rate):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets = {}

    def allow(self, key, now=None):
        if now is None:
            now = time.monotonic()

        if key not in self._buckets:
            self._buckets[key] = {"tokens": self.capacity, "last_time": now}

        bucket = self._buckets[key]

        # Refill based on elapsed time
        elapsed = now - bucket["last_time"]
        if elapsed > 0:
            refill = elapsed * self.refill_rate
            bucket["tokens"] = min(self.capacity, bucket["tokens"] + refill)
            bucket["last_time"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False
