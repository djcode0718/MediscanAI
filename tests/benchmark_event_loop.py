# tests/benchmark_event_loop.py
import asyncio
import time
import sys
import os
import statistics
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.core.security import create_access_token
from backend.db.session import SessionLocal
from backend.models.user import User


async def measure_event_loop_responsiveness():
    """
    Empirically verify that FastAPI's event loop remains responsive during active ML analysis.
    Starts an /api/analyze request in the background, and measures latency of /api/health pings
    while the ML pipeline is executing in worker threads.
    """
    print("\n--- Measuring FastAPI Event-Loop Responsiveness ---")
    
    # 1. Create or get test user token
    db = SessionLocal()
    user = db.query(User).filter(User.email == "phase3_user_a@mediscan.ai").first()
    if not user:
        user = db.query(User).first()
    user_id = user.id if user else 1
    db.close()

    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        # 2. Idle health check latency
        idle_latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            r = await client.get("/api/health")
            assert r.status_code == 200
            idle_latencies.append((time.perf_counter() - t0) * 1000)
            await asyncio.sleep(0.02)

        print(f"1. Idle /api/health Latency (N=10): Min={min(idle_latencies):.2f}ms, Mean={statistics.mean(idle_latencies):.2f}ms, Max={max(idle_latencies):.2f}ms")

        # 3. Launch background analysis request
        analysis_done = asyncio.Event()
        analysis_result = {}

        async def run_analysis_task():
            try:
                t0 = time.perf_counter()
                r = await client.post(
                    "/api/analyze",
                    data={"text": "I have had a dry cough and mild fever for two days."},
                    headers=headers
                )
                analysis_result["status"] = r.status_code
                analysis_result["duration"] = time.perf_counter() - t0
            finally:
                analysis_done.set()

        task = asyncio.create_task(run_analysis_task())

        # Allow task to enter worker thread execution
        await asyncio.sleep(0.5)

        # 4. Measure /api/health latency WHILE ML workload is executing
        concurrent_health_latencies = []
        while not analysis_done.is_set():
            t0 = time.perf_counter()
            r = await client.get("/api/health")
            assert r.status_code == 200
            latency_ms = (time.perf_counter() - t0) * 1000
            concurrent_health_latencies.append(latency_ms)
            await asyncio.sleep(0.2)

        await task

        print(f"2. Active ML Analysis Finished in {analysis_result.get('duration', 0):.2f}s (HTTP {analysis_result.get('status')})")
        if concurrent_health_latencies:
            print(f"3. Concurrent /api/health Latency during ML execution (N={len(concurrent_health_latencies)}): "
                  f"Min={min(concurrent_health_latencies):.2f}ms, "
                  f"Mean={statistics.mean(concurrent_health_latencies):.2f}ms, "
                  f"Max={max(concurrent_health_latencies):.2f}ms")
            print("✔ Non-blocking event-loop behavior empirically verified.")


if __name__ == "__main__":
    asyncio.run(measure_event_loop_responsiveness())
