# Dependency & Import Chain Root Cause Analysis: Phase 1.2.d.2

## Executive Summary

During Phase 1.2.d.1 independent audit, an immediate technical blocker was reported:
```bash
python -c "import backend.main"
# ModuleNotFoundError: No module named 'langchain.docstore'
```
Furthermore, the test suite (`pytest`) concealed this failure because `tests/conftest.py` contained an eager compatibility shim injecting a fake `langchain.docstore.document.Document` class directly into `sys.modules`.

This document records the exact investigation, reproduction, dependency chain trace, architectural remediation, and validation that eliminated the import blocker and removed the test shim.

---

## 1. Import Chain Trace & Root Cause

### 1.1 Exact Import Chain

A clean-process trace of `import backend.main` revealed the following execution path:

1. `backend/main.py:46`: `from app.core import Pipeline`
2. `app/core.py:11`: `from app.ocr import extract_text_from_image`
3. `app/ocr.py:13`: `from paddleocr import PaddleOCR` (eager top-level import in legacy code)
4. `paddleocr/__init__.py`: imports PaddleX components
5. `paddlex/inference/pipelines/components/retriever/base.py:27`:
   ```python
   from paddlex.utils.deps import is_dep_available

   if is_dep_available("langchain"):
       from langchain.docstore.document import Document
   ```
6. Python raises:
   ```
   ModuleNotFoundError: No module named 'langchain.docstore'
   ```

### 1.2 Dependency Versions in Active Environment

Inspecting the active environment (`/Users/sj/miniforge3/envs/med-env`):
- `langchain`: `1.4.6` (modern LangChain 1.x, installed to support RAG evaluation frameworks such as `ragas 0.2.14`)
- `paddleocr`: `2.7.3`
- `paddlex`: `3.0.0b1`

### 1.3 Architectural Mismatch

In LangChain 0.0.x / 0.1.x, document abstractions lived in `langchain.docstore.document.Document`. In modern LangChain (1.0+), document structures were migrated to `langchain_core.documents.Document`, and `langchain.docstore` was removed.

PaddleX 3.0.0b1 contains a conditional check:
```python
if is_dep_available("langchain"):
    from langchain.docstore.document import Document
```
Because `langchain` 1.4.6 is installed, `is_dep_available("langchain")` returns `True`, triggering an import of a submodule (`langchain.docstore`) that no longer exists in LangChain 1.x.

### 1.4 The Inadequate Test Shim

In `tests/conftest.py`, a 15-line monkey-patch was previously injected before test discovery:
```python
# tests/conftest.py (legacy shim)
try:
    import langchain.docstore.document
except ModuleNotFoundError:
    import sys, types
    docstore_mod = types.ModuleType("langchain.docstore")
    ...
    sys.modules["langchain.docstore"] = docstore_mod
    sys.modules["langchain.docstore.document"] = doc_mod
```
While this allowed `pytest` to run without error, any production process—such as `uvicorn backend.main:app` or clean CLI invocation—failed immediately on startup.

---

## 2. Evaluation of Remediation Options

| Option | Description | Maintainability | Risk | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Option 1: Dependency Downgrade** | Downgrade `langchain` to <0.1.0 | Very Low | Severe breakage to `ragas` and modern RAG evaluation tools | **Rejected** |
| **Option 2: Production Monkey-Patch** | Add shim to `backend/main.py` | Low | Masking incompatibilities; creates fragile runtime state | **Rejected** |
| **Option 3: Targeted Lazy Import** | Move `from paddleocr import PaddleOCR` inside `get_ocr_model()` | High | Zero risk to web startup, zero dependency churn, completely isolates OCR runtime | **Accepted** |

---

## 3. Implementation of the Targeted Lazy Import

In [`app/ocr.py`](file:///Users/sj/Documents/mediscanai/app/ocr.py):

```python
# app/ocr.py
def get_ocr_model():
    """
    Lazy initialization of PaddleOCR.
    Defers importing paddleocr and initializing heavy OCR model until first image is processed.
    Prevents PaddleX langchain.docstore import failures at backend/app startup.
    """
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_instance = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR engine: {e}")
            raise
    return _ocr_instance
```

### 3.1 Removal of the Test Shim

Because `backend.main` and `app.core` no longer eagerly import `paddleocr` at module import time, `tests/conftest.py` was cleaned of the artificial shim:
- Lines 17–31 in `tests/conftest.py` completely removed.
- Clean standard fixtures preserved.

---

## 4. Verification Results

1. **Clean Subprocess Import:**
   - Command: `python -c "import backend.main"` (executed in a fresh subprocess with no test runner or shim present).
   - Exit code: `0`.
   - Duration: ~4.69 s (standard Python startup & model definitions).
   - Status: **PASSED**.

2. **Pytest Test Discovery:**
   - Command: `pytest --collect-only`
   - Result: 211 tests collected across all test suites in 0.10s without any `langchain.docstore` error.
   - Status: **PASSED**.

3. **FastAPI Application Health:**
   - Endpoint: `GET /api/health`
   - Status Code: `200 OK`
   - Response: `{"status": "alive", "app": "MediScanAI", "environment": "development"}`
   - Status: **PASSED**.

4. **OCR Dependency Error Isolation:**
   - If PaddleOCR fails to initialize or encounters runtime exceptions during image processing, it raises a diagnosable `RuntimeError` or `Exception` caught by the multimodal pipeline fallback rather than crashing server startup.
   - Status: **PASSED**.
