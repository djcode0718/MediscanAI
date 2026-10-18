# Phase 1.2.a — Recovery and Preflight Verification Notes

## 1. System Recovery & Preflight Audit

- **Incident:** Laptop shutdown during initial Phase 1.2.a preflight check.
- **State Upon Recovery:**
  - Git branch: `feat/retrieval-evaluation` (Commit `40ba53b24b8afefe8ea45188f2f2eaa921d2d548`).
  - Invariant verification: `evaluation/benchmark/gold_judgments.jsonl` is strictly **0 bytes**.
  - Off-limits directory: `entity_resolution/` untouched and uninspected.
  - No partial benchmark files or corrupted outputs were generated prior to interruption.
  - Available host resources: 36 GB free disk space, ~5.8 GB free/inactive RAM.
  - Active Ollama daemon: running locally at `http://localhost:11434` (Ollama v0.30.5).
  - Target model verified: `llama3.1:8b` (digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`).
  - Retrieval configuration verified: `f3937376cd191ee7` (exact SHA-256 prefix for `evaluation/retrieval/phase_d_2_c/intent_router.py`).
  - Generation prompt template verified: `d9cb6819ed81b1a02cea4fe5f654de1381b17fb3e8028f423e0347af1b44dbe0` (Phase C.4 standard).

---

## 2. Preflight Smoke Test Execution

A single-case smoke test was executed on development split case `MED-BENCH-001` (`"Lipitor"`) to confirm end-to-end functionality of retrieval, context assembly, and local Ollama inference under `CFG-04-D2C-ADAPTIVE-FINAL`.

- **Case ID:** `MED-BENCH-001`
- **Split:** `dev` (non-held-out)
- **Query:** `Lipitor` (drug brand lookup)
- **Retrieved Evidence:**
  - Candidate 1: Key `63899` (Score: 5.2631, Atorvastatin Calcium)
  - Candidate 2: Key `53548` (Score: 4.8304, Atorvastatin Calcium)
  - Number of items passing threshold ($\tau = -0.5$): 2
  - Retrieval Latency: 5,303 ms
- **Generation Parameters:**
  - Model: `llama3.1:8b`
  - Temperature: 0.0
  - Context size / max tokens: `num_predict=512`, `top_p=1.0`
- **Generation Metrics:**
  - Generation Latency: 29,375 ms (29.38s)
  - Prompt Tokens: 1,714
  - Generated Tokens: 224
  - Generation Speed: 7.63 tokens/second
- **Safety Checks:**
  - Mandatory Warning Header (`### ⚠️ Important Warning`): **PASSED**
  - Verbatim Medical Disclaimer: **PASSED**
  - Factual Summary & Clinical Uncertainty Sections: **PASSED**

Output persisted in [smoke_test_recovery.json](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_2_a_generation_baseline/smoke_test_recovery.json).

---

## 3. Current State & Next Steps

- **Completed:** Environment verification, configuration hash audit, resource validation, and single-case preflight smoke test.
- **Incomplete:** The 50-case benchmark generation run has not been launched, pending user authorization and execution plan review.
- **Recommended Next Step:**
  - Execute sequential generation across the 50 benchmark cases in batches or with checkpoints, maintaining progress logs under `evaluation/retrieval/phase_1_2_a_generation_baseline/`.
  - Estimated run time: ~25-30 minutes total for 50 cases at ~30s/case.
