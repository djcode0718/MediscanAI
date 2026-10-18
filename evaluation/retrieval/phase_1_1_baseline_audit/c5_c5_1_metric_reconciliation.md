# MediScanAI Phase 1.1 — Phase C.5 & C.5.1 Metric Reconciliation

**Evaluation Phase:** Phase 1.1 Baseline Audit  
**Date:** October 17, 2026  
**Auditor:** Autonomous Systems Baseline & Evaluation Specialist  
**Artifact Path:** `evaluation/retrieval/phase_1_1_baseline_audit/c5_c5_1_metric_reconciliation.md`  

---

## 1. Executive Summary & Audit Resolution

A rigorous, independent recalculation was conducted to reconcile the conflicting historical evaluation metrics reported in Phase C.5 (`evaluation/ragas/phase_c_5/evaluation_report.md`) versus the narrative report in Phase C.5.1 (`evaluation/ragas/phase_c_5/audit_c5_1/audit_report.md`).

### Definitive Reconciliation Finding
1. **The Original Phase C.5 Metrics are the True, Mathematically Recomputed Values:**
   Independent recalculation directly from the raw, case-level records ([`case_level_scores.csv`](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/case_level_scores.csv) and [`paired_metric_deltas.csv`](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/paired_metric_deltas.csv)) confirms the original Phase C.5 metrics:
   - **Faithfulness:** Baseline **0.5835** (0.583470), Graph **0.5703** (0.570257), Mean Delta **-0.0132**
   - **Answer Relevancy:** Baseline **0.7532** (0.753188), Graph **0.7749** (0.774928), Mean Delta **+0.0217**
   - **Context Precision:** Baseline **0.8932** (0.893241), Graph **0.8689** (0.868916), Mean Delta **-0.0243**
   - **Context Recall:** Baseline **0.6186** (0.618561), Graph Marginal **0.6041** (0.604074), Graph Paired ($N=44$) **0.6064** (0.606439), Mean Paired Delta **-0.0121**
2. **The C.5.1 Narrative Markdown Table Contains an Unreproduced Clerical Error:**
   The numbers reported in the narrative Markdown table of `audit_report.md` Section 3.1 (e.g., Faithfulness: `0.817651`, Answer Relevancy: `0.771962`, Context Precision: `0.852335`) **do not exist in any raw data artifact**.
   Critically, the machine-readable audit script ([`generate_audit_data.py`](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/generate_audit_data.py)) generated [`recomputed_metrics.json`](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/recomputed_metrics.json), which records `baseline_mean_all: 0.58347` and `graph_mean_all: 0.570257`. The anomalous values in `audit_report.md` are classified as:

$$\mathbf{UNREPRODUCED\_CLERICAL\_ERROR}$$

---

## 2. Master Reconciliation Table

| Metric | Dimension / Cohort | Phase C.5 Reported | Phase C.5.1 Markdown Text | C.5.1 Recomputed JSON (`recomputed_metrics.json`) | Phase 1.1 Independent Audit | Status & Reconciliation Classification |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Faithfulness** | Baseline Mean ($N=50$) | **0.5835** | 0.817651 | **0.583470** | **0.583470** | Verified: C.5 is ground truth; C.5.1 text is clerical defect |
| | Graph Mean ($N=50$) | **0.5703** | 0.806052 | **0.570257** | **0.570257** | Verified: C.5 is ground truth |
| | Mean Paired Delta | **-0.0132** | -0.011599 | **-0.013213** | **-0.013213** | Verified exact match to C.5 |
| | Bootstrap 95% CI | `[-0.0759, 0.0527]` | `[-0.0759, 0.0527]` | `[-0.0759, 0.0527]` | `[-0.0759, 0.0527]` | Exact match; spans zero |
| **Answer Relevancy**| Baseline Mean ($N=50$) | **0.7532** | 0.771962 | **0.753188** | **0.753188** | Verified: C.5 is ground truth |
| | Graph Mean ($N=50$) | **0.7749** | 0.800571 | **0.774928** | **0.774928** | Verified: C.5 is ground truth |
| | Mean Paired Delta | **+0.0217** | +0.028609 | **+0.021740** | **+0.021740** | Verified exact match to C.5 |
| | Bootstrap 95% CI | `[-0.0180, 0.0752]` | `[-0.0180, 0.0752]` | `[-0.0180, 0.0752]` | `[-0.0180, 0.0752]` | Exact match; spans zero |
| **Context Precision**| Baseline Mean ($N=45$) | **0.8932** | 0.852335 | **0.893241** | **0.893241** | Verified: C.5 is ground truth |
| | Graph Mean ($N=45$) | **0.8689** | 0.828038 | **0.868916** | **0.868916** | Verified: C.5 is ground truth |
| | Mean Paired Delta | **-0.0243** | -0.024297 | **-0.024325** | **-0.024325** | Verified exact match to C.5 |
| | Bootstrap 95% CI | `[-0.0533, 0.0018]` | `[-0.0533, 0.0018]` | `[-0.0533, 0.0018]` | `[-0.0533, 0.0018]` | Exact match; spans zero |
| **Context Recall** | Baseline Mean ($N=44$) | **0.6186** | 0.618561 | **0.618561** | **0.618561** | Verified exact match (1 timeout) |
| | Graph Mean (Marginal $N=45$) | **0.6041** | 0.604074 | **0.604074** | **0.604074** | Marginal mean across all 45 cases |
| | Graph Mean (Paired $N=44$) | *0.6064*\* | 0.606439 | **0.606439** | **0.606439** | Strictly paired mean on 44 cases |
| | Mean Paired Delta | **-0.0121** | -0.012121 | **-0.012121** | **-0.012121** | Verified: $-0.012121 = 0.606439 - 0.618561$ |

*\*Note: 0.6064 was reported in C.5 table notes for paired comparisons.*

---

## 3. Root-Cause Analysis of the Discrepancy

### Finding 1: The C.5.1 Markdown Text Defect
- In Phase C.5.1, the auditor generated [`recomputed_metrics.json`](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/recomputed_metrics.json) using Python (`generate_audit_data.py`). That JSON file accurately recomputed:
  ```json
  "faithfulness": {
    "baseline_mean_all": 0.58347,
    "graph_mean_all": 0.570257
  }
  ```
- However, when composing [`audit_report.md`](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/audit_report.md) Section 3.1, a table with phantom values (`0.817651`, `0.806052`, etc.) was erroneously pasted into the document.
- Crucially, the confidence intervals in that very same table:
  `Faithfulness CI: [-0.075905, 0.052703]`
  match the mean delta of **`-0.013213`**, NOT the erroneous delta in the table.
- **Conclusion:** The values in the Markdown text of `audit_report.md` Section 3.1 are an ungrounded clerical error. The machine-readable data and C.5 reports are correct.

### Finding 2: Context Recall Denominator and Timeout Handling (DISC-001 & DISC-002)
- Query `MED-BENCH-029` (*"How does diabetic kidney disease develop and what are its clinical stages?"*) experienced a worker timeout (`Job[3] TimeoutError after 180s`) during Baseline Context Recall evaluation.
- Consequently:
  - Baseline Context Recall contains **44 valid scores**.
  - Graph-Assisted Context Recall contains **45 valid scores** (succeeded with score `0.500000`).
- This created two distinct graph averages:
  1. **Marginal Graph Mean ($N=45$):** Sum of all 45 graph scores divided by 45 = **`0.604074`**.
  2. **Strictly Paired Graph Mean ($N=44$):** Sum of the 44 graph scores matching the 44 valid baseline cases = **`0.606439`**.
- Subtracting the baseline mean (`0.618561`) from the strictly paired graph mean (`0.606439`) yields:
  $$0.606439 - 0.618561 = \mathbf{-0.012121}$$
  This matches `mean_paired_delta` exactly.
- Both figures are valid when properly labeled:
  - **Marginal Context Recall:** Baseline = 0.6186 ($N=44$), Graph = 0.6041 ($N=45$), Marginal Delta = $-0.0145$.
  - **Paired Context Recall:** Baseline = 0.6186 ($N=44$), Graph = 0.6064 ($N=44$), Paired Delta = $\mathbf{-0.0121}$.

---

## 4. Evaluated Cases & Split Integrity Verification

1. **Cases Evaluated:** 50 canonical benchmark cases (`MED-BENCH-001` through `MED-BENCH-050`).
2. **Answerable Cases:** 45 cases (`MED-BENCH-001` through `040`, `046` through `050`).
3. **Negative Controls:** 5 cases (`MED-BENCH-041` through `045`).
   - Excluded by metric contract from Context Precision and Context Recall (ground truth is unanswerable / absent).
   - Evaluated for Faithfulness (checking absence of hallucinations) and Answer Relevancy.
4. **Graph-Assisted Symmetry:** Both baseline and graph-assisted runs evaluated the exact same 50 cases using identical prompt structures and generation bounds.

---

## 5. Statistical Synthesis

Across all 50 cases:
- **Faithfulness:** Mean delta = $-0.0132$ ($95\%\text{ CI } [-0.0759, +0.0527]$, spans zero).
- **Answer Relevancy:** Mean delta = $+0.0217$ ($95\%\text{ CI } [-0.0180, +0.0752]$, spans zero).
- **Context Precision:** Mean delta = $-0.0243$ ($95\%\text{ CI } [-0.0533, +0.0018]$, spans zero).
- **Context Recall:** Mean delta = $-0.0121$ ($95\%\text{ CI } [-0.0803, +0.0591]$, spans zero).

**Definitive Conclusion:**  
No statistically significant difference exists between the baseline hybrid pipeline and the global graph-assisted pipeline in Phase C.5. The true baseline metrics for Phase C.5 are established and verified.
