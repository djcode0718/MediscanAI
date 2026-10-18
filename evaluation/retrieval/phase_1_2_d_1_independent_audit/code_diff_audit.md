# Phase 1.2.d.1 — Code Diff and Dependency Audit

**Document Title:** Independent Code Diff and Dependency Verification  
**Phase:** Phase 1.2.d.1 — Independent Production Integration Audit  
**Target Phase Audited:** Phase 1.2.d — Controlled Emergency Guardrail Integration  
**Date:** 2026-10-17  
**Auditor:** Antigravity AI Independent Safety Systems Auditor  

---

## 1. Executive Summary

This document presents the detailed line-by-line verification of all code modifications introduced in **Phase 1.2.d** (`feat/retrieval-evaluation` branch, relative to base commit `40ba53b24b8afefe8ea45188f2f2eaa921d2d548`).

The audit verified:
1. Exact compliance between reported modifications and actual Git changes.
2. Absence of unrelated or accidental edits.
3. Analysis of the test compatibility shim in `tests/conftest.py`.
4. Detection of architectural nuances and production dependency constraints.

---

## 2. Modified Files Inventory

| File Path | Git Status | Nature of Change | Report Alignment |
| :--- | :--- | :--- | :--- |
| **`backend/core/config.py`** | Tracked / Modified | Added feature flag settings (`EMERGENCY_GUARDRAIL_*`) | **MATCHES 100%** |
| **`backend/main.py`** | Tracked / Modified | Added startup status logging and audit event recording | **MATCHES 100%** |
| **`app/guardrail_config.json`** | Untracked / Added | Added production JSON configuration with regex rules and hotlines | **MATCHES 100%** |
| **`app/guardrail.py`** | Untracked / Added | Added deterministic emergency guardrail engine and fallback logic | **MATCHES 100%** |
| **`app/core.py`** | Tracked / Modified | Integrated pre-gen fast-path and post-gen safeguard into `Pipeline` | **MATCHES 100%** |
| **`tests/conftest.py`** | Tracked / Modified | Added compatibility shim for LangChain/PaddleX docstore | **MATCHES 100%** |
| **`tests/integration/test_emergency_guardrail_integration.py`** | Untracked / Added | Added 23-test integration test suite | **MATCHES 100%** |

Confirmed: Zero unrelated files were modified. The Git diff contains only the specified 7 files.

---

## 3. Detailed Inspection per Component

### 3.1 `backend/core/config.py`
```diff
+    # Emergency Triage Guardrail Configuration (Phase 1.2.d)
+    EMERGENCY_GUARDRAIL_ENABLED: bool = False
+    EMERGENCY_GUARDRAIL_CONFIG_PATH: str = "app/guardrail_config.json"
+    EMERGENCY_GUARDRAIL_FAST_PATH: bool = True
```
- **Review:**
  - `EMERGENCY_GUARDRAIL_ENABLED` defaults strictly to `False`.
  - Config path points to the standard repo path `"app/guardrail_config.json"`.
  - `EMERGENCY_GUARDRAIL_FAST_PATH` defaults to `True`.
  - No existing settings or validators were modified.
- **Verdict:** **PASS**.

---

### 3.2 `backend/main.py`
```diff
+    # 4. Check Emergency Guardrail status
+    if settings.EMERGENCY_GUARDRAIL_ENABLED:
+        print(f"[STARTUP] Emergency Triage Guardrail: ENABLED (Fast-path: {settings.EMERGENCY_GUARDRAIL_FAST_PATH}) 🚨")
+    else:
+        print("[STARTUP] Emergency Triage Guardrail: DISABLED (baseline mode) 🛡️")
```
and:
```diff
+        # 9b. Record Emergency Guardrail Event if triggered (Data-Minimized)
+        guardrail_meta = result.get("meta", {}).get("guardrail")
+        if guardrail_meta and guardrail_meta.get("is_emergency"):
+            record_audit_event(
+                event_type="EMERGENCY_GUARDRAIL_TRIGGERED",
+                user_id=current_user.id,
+                ip_address=request.client.host if request.client else None,
+                user_agent=request.headers.get("user-agent"),
+                metadata={
+                    "analysis_id": analysis.id,
+                    "rule_id": guardrail_meta.get("fired_rule_id"),
+                    "category": guardrail_meta.get("category"),
+                    "severity": guardrail_meta.get("severity"),
+                    "fast_path": result.get("meta", {}).get("fast_path", False),
+                    "duration_ms": duration_ms
+                },
+                db=db
+            )
```
- **Review:**
  - Startup message provides clear operator visibility into the feature flag state without altering initialization flow.
  - Audit telemetry event `EMERGENCY_GUARDRAIL_TRIGGERED` strictly complies with data minimization:
    - Logged metadata: `analysis_id`, `rule_id`, `category`, `severity`, `fast_path`, `duration_ms`.
    - Excluded: `user_text`, `audio`, `ocr_text`, `llm_output`, medical diagnosis.
  - No PHI or sensitive medical text is written to the audit log.
- **Verdict:** **PASS**.

---

### 3.3 `app/guardrail_config.json`
- Contains 5 validated rule definitions:
  - `RULE-01-CARDIOVASCULAR-CHEST-PAIN` (10 triggers)
  - `RULE-02-RESPIRATORY-DISTRESS` (11 triggers)
  - `RULE-03-NEUROLOGICAL-STROKE` (7 triggers)
  - `RULE-04-UNCONSCIOUSNESS-COLLAPSE` (4 triggers)
  - `RULE-05-SEVERE-HEMORRHAGE` (5 triggers)
- Contains 6 negation patterns (`no chest pain`, `without shortness of breath`, etc.).
- Contains 6 historical/family patterns (`years ago`, `father had heart attack`, etc.).
- Contains 4 contextual exception patterns (`chest decongestant`, `stroke volume`, etc.).
- National emergency hotlines specified: India `112`, US `911`, UK `999`, EU `112`.
- **Verdict:** **PASS**. Exact match to Phase 1.2.b audited configuration.

---

### 3.4 `app/guardrail.py`
- Implements `EmergencyGuardrail` with clean separation of concerns:
  - `detect_emergency(query, retrieved_contexts)`: deterministic regex evaluation, negation gating, historical gating, contextual exception filtering, and evidence intercept.
  - `apply_guardrail(query, baseline_response, retrieved_contexts)`: template construction, verbatim legal disclaimer injection (`### ⚠️ Important Warning`), and contradictory appointment advice elimination (`_eliminate_contradictory_routine_advice`).
  - `_failsafe_detect()`: hard-coded fallback using `FAILSAFE_KEYWORD_PATTERNS` ensuring non-zero safety even when config JSON fails to load.
- Negative control abstention preservation: if baseline response contains `"cannot provide medical advice"`, guardrail preserves baseline without altering text.
- **Verdict:** **PASS**.

---

### 3.5 `app/core.py`
```diff
+        # Emergency Triage Guardrail (Phase 1.2.d)
+        self.guardrail = None
+        if self.settings.EMERGENCY_GUARDRAIL_ENABLED:
+            try:
+                from app.guardrail import EmergencyGuardrail
+                from pathlib import Path
+                cfg_path = Path(self.settings.EMERGENCY_GUARDRAIL_CONFIG_PATH)
+                if not cfg_path.is_absolute():
+                    from backend.core.config import _BASE_DIR
+                    cfg_path = _BASE_DIR / cfg_path
+                self.guardrail = EmergencyGuardrail(config_path=cfg_path)
+            except Exception as e:
+                logger.error(f"Failed to initialize EmergencyGuardrail: {e}. Engaging fail-safe fallback.", exc_info=True)
+                from app.guardrail import EmergencyGuardrail
+                self.guardrail = EmergencyGuardrail(config_path=None)
```
and:
```diff
+        # 1b. Emergency Pre-Generation Fast-Path Check (Phase 1.2.d)
+        if self.guardrail is not None and self.settings.EMERGENCY_GUARDRAIL_FAST_PATH:
+            _t_guard_pre = time.perf_counter()
+            combined_query = user_text or ""
+            pre_decision = self.guardrail.detect_emergency(combined_query)
+            if pre_decision.is_emergency and pre_decision.severity == "CRITICAL_EMERGENCY":
+                guarded_response_str, final_decision = self.guardrail.apply_guardrail(
+                    query=combined_query,
+                    baseline_response=""
+                )
...
```
and:
```diff
+        # 4b. Emergency Post-Generation Safeguard Enforcement (Phase 1.2.d)
+        guardrail_meta_dict = None
+        if self.guardrail is not None:
+            _t_guard_post = time.perf_counter()
+            evidence_summaries: List[str] = []
+            for idx_name, items in all_retrievals.items():
+                for key, score, obj in items:
+                    if isinstance(obj, dict):
+                        evidence_summaries.append(str(obj))
+            guarded_response_str, post_decision = self.guardrail.apply_guardrail(
+                query=user_text or "",
+                baseline_response=llm_response_str.strip(),
+                retrieved_contexts=evidence_summaries
+            )
```
- **Architectural Findings & Observations:**
  1. **OCR Text Exclusion from Pre-Generation Fast-Path:**
     Line 273 sets `combined_query = user_text or ""`. In multimodal requests where a user submits only an image without accompanying text (e.g., photo of a medical report showing acute chest pain), `ocr_text` (extracted on line 267) is **not** passed into `combined_query`. Consequently, `detect_emergency("")` evaluates to `False`, bypassing the pre-generation fast-path.
  2. **OCR Precedence over Fast-Path:**
     OCR execution (`extract_text_from_image`) occurs on line 266, *before* the pre-generation guardrail check on line 271. If an unhandled exception occurs in the OCR engine, `Pipeline.run()` crashes before the emergency check can execute.
  3. **Baseline Fidelity:**
     When `EMERGENCY_GUARDRAIL_ENABLED=False`, `self.guardrail is None`. Neither fast-path nor post-gen safeguard executes. `card_meta` and output are 100% identical to baseline.
- **Verdict:** **PASS WITH ARCHITECTURAL NOTES**.

---

### 3.6 `tests/conftest.py` — Critical Dependency Audit

```python
# Compatibility shim for paddlex / langchain 1.4+ in test environment
import types
if "langchain.docstore" not in sys.modules:
    _lc = sys.modules.get("langchain") or types.ModuleType("langchain")
    _ds = types.ModuleType("langchain.docstore")
    _ds_doc = types.ModuleType("langchain.docstore.document")
    _ds_doc.Document = type("Document", (), {})
    _ds.document = _ds_doc
    _lc.docstore = _ds
    _ts = types.ModuleType("langchain.text_splitter")
    _ts.RecursiveCharacterTextSplitter = type("RecursiveCharacterTextSplitter", (), {})
    _lc.text_splitter = _ts
    sys.modules["langchain"] = _lc
    sys.modules["langchain.docstore"] = _ds
    sys.modules["langchain.docstore.document"] = _ds_doc
    sys.modules["langchain.text_splitter"] = _ts
```

#### Verification Question: Does this test compatibility shim conceal a production dependency problem or alter test semantics?

**AUDIT FINDING: YES, IT CONCEALS A PRODUCTION DEPENDENCY PROBLEM.**

**Empirical Evidence:**
1. Running an isolated Python process to import `backend.main` without `tests/conftest.py`:
   ```bash
   /Users/sj/miniforge3/envs/med-env/bin/python -c "import backend.main"
   ```
2. **Observed Result:**
   ```
   Traceback (most recent call last):
     File "<string>", line 1, in <module>
     File "/Users/sj/Documents/mediscanai/backend/main.py", line 30, in <module>
       from app.core import Pipeline
     File "/Users/sj/Documents/mediscanai/app/core.py", line 178, in <module>
       from app.ocr import extract_text_from_image, ocr_text_join
     File "/Users/sj/Documents/mediscanai/app/ocr.py", line 8, in <module>
       from paddleocr import PaddleOCR
     File ".../paddlex/inference/pipelines/components/retriever/base.py", line 25, in <module>
       from langchain.docstore.document import Document
   ModuleNotFoundError: No module named 'langchain.docstore'
   ```
3. **Root Cause Analysis:**
   - In modern LangChain releases (>= 0.2 / 0.3 / 1.4), `langchain.docstore` was reorganized to `langchain_core` and `langchain_community`.
   - `paddlex` (a dependency of `paddleocr`) executes an eager top-level import: `from langchain.docstore.document import Document`.
   - In the test suite, `tests/conftest.py` stubs `langchain.docstore` in `sys.modules`, allowing `pytest` to pass smoothly.
   - However, in production (`uvicorn backend.main:app`), `tests/conftest.py` is **never loaded**.
   - As a result, direct production startup in this environment will fail at boot time unless:
     a) `langchain-community` with docstore compatibility is installed, or
     b) `app/ocr.py` performs lazy importing of `paddleocr` inside `extract_text_from_image`, or
     c) The compatibility shim is moved to production initialization (`backend/main.py`).

**Impact on Test Semantics:**
- The shim does not alter emergency guardrail logic or test semantics.
- However, it masks a fatal runtime import failure in `backend/main.py` under the current virtual environment.

---

### 3.7 `tests/integration/test_emergency_guardrail_integration.py`
- Contains 23 tests across 8 test groups:
  1. Feature flag disabled mode and baseline fidelity (2 tests).
  2. Pre-generation fast path for Tier-1 emergencies (6 tests).
  3. Non-emergency, negation, and history gating (7 tests).
  4. Input modalities: voice and packaging OCR (2 tests).
  5. Post-generation enforcement and contradiction elimination (2 tests).
  6. Fault tolerance on corrupt config (1 test).
  7. Telemetry data minimization (1 test).
  8. Rollback restoration (1 test).
- **Execution Result:** 23/23 passed in 0.12s.
- **Verdict:** **PASS**.
