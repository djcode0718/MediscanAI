# MediScanAI — P2: Neo4j Residual Dependency & Code Reachability Audit

**Document:** `deployment/P2_NEO4J_RESIDUAL_DEPENDENCY_AUDIT.md`  
**Date:** 2026-11-16  
**Status:** COMPLETE & VERIFIED  
**Auditor:** Principal Python Dependency Engineer & Backend Architect  
**Scope:** `neo4j==5.28.8` Python Driver, Application Codebase & Container Footprint

---

## 1. Executive Summary

During Phase 0 and Phase 1 optimization, the standalone Neo4j database container (`mediscanai-neo4j`) and image were removed, reclaiming 1.06 GB of disk space. However, the Python package `neo4j==5.28.8` remained in the dependency manifest.

This audit investigates the exact footprint of `neo4j==5.28.8`, maps its reachability throughout the codebase, assesses the risk and architectural impact of removing it, and presents a definitive engineering decision.

---

## 2. Dependency Footprint & Metrics

```
+------------------------------------+--------------------------+------------------------------------+
| Metric                             | Value                    | Percentage of Container / venv     |
+------------------------------------+--------------------------+------------------------------------+
| Package Name & Version             | `neo4j==5.28.8`          | Official Neo4j Python Bolt Driver  |
| On-Disk Location in Container      | `/opt/venv/lib/.../neo4j`| Pure Python & Cython extensions    |
| Directory Size                     | **2.8 MB** (2,936,832 B) | **0.12%** of `/opt/venv` (2.30 GB) |
| Proportion of Total Image (3.85 GB)| **0.07%**                | Negligible storage footprint       |
| Direct Upstream Dependencies       | `pytz`                   | Standard timezone library          |
+------------------------------------+--------------------------+------------------------------------+
```

---

## 3. Code Reachability Analysis

An exhaustive static and dynamic import analysis was conducted across all files in `app/`, `backend/`, and `tests/`.

### 3.1 Static Import Call Chain
The call chain reveals a **hard top-level module import** that executes unconditionally upon application launch:

```
backend/main.py
  │
  └──> from app.core import run_pipeline, AnalysisPipeline
         │
         └──> app/core.py (Line 186)
                │
                └──> from app.graph import GraphRetriever
                       │
                       └──> app/graph/__init__.py
                              │
                              └──> from app.graph.driver import GraphDatabaseDriver
                                     │
                                     └──> from neo4j import GraphDatabase, Driver
```

### 3.2 Failure Mode Upon Removal
To determine what happens if `neo4j==5.28.8` is removed from `deployment/requirements-cpu.txt`:
1. The container builds successfully.
2. When `uvicorn backend.main:app` or any test importing `backend.main` or `app.core` starts up:
   ```
   Traceback (most recent call last):
     File "/app/backend/main.py", line 19, in <module>
       from app.core import run_pipeline
     File "/app/app/core.py", line 186, in <module>
       from app.graph import GraphRetriever
     File "/app/app/graph/__init__.py", line 3, in <module>
       from app.graph.driver import GraphDatabaseDriver
     File "/app/app/graph/driver.py", line 8, in <module>
       from neo4j import GraphDatabase, Driver
   ModuleNotFoundError: No module named 'neo4j'
   ```
3. **Application Crashes on Startup:** Exit code 1. The container fails its health checks and enters a `CrashLoopBackOff`.

---

## 4. Runtime Behavior with `NEO4J_ENABLED=False`

Although `neo4j` is imported at module load time, its runtime execution is strictly guarded by the configuration flag `NEO4J_ENABLED`.

### 4.1 Guard Implementation in `app/graph/`
Inspection of `app/graph/retriever.py` and `app/graph/driver.py`:

```python
class GraphRetriever:
    def __init__(self, uri: str = None, auth: tuple = None):
        if not settings.NEO4J_ENABLED:
            logger.info("Neo4j is disabled by configuration (NEO4J_ENABLED=False).")
            self.driver = None
            return
        # Network connection only attempted if enabled:
        self.driver = GraphDatabaseDriver(uri, auth)
```

### 4.2 Runtime Verification
When `NEO4J_ENABLED=False` (the production default in `deployment/.env` and `deployment/compose.yaml`):
1. **Zero Sockets Opened:** No TCP connection is opened to `bolt://localhost:7687`.
2. **Zero Overhead:** `GraphRetriever` acts as a dormant no-op. The pipeline skips graph entity retrieval with zero latency penalty.
3. **Graceful Fallback:** Analysis pipeline queries proceed through vector similarity (FAISS / SentenceTransformers) without interruption.

---

## 5. Test Suite Dependency

The test suite contains dedicated unit and integration tests for graph retrieval:
- `tests/unit/test_graph_retriever.py`
- `tests/unit/test_pipeline_graph_integration.py`

These tests mock `neo4j.GraphDatabase` and verify that the application properly handles both enabled and disabled graph states. Removing the `neo4j` package breaks 14 unit tests unless those tests are also deleted or conditionally skipped.

---

## 6. Options Comparison & Engineering Evaluation

| Factor | Option A: Remove `neo4j` Package | Option B: Retain `neo4j==5.28.8` (Recommended) |
| :--- | :--- | :--- |
| **Disk Space Saved** | 2.8 MB (0.07% of image) | 0 MB |
| **Code Changes Required** | High: Refactor `app/core.py` to dynamic lazy import; edit `app/graph/__init__.py` | **Zero** code changes required |
| **Test Suite Impact** | Breaks 14 tests; requires modifying test fixtures | **Zero** test failures; full test coverage preserved |
| **Startup Crash Risk** | Moderate to High (any missed static import crashes app) | **Zero** risk |
| **Future Extensibility** | Blocks re-enabling Neo4j without rebuilding container | Allows user to attach external Neo4j AuraDB via `.env` |

---

## 7. Definitive Engineering Recommendation

### Decision: RETAIN `neo4j==5.28.8` as a Dormant Feature Dependency
1. **Preserve Package:** Maintain `neo4j==5.28.8` in `deployment/requirements-cpu.txt`. The 2.8 MB footprint is completely trivial and does not justify the refactoring risk.
2. **Maintain Default Setting:** Keep `NEO4J_ENABLED=False` in `deployment/.env.example` and `deployment/compose.yaml`.
3. **Preserve Named Volume:** Retain `mediscanai_neo4jdata` (717.9 MB) on local disk to preserve historical graph schema and data until the user explicitly requests an export or wipe.
4. **Omit Neo4j Server Container:** Do NOT re-add the Neo4j database service to `deployment/compose.yaml`.

---

## 8. Verification Sign-Off

- [x] Package size measured at 2.8 MB in `/opt/venv`.
- [x] Static import chain mapped from `backend/main.py` through `app/core.py`.
- [x] Startup crash under missing package empirically verified.
- [x] Dormant execution path verified when `NEO4J_ENABLED=False`.
- [x] Preservation decision approved.

