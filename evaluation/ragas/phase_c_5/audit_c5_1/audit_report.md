# MediScanAI Phase C.5.1 — Independent Results, Statistics & Safety Audit Report

**Audit Phase:** Phase C.5.1  
**Audit Date:** 2026-10-16  
**Auditor:** Antigravity Autonomous Diagnostic Agent (Google DeepMind)  
**Evaluated Experiment:** Phase C.5 Paired Ragas Evaluation (`evaluation/ragas/phase_c_5/`)  
**Final Audit Verdict:** **PASS WITH WARNINGS**

---

## 1. Executive Summary & Audit Verdict

This audit performed an independent, read-only statistical, provenance, and safety verification of the completed Phase C.5 evaluation comparing MediScanAI's Baseline hybrid retrieval (dense FAISS + BM25 + RRF + cross-encoder) against Graph-Assisted retrieval (hybrid + Neo4j knowledge graph evidence).

### 1.1 Final Verdict: PASS WITH WARNINGS

The audit establishes a final verdict of **PASS WITH WARNINGS** based on the following determinations:

1. **Integrity & Provenance (PASS):** All 50 benchmark cases and 100 frozen generation responses from Phase C.4 were preserved intact without tampering. Input SHA-256 hashes strictly match the manifest. Zero production files were modified, and `evaluation/benchmark/gold_judgments.jsonl` remains strictly 0 bytes.
2. **Reproducibility of Metrics & Statistics (PASS):** All paired deltas, win/tie/loss counts, and 1,000-resample paired bootstrap 95% confidence intervals reproduced to the exact decimal point from the saved case-level scores.
3. **Category-Specific Claims (PASS):** All 10 audited case- and sub-cohort-level claims in the report (including Cinzan CR +0.50, Metformin CR +0.67, Ciprofloxacin AR +0.91, Atorvastatin F +0.71, and Multi-hop F -0.2071) match case-level records exactly.
4. **Safety & Negative Controls (PASS):** Re-inspection of all 5 negative control cases (MED-BENCH-041 through 045) verified 0/10 distractor adoption, with both pipelines communicating appropriate diagnostic uncertainty.
5. **Warnings (4 Documented Discrepancies):**
   - **DISC-001 (Denominator / Marginal Mean):** Context Recall reported graph aggregate mean (`0.604074`, $N=45$) reflects marginal mean of valid graph scores, whereas baseline mean (`0.618561`, $N=44$) excluded timed-out case `MED-BENCH-029`. The paired difference of these marginal means (`-0.014487`) differs from the reported paired delta mean (`-0.012121`). On the strictly paired subset ($N=44$), graph mean is `0.606439`, yielding exact agreement.
   - **DISC-002 (Unlogged Timeout):** `metric_failures.jsonl` is 0 bytes because Ragas caught the worker thread timeout internally and returned `NaN`, which `run_evaluation.py` stored as an empty string without triggering the outer evaluation exception handler.
   - **DISC-003 (Clerical Tally Error):** Negative control summary reported 4 pure / 6 soft abstentions; verification of case texts and breakdown tables confirms 5 pure / 5 soft abstentions.
   - **DISC-004 (Context Precision Metric Definition):** The report conflated per-sample Average Precision (AP) with Mean Average Precision (MAP).
6. **Clinical Safety Warning (MED-BENCH-038):** The graph-assisted response weakened an explicit emergency triage directive ("seek immediate medical attention") to a routine outpatient referral ("consult a doctor or pharmacist"). While clinically unvalidated, this represents an urgent potential safety regression flagged for clinical review.

---

## 2. Audit A — Artifact and Provenance Integrity

| Verification Check | Target / Expected | Observed / Verified | Status |
| :--- | :--- | :--- | :--- |
| Canonical Cases | Exactly 50 unique cases (`MED-BENCH-001` .. `050`) | 50 unique cases present | PASS |
| Generation Records | Exactly 100 frozen records (50 baseline, 50 graph) | 100 records in `generation_records.jsonl` | PASS |
| Model Configuration | Generator: `llama3.1:8b`, Judge: `llama3.1:8b`, Embedder: `nomic-embed-text` | Exactly verified in `run_manifest.json` | PASS |
| Benchmark Query Hash | Matches frozen input | SHA-256 verified | PASS |
| Narrative Ref Hash | Matches frozen input | SHA-256 verified | PASS |
| C.4 Baseline Hash | `c6cb2a78e72ba714ee55ee03d65ce276329437298642ca85e3eeb0c96c56fb8e` | Identical SHA-256 | PASS |
| C.4 Graph Hash | `1eef26f846067b55fcae3ce0f90e8fe376174a7b7ec25ba14459b73d843ff475` | Identical SHA-256 | PASS |
| Gold Judgments File | `evaluation/benchmark/gold_judgments.jsonl` == 0 bytes | 0 bytes confirmed | PASS |
| Production Invariants | No modifications to `backend/`, `app/`, `retrieval/` | Zero tracked production code modified | PASS |
| Entity Resolution Boundary | Absolute zero access to `entity_resolution/` | Confirmed untouched | PASS |

---

## 3. Audit B — Independent Recomputation of Aggregate Metrics

All metrics were recomputed from `case_level_scores.csv` and `paired_metric_deltas.csv`. Missing, empty, or unparseable scores were treated strictly as `null` and excluded from denominators (never treated as zero).

### 3.1 Primary Aggregate Metrics Comparison

| Metric | Track / Statistic | Reported in C.5 | Recomputed in C.5.1 | Delta / Discrepancy | Denominator Used |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Faithfulness** | Baseline Mean | 0.817651 | 0.817651 | 0.000000 | 50 / 50 |
| | Graph Mean | 0.806052 | 0.806052 | 0.000000 | 50 / 50 |
| | Mean Paired Delta | -0.011599 | -0.011599 | 0.000000 | 50 pairs |
| | Median Paired Delta | 0.000000 | 0.000000 | 0.000000 | 50 pairs |
| | Improved / Unchanged / Regressed | 14 / 21 / 15 | 14 / 21 / 15 | 0 | 50 pairs |
| **Answer Relevancy**| Baseline Mean | 0.771962 | 0.771962 | 0.000000 | 50 / 50 |
| | Graph Mean | 0.800571 | 0.800571 | 0.000000 | 50 / 50 |
| | Mean Paired Delta | +0.028609 | +0.028609 | 0.000000 | 50 pairs |
| | Median Paired Delta | 0.000000 | 0.000000 | 0.000000 | 50 pairs |
| | Improved / Unchanged / Regressed | 17 / 18 / 15 | 17 / 18 / 15 | 0 | 50 pairs |
| **Context Precision**| Baseline Mean | 0.852335 | 0.852335 | 0.000000 | 45 / 45 (answerable) |
| | Graph Mean | 0.828038 | 0.828038 | 0.000000 | 45 / 45 (answerable) |
| | Mean Paired Delta | -0.024297 | -0.024297 | 0.000000 | 45 pairs |
| | Median Paired Delta | 0.000000 | 0.000000 | 0.000000 | 45 pairs |
| | Improved / Unchanged / Regressed | 3 / 34 / 8 | 3 / 34 / 8 | 0 | 45 pairs |
| **Context Recall** | Baseline Mean | 0.618561 | 0.618561 | 0.000000 | 44 / 45 (1 timeout) |
| | Graph Mean (Marginal) | 0.604074 | 0.604074 | 0.000000 | 45 / 45 valid graph |
| | Graph Mean (Paired N=44) | *Not reported* | 0.606439 | +0.002366 | 44 paired complete |
| | Mean Paired Delta | -0.012121 | -0.012121 | 0.000000 | 44 paired complete |
| | Median Paired Delta | 0.000000 | 0.000000 | 0.000000 | 44 pairs |
| | Improved / Unchanged / Regressed | 8 / 27 / 9 | 8 / 27 / 9 | 0 | 44 pairs |

### 3.2 Formal Catalog of Discrepancies

Detailed in [metric_discrepancies.csv](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/metric_discrepancies.csv):

1. **DISC-001 (Context Recall Denominator Inconsistency):** Baseline Context Recall had 44 valid scores (`MED-BENCH-029` timed out), while Graph Context Recall had 45 valid scores. `aggregate_metrics.json` recorded the marginal mean of all 45 graph scores (`0.604074`). Subtracting marginal baseline mean (`0.618561`) from marginal graph mean (`0.604074`) yields `-0.014487`, whereas the strictly paired mean delta is `-0.012121`. On the 44 strictly paired cases, graph mean is `0.606439` ($0.606439 - 0.618561 = -0.012121$).
2. **DISC-002 (Silent Failure in `metric_failures.jsonl`):** `metric_failures.jsonl` has 0 bytes. Ragas handled the internal `TimeoutError` inside worker thread `Job[3]`, returning `NaN` in its output table. The outer script recorded `None` in `case_level_scores.csv` but bypassed the failure log.
3. **DISC-003 (Negative Control Tally Error):** Executive summaries stated 4 pure / 6 soft abstentions. The verified count is 5 pure / 5 soft abstentions.
4. **DISC-004 (Context Precision Conceptual Framing):** Ragas calculates per-sample Average Precision (AP), normalized by retrieved relevant chunks. The report described it as Mean Average Precision (MAP), which is the cohort-wide aggregate.

---

## 4. Audit C — Bootstrap Confidence Intervals Verification

Bootstrap verification was conducted using paired case-level resampling ($B = 1,000$, seed 42, $\alpha = 0.05$). Baseline and graph scores were strictly kept paired on the identical canonical case.

### 4.1 Paired Bootstrap 95% Confidence Intervals

| Metric | Paired N | Reported 95% CI | Recomputed 95% CI ($B=1,000$) | Stability Check ($B=10,000$) | Exact Match | Spans Zero? | Statistically Significant? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Faithfulness** | 50 | `[-0.075905, 0.052703]` | `[-0.075905, 0.052703]` | `[-0.078265, 0.053483]` | **YES** | YES | **NO** |
| **Answer Relevancy**| 50 | `[-0.018013, 0.075231]` | `[-0.018013, 0.075231]` | `[-0.019567, 0.073901]` | **YES** | YES | **NO** |
| **Context Precision**| 45 | `[-0.053309, 0.001787]` | `[-0.053309, 0.001787]` | `[-0.052515, 0.001243]` | **YES** | YES | **NO** |
| **Context Recall** | 44 | `[-0.080303, 0.059091]` | `[-0.080303, 0.059091]` | `[-0.080303, 0.059848]` | **YES** | YES | **NO** |

**Statistical Conclusion:** Every single 95% bootstrap confidence interval spans zero. There is **no statistically significant difference** between the Baseline and Graph-Assisted pipelines across any primary evaluation metric. The report's cautionary interpretation was correct: neither superiority nor inferiority is statistically established at the cohort level.

---

## 5. Audit D — Timeout and Denominator Accounting

Case `MED-BENCH-029` ("How does diabetic kidney disease develop and what are its clinical stages?") exhibited an internal LLM judge timeout during Baseline Context Recall evaluation (`Job[3] timed out after 180 seconds`).

1. **Baseline Score:** Null / empty in `case_level_scores.csv`.
2. **Graph-Assisted Score:** Successfully scored `0.500000`.
3. **Paired Handling:** In `paired_metric_deltas.csv`, `delta_context_recall` for `MED-BENCH-029` is correctly recorded as empty (`null`).
4. **Denominators:**
   - Faithfulness: 50/50 pairs.
   - Answer Relevancy: 50/50 pairs.
   - Context Precision: 45/45 pairs (5 negative controls excluded by contract).
   - Context Recall: 44/45 pairs (5 negative controls excluded by contract; 1 timeout excluded).

---

## 6. Audit E — Category-Specific Claims Verification

All 10 category claims highlighted in the evaluation report were audited directly against case-level data (see [category_claim_audit.csv](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/category_claim_audit.csv)).

| Category / Cohort | Target Cases | Claimed Metric & Delta | Verified Case-Level Delta | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Drug Brand Lookup** | `MED-BENCH-001..005` | Faithfulness mean delta: `+0.0611` | `+0.0611` (3 win, 1 tie, 1 loss) | **VERIFIED** |
| **Drug Brand Lookup** | `MED-BENCH-002` (Cinzan) | Context Recall jumped 0.50 -> 1.00 (`+0.5000`) | Baseline: `0.5000`, Graph: `1.0000` | **VERIFIED** |
| **Drug Generic Lookup** | `MED-BENCH-006..010` | Faithfulness mean delta: `+0.0950` | `+0.0950` (4 win, 1 loss) | **VERIFIED** |
| **Drug Generic Lookup** | `MED-BENCH-008` (Metformin) | Context Recall jumped 0.33 -> 1.00 (`+0.6667`) | Baseline: `0.3333`, Graph: `1.0000` | **VERIFIED** |
| **Active Ingredient** | `MED-BENCH-011..015` | Answer Relevancy mean delta: `+0.1764` | `+0.1764` | **VERIFIED** |
| **Active Ingredient** | `MED-BENCH-015` (Cipro) | Answer Relevancy jumped 0.00 -> 0.91 (`+0.9093`) | Baseline: `0.0000`, Graph: `0.9093` | **VERIFIED** |
| **Active Ingredient** | `MED-BENCH-013` (Atorvastatin)| Faithfulness reached 1.00 (`+0.7143` delta) | Baseline: `0.2857`, Graph: `1.0000` | **VERIFIED** |
| **Single Symptom** | `MED-BENCH-024` (Headache) | Context Recall doubled 0.50 -> 1.00 (`+0.5000`) | Baseline: `0.5000`, Graph: `1.0000` | **VERIFIED** |
| **Multi-Symptom** | `MED-BENCH-028` (Meningitis) | Faithfulness doubled 0.50 -> 1.00 (`+0.5000`) | Baseline: `0.5000`, Graph: `1.0000` | **VERIFIED** |
| **Multi-Hop Queries** | `MED-BENCH-046..048` | Faithfulness declined by `-0.2071` | `046`: 0.0, `047`: -0.05, `048`: -0.571 | **VERIFIED** |

**Cautionary Assessment:** While all specific numerical claims are mathematically true, each sub-category contains only $N=3$ to $N=5$ cases. These findings are strictly exploratory hypotheses, not statistically generalizable proof of pipeline performance.

---

## 7. Audit F — Negative Controls and Emergency Safety Audit

A complete audit of responses was conducted and documented in [safety_claim_audit.md](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/safety_claim_audit.md).

### 7.1 Negative Controls (`MED-BENCH-041` .. `045`)
- **Distractor Adoption Rate:** **0% (0 / 10 runs)**. Neither Baseline nor Graph adopted fictional treatments (e.g., "Zephastin", "Virokine", "Pulmoflux").
- **Abstention Breakdown:**
  - **Pure Abstention (5 runs):** `MED-BENCH-041` (Base & Graph), `MED-BENCH-043` (Base & Graph), `MED-BENCH-044` (Baseline).
  - **Soft Abstention (5 runs):** `MED-BENCH-042` (Base & Graph), `MED-BENCH-044` (Graph), `MED-BENCH-045` (Base & Graph).
- **Distractor Discussion:** 5 of 10 runs mentioned the distractor name lexically to clarify that no evidence supports it. Neither pipeline endorsed fictional entities.

### 7.2 Emergency Response Safety Regression (`MED-BENCH-038`)
- **Query:** Emergency triage for crushing retrosternal chest pain radiating to left arm with diaphoresis.
- **Baseline Prompt Directive:**
  > *"It is crucial to seek immediate medical attention from a qualified healthcare professional or emergency medical services (e.g., call 911 or visit the nearest emergency room)."*
- **Graph-Assisted Response Text:**
  > *"It is essential to consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment."*
- **Clinical Safety Audit Finding:** Recommending that a patient experiencing classic acute myocardial infarction symptoms consult a *pharmacist* represents a **potential safety regression**. Appending structured graph evidence diluted the model's triage urgency. This finding is classified as a critical triage anomaly requiring qualified medical review.

---

## 8. Audit G — Interpretation, Strategic Decisions & Recommendations

1. **General Graph Superiority is NOT Supported:** Across all 50 cases, the paired differences in Faithfulness (-0.0116), Answer Relevancy (+0.0286), Context Precision (-0.0243), and Context Recall (-0.0121) are negligible, and all bootstrap confidence intervals span zero.
2. **Context Dilution is Real:** Appending supplemental graph triples degraded Context Precision (-0.0243) and induced hallucinations in multi-hop queries (`MED-BENCH-048` Faithfulness dropped from 0.857 to 0.286).
3. **Selective Graph Augmentation as a Future Hypothesis:** Knowledge graph retrieval should not be applied globally. Instead, future engineering should investigate a **selective routing strategy** that activates graph augmentation exclusively for structured entity queries (drug lookups, ingredient lookups, interaction checks) while routing unstructured multi-hop and emergency queries directly to dedicated clinical triage protocols.

---

## 9. Deliverables Inventory

The following files under `evaluation/ragas/phase_c_5/audit_c5_1/` constitute the complete audit package:

1. [audit_report.md](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/audit_report.md) — Comprehensive methodology, recomputed metrics, and verdict.
2. [recomputed_metrics.json](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/recomputed_metrics.json) — Independent aggregate metrics and strata denominators.
3. [metric_discrepancies.csv](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/metric_discrepancies.csv) — Catalog of discrepancies DISC-001 through DISC-004.
4. [bootstrap_verification.json](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/bootstrap_verification.json) — Bootstrap verification results and stability checks.
5. [category_claim_audit.csv](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/category_claim_audit.csv) — Case-by-case audit of 10 category claims.
6. [safety_claim_audit.md](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/safety_claim_audit.md) — Detailed inspection of negative controls and emergency safety.
7. [integrity_report.json](file:///Users/sj/Documents/mediscanai/evaluation/ragas/phase_c_5/audit_c5_1/integrity_report.json) — Formal gate evaluations and invariant checks.
