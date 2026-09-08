# backend/core/rate_limiter.py
import time
import threading
from typing import Dict, List, Tuple


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter.
    Designed for single-instance deployments to protect expensive AI inference.
    (Can be adapted to Redis backend for distributed deployments in future phases).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Check if a request under 'key' is permitted within the sliding window.
        Returns:
            Tuple[bool, int]: (is_allowed, retry_after_seconds)
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Clean timestamps older than the sliding window
            timestamps = self._requests.get(key, [])
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) < limit:
                valid_timestamps.append(now)
                self._requests[key] = valid_timestamps
                return True, 0
            else:
                self._requests[key] = valid_timestamps
                oldest = valid_timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return False, retry_after

    def reset(self, key: str = None) -> None:
        """Reset state for a specific key or all keys (useful for testing)."""
        with self._lock:
            if key:
                self._requests.pop(key, None)
            else:
                self._requests.clear()


# Global singleton instance
rate_limiter = InMemoryRateLimiter()


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int]:
    """Helper wrapper for global rate limiter instance."""
    return rate_limiter.is_allowed(key, limit, window_seconds)
