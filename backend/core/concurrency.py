# backend/core/concurrency.py
import threading
import logging
from typing import Optional

logger = logging.getLogger("mediscanai.concurrency")


class AnalysisSlotManager:
    """
    Lifecycle-safe bounded concurrency limiter for expensive local ML inference workloads.
    
    Protects local compute resources (RAM, CPU, GPU) from exhaustion under burst concurrent traffic
    by limiting the number of simultaneously executing analysis tasks.
    
    Uses thread-safe locking so it remains fully functional across multiple threads,
    event loops, and test runners (e.g. pytest event loops) without cross-loop binding errors.
    """

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max(1, max_concurrent)
        self._active_slots = 0
        self._sync_lock = threading.Lock()

    @property
    def active_slots(self) -> int:
        with self._sync_lock:
            return self._active_slots

    @property
    def available_slots(self) -> int:
        with self._sync_lock:
            return max(0, self.max_concurrent - self._active_slots)

    def try_acquire(self) -> bool:
        """
        Attempts to acquire an analysis execution slot atomically.
        Returns True if a slot was acquired, False if the system is at capacity.
        """
        with self._sync_lock:
            if self._active_slots < self.max_concurrent:
                self._active_slots += 1
                logger.info(
                    f"Acquired ML analysis slot. Active: {self._active_slots}/{self.max_concurrent}"
                )
                return True
            logger.warning(
                f"ML analysis capacity reached ({self._active_slots}/{self.max_concurrent}). Rejecting new request."
            )
            return False

    def release(self) -> None:
        """
        Releases an analysis execution slot safely.
        Guarantees that active slots counter never drops below 0.
        """
        with self._sync_lock:
            if self._active_slots > 0:
                self._active_slots -= 1
                logger.info(
                    f"Released ML analysis slot. Active: {self._active_slots}/{self.max_concurrent}"
                )
            else:
                logger.warning("Attempted to release an analysis slot when active count is already 0.")

    def reset(self) -> None:
        """Reset active slots to 0 (useful for test teardown)."""
        with self._sync_lock:
            self._active_slots = 0


# Global singleton instance configured via settings
from backend.core.config import settings

slot_manager = AnalysisSlotManager(max_concurrent=settings.MAX_CONCURRENT_ANALYSES)
