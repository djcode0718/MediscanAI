# MediScanAI Candidate A6.1 — Verification & Post-Triage Audit Report

**Date:** 2026-10-24 14:37:17
**Verified Source Commit:** `2e8abc53dc46c3293c24f3b80f7495310197ce8f`
**Branch:** `exp/ragas-opt`
**Candidate:** `A6.1`
**Baseline Rollback:** `A6`

## 1. Verified Repository State and Configuration

- **Source State:** Working tree verified clean prior to evaluation; targeted fixes confirmed in `app/evidence.py`, `app/prompt_v2.py`, and test suites.
- **Active Prompt Template:** Confirmed `prompt_version='v5'`, unified with positive indication rules and alternatives normalizers.
- **Routing Configuration:** Confirmed `routing_version='v2'`.
- **Rollback Safety:** Baseline A6 artifacts in `evaluation/e2e/results/A6/` and prior A2–A8 records remain completely preserved.

## 2. Deterministic Validation & Regression Test Results

- **Sanitizer & Normalizer Validation (Phase 2):** Passed. Verified symptom-only negative disclaimer stripping, replacement with `Not applicable: no medicine provided.`, physical container attribution normalization, and strict citation preservation (`[E1]`-`[E10]`).
- **Targeted Unit Tests:** Passed (37 / 37 passed in `test_evidence_hygiene.py` and `test_prompt_v2.py`).
- **Full Unit Suite (Phase 3):** Passed (180 / 180 passed, 0 failures, 0 errors, 0 model calls in test execution).

## 3. Controlled Development Evaluation (A6.1 vs A6)

- **Evaluated Benchmark:** 40 frozen development cases (`dev_subset_40.json`).
- **A6 Mean Faithfulness:** 0.8021
- **A6.1 Mean Faithfulness:** 0.7614 (-0.0407)
- **A6 Median Faithfulness:** 1.0000
- **A6.1 Median Faithfulness:** 1.0000 (+0.0000)
- **Paired Comparison:** 4 Wins, 9 Losses, 26 Ties (tolerance: 1e-4).

## 4. Improvements and Regressions by Category

| Category | Count | A6 Mean | A6.1 Mean | Delta | Regression Check |
|---|---:|---:|---:|---:|---|
| `medicine_only_clean_ocr` | 6 | 1.0000 | 1.0000 | +0.0000 | ✅ No regression |
| `medicine_only_noisy_ocr` | 5 | 0.8000 | 0.8000 | +0.0000 | ✅ No regression |
| `symptom_only` | 8 | 0.8500 | 0.8021 | -0.0479 | ⚠️ Regression detected |
| `symptom_plus_medicine_match` | 8 | 0.8793 | 0.8849 | +0.0056 | ✅ No regression |
| `symptom_plus_medicine_mismatch` | 6 | 0.8889 | 0.7361 | -0.1528 | ⚠️ Regression detected |
| `unanswerable` | 7 | 0.4167 | 0.3810 | -0.0357 | ⚠️ Regression detected |

## 5. Decision & Recommendation

### Verdict: REVERT TO A6 (ROLLBACK CANDIDATE)
Candidate A6.1 showed an unexpected net regression on the development benchmark. Rollback to A6 is recommended.

## 6. Output Artifact Inventory

- `evaluation/e2e/results/A6_1/generated_cases.jsonl`
- `evaluation/e2e/results/A6_1/scored_results.jsonl`
- `evaluation/e2e/results/A6_1/unsupported_statements.jsonl`
- `evaluation/e2e/results/A6_1/resource_usage.jsonl`
- `evaluation/e2e/results/A6_1/generation_metadata.json`
- `evaluation/e2e/results/A6_1_EVAL_REPORT.md`
- `evaluation/e2e/results/A6_1_RESOURCE_USAGE_REPORT.md`
- `evaluation/e2e/results/A6_1_VERIFICATION_REPORT.md`
- `evaluation/e2e/results/A6_1_PROGRESS.md`
- `evaluation/e2e/results/A6_1/progress.json`
