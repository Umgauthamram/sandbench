"""Reference solution for async-rate-limiter task."""
import time
from collections import defaultdict


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict = defaultdict(list)

    async def is_allowed(self, key: str, now: float = None) -> bool:
        if now is None:
            now = time.monotonic()

        timestamps = self._timestamps[key]

        # Clean up old entries outside the window
        cutoff = now - self.window_seconds
        self._timestamps[key] = [t for t in timestamps if t > cutoff]
        timestamps = self._timestamps[key]

        if len(timestamps) >= self.max_requests:
            return False

        timestamps.append(now)
        return True
