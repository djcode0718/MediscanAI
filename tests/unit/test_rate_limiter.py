# tests/unit/test_rate_limiter.py
import time
from concurrent.futures import ThreadPoolExecutor
from backend.core.rate_limiter import InMemoryRateLimiter


class TestRateLimiterUnit:
    """Unit tests for sliding-window rate limiting algorithm and concurrency."""

    def test_sequential_rate_limiting_and_retry_after(self):
        limiter = InMemoryRateLimiter()
        key = "test_user_sequential"
        limit = 3
        window = 2

        # 3 allowed requests
        assert limiter.is_allowed(key, limit, window)[0] is True
        assert limiter.is_allowed(key, limit, window)[0] is True
        assert limiter.is_allowed(key, limit, window)[0] is True

        # 4th request must be rejected
        allowed, retry_after = limiter.is_allowed(key, limit, window)
        assert allowed is False
        assert retry_after >= 1

        # Wait for window to expire
        time.sleep(2.1)

        # Should be allowed again
        assert limiter.is_allowed(key, limit, window)[0] is True

    def test_thread_safety_concurrency(self):
        limiter = InMemoryRateLimiter()
        key = "concurrent_user"
        limit = 10
        window = 60

        def send_request(i):
            return limiter.is_allowed(key, limit, window)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(send_request, range(25)))

        allowed_count = sum(1 for allowed, _ in results if allowed)
        rejected_count = sum(1 for allowed, _ in results if not allowed)

        assert allowed_count == limit
        assert rejected_count == (25 - limit)
