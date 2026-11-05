# Reference Baseline B0 Audit & Re-Scoring Report (MediScanAI Phase 3B)

**Date:** 2026-10-24 18:09:36 UTC
**Authoritative Judge Model:** `llama3.1:8b` (Single Authorized Judge)
**Baseline Status:** `PROVISIONAL`
**Evaluator Framework:** Repaired RAGAS (`llama3.1:8b`, Cache V2, Strict Output Parsing, Contamination Guard v2.0.0)

## 1. Executive Summary & Baseline Quality Gate

- **Authoritative Judge Model:** **`llama3.1:8b`** (Enforced by code and unit tests; unauthorized models strictly rejected)
- **Baseline B0 Status:** **`PROVISIONAL`** (Automatic criteria pass; pending human adjudication)
- **Baseline A6 Invalid Rate:** **0.0%** (0/40 invalid; strictly $\le 3.0\%$ threshold — PASS)
- **A6 Test-Retest Stability:** Case-level MAD = `0.0000`, Statement agreement = `100.0%` (0 disagreeing cases)
- **A6.1 Test-Retest Stability:** Case-level MAD = `0.0000`, Statement agreement = `100.0%`
- **All-Cases Mean Faithfulness (B0 Reference):** **0.8021** (Median: **1.0000**)
- **Answerable-Only Mean Faithfulness (33 cases):** **0.8839**
- **RAGAS on Abstentions (7 unanswerable cases):** **0.4167**

## 2. Table 1: Evaluator Effect (Old Reported vs Repaired Rescored on Same Answers)

Cases where per-case faithfulness changed by > 0.10 or status changed under the repaired evaluator:

| Candidate | Case ID | Category | Old Score | Rescored (Repaired) | Delta | Status / Diagnostic Notes |
|---|---|---|---:|---:|---:|---|
| A6.1 | `E2E-062` | `symptom_plus_medicine_match` | nan | Invalid (invalid_parse_failure) | Status change | invalid_parse_failure (-) |
| A6.1 | `E2E-080` | `symptom_plus_medicine_mismatch` | 0.0000 | Invalid (invalid_contaminated) | Status change | invalid_contaminated (-) |

## 3. Table 2: Candidate Effect (A6.1 vs A6 Under Repaired Evaluator)

- **Paired Intersection:** 38 cases
- **Paired Mean Delta (A6.1 - A6):** **-0.0234**
- **Bootstrap 95% CI (10k resamples, seed 42):** **[-0.0763, +0.0315]**
- **Wins / Losses / Ties:** **4W / 8L / 26T**
- **Statistical Verdict:** **INCONCLUSIVE**
- **Candidate Promotion Gate:** **REJECTED_FOR_PROMOTION (Candidate invalid rate 5.0% exceeds 3.0% threshold)**

> [!NOTE]
> Candidate A6.1 exhibits an invalid rate of 5.0% (2/40 cases: E2E-062 parse failure, E2E-080 contaminated), which exceeds the 3.0% threshold. Therefore, candidate A6.1 cannot be recommended for promotion regardless of mean score.

### Category Breakdown (Repaired Evaluator)

| Category | Valid N (Base/Cand) | Baseline A6 Mean | Candidate A6.1 Mean | Delta |
|---|---:|---:|---:|---:|
| `medicine_only_clean_ocr` | 6 / 6 | 1.0000 | 1.0000 | +0.0000 |
| `medicine_only_noisy_ocr` | 5 / 5 | 0.8000 | 0.8000 | +0.0000 |
| `symptom_only` | 8 / 8 | 0.8500 | 0.8021 | -0.0479 |
| `symptom_plus_medicine_match` | 8 / 7 | 0.8793 | 0.8849 | +0.0057 |
| `symptom_plus_medicine_mismatch` | 6 / 5 | 0.8889 | 0.8833 | -0.0055 |
| `unanswerable` | 7 / 7 | 0.4167 | 0.3810 | -0.0357 |

## 4. Authoritative Judge Model Enforcement & Results Inventory

### Authoritative Judge Model
- **Authorized Model:** `llama3.1:8b`
- **Enforcement Mechanism:** `evaluation/e2e/judge_factory.py` strictly raises `UnauthorizedJudgeError` if any unauthorized model is passed. Verified via unit test suite `tests/evaluation/test_authorized_judge.py`.

### Included Authoritative Passes (B0 Baseline & Comparison)
- `B0_A6_p1/` (A6 Pass 1, `llama3.1:8b`, Cache Bypassed, 40/40 valid)
- `B0_A6_p2/` (A6 Pass 2, `llama3.1:8b`, Cache Bypassed, 40/40 valid, 100% test-retest agreement)
- `B0_A61_p1/` (A6.1 Pass 1, `llama3.1:8b`, Cache Bypassed, 38/40 valid)
- `B0_A61_p2/` (A6.1 Pass 2, `llama3.1:8b`, Cache Bypassed, 38/40 valid, 100% test-retest agreement)

### Excluded Diagnostic Passes
- `B0_A6_second_judge/` (`qwen2.5:3b`): **EXCLUDED** from authoritative statistics, baseline calculation, and adjudication sheets. Preserved strictly as a historical diagnostic artifact.

## 5. Adjudication Pack & Instructions for Human Reviewer

An audited adjudication pack has been generated under `evaluation/e2e/results/B0/`:
1. **Blinded Sheet (For Human Labeling):** [`evaluation/e2e/results/B0/adjudication_sheet_blind.csv`](file:///Users/sj/Documents/mediscanai/evaluation/e2e/results/B0/adjudication_sheet_blind.csv)
   - AI judge verdicts and reasons are omitted to eliminate cognitive anchoring.
   - Context blocks have clean formatting without duplicated tokens.
2. **Full Reference Sheet (With AI Verdicts):** [`evaluation/e2e/results/B0/adjudication_sheet.csv`](file:///Users/sj/Documents/mediscanai/evaluation/e2e/results/B0/adjudication_sheet.csv)
3. **Human Labeling Rubric:** [`evaluation/e2e/tools/ADJUDICATION_RUBRIC.md`](file:///Users/sj/Documents/mediscanai/evaluation/e2e/tools/ADJUDICATION_RUBRIC.md)

> [!IMPORTANT]
> **Action required by human reviewer to establish baseline:**
> 1. Open [`adjudication_sheet_blind.csv`](file:///Users/sj/Documents/mediscanai/evaluation/e2e/results/B0/adjudication_sheet_blind.csv).
> 2. Fill in the `human_label` column (`supported`, `unsupported`, or `unclear`) according to [`ADJUDICATION_RUBRIC.md`](file:///Users/sj/Documents/mediscanai/evaluation/e2e/tools/ADJUDICATION_RUBRIC.md).
> 3. Execute `PYTHONPATH=. python evaluation/e2e/tools/adjudication_stats.py` to evaluate agreement.
>
> Baseline B0 will be elevated from **PROVISIONAL** to **ESTABLISHED** once agreement $\ge 85\%$ and negative precision $\ge 80\%$ are verified.
