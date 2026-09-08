# tests/unit/test_concurrency_limiter.py
from concurrent.futures import ThreadPoolExecutor
from backend.core.concurrency import AnalysisSlotManager


class TestConcurrencyLimiterUnit:
    """Unit tests for lifecycle-safe AnalysisSlotManager."""

    def test_slot_acquisition_and_release_lifecycle(self):
        manager = AnalysisSlotManager(max_concurrent=2)
        assert manager.active_slots == 0
        assert manager.available_slots == 2

        # Acquire Slot 1
        assert manager.try_acquire() is True
        assert manager.active_slots == 1
        assert manager.available_slots == 1

        # Acquire Slot 2
        assert manager.try_acquire() is True
        assert manager.active_slots == 2
        assert manager.available_slots == 0

        # Attempt Slot 3 (Exhausted) -> Must return False
        assert manager.try_acquire() is False
        assert manager.active_slots == 2

        # Release Slot
        manager.release()
        assert manager.active_slots == 1
        assert manager.available_slots == 1

        # Now Slot 3 can be acquired
        assert manager.try_acquire() is True
        assert manager.active_slots == 2

        # Release all
        manager.release()
        manager.release()
        assert manager.active_slots == 0

        # Excessive release should clamp safely at 0
        manager.release()
        assert manager.active_slots == 0

    def test_guaranteed_release_on_exception(self):
        manager = AnalysisSlotManager(max_concurrent=1)

        def mock_failing_operation():
            if not manager.try_acquire():
                raise RuntimeError("No slots")
            try:
                raise ValueError("Simulated ML inference crash")
            finally:
                manager.release()

        try:
            mock_failing_operation()
        except ValueError:
            pass

        # Verify active slots returned to 0
        assert manager.active_slots == 0
        assert manager.available_slots == 1
        assert manager.try_acquire() is True
        manager.release()

    def test_multi_threaded_concurrency_protection(self):
        manager = AnalysisSlotManager(max_concurrent=3)
        acquired_slots = []

        def worker(worker_id):
            acquired = manager.try_acquire()
            if acquired:
                acquired_slots.append(worker_id)
            return acquired

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(worker, range(20)))

        success_count = sum(1 for r in results if r is True)
        assert success_count == 3
        assert manager.active_slots == 3

        # Release all acquired slots
        for _ in range(success_count):
            manager.release()

        assert manager.active_slots == 0
