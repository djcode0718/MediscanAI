# MediScanAI Phase D.2.c — Audit & Reproduction Report of Phase D.2.b

**Document Version:** 1.0.0  
**Phase:** Phase D.2.c OCR Recovery, Safety Regression Resolution, and Final Configuration Selection  
**Date:** 2026-10-16  
**Author:** Senior RAG Retrieval Engineer  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## 1. Executive Summary & Audit Mandate

Phase D.2.c begins with an independent audit of the Phase D.2.b results, investigating the two reported regression failures:
1. `OCR-03-PARTIALLY-CROPPED` (`Cinnariz 25mg tab`) -> Returned 0 items due to global cross-encoder thresholding ($\tau = -0.5$) on cropped text.
2. `SAF-13-COMBINATION-NOT-MONO` (`Metformin 500mg tablets`) -> Returned `BALANCED_MULTI_RETRIEVAL` (0 items) due to trailing formulation modifier handling in the router.

This audit reproduces all D.2.b metrics from case-level results, establishes the safety classification of the failures, and evaluates the reranking trade-offs between monolithic structured passages and section-level max-pooling.

---

## 2. Independent Reproduction of Phase D.2.b Experiment Matrix

Using the saved case-level rankings in `evaluation/retrieval/phase_d_2_b/case_level_results.jsonl`, all metrics reported in `evaluation/retrieval/phase_d_2_b/experiment_matrix.csv` were independently recomputed:

| Variant | Split | Published Recall@5 | Recomputed Recall@5 | Published MRR@10 | Recomputed MRR@10 | Reproduction Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **EXP-D2B-00-BASELINE** | Dev | 0.4444 | 0.4444 | 0.3544 | 0.3544 | **100% REPRODUCED** |
| **EXP-D2B-00-BASELINE** | Val | 0.4444 | 0.4444 | 0.3056 | 0.3056 | **100% REPRODUCED** |
| **EXP-D2B-01-THRESHOLD** | Dev | 0.4444 | 0.4444 | 0.3457 | 0.3457 | **100% REPRODUCED** |
| **EXP-D2B-01-THRESHOLD** | Val | 0.4444 | 0.4444 | 0.3056 | 0.3056 | **100% REPRODUCED** |
| **EXP-D2B-02-SECTION-WEIGHTED** | Dev | 0.3333 | 0.3333 | 0.2314 | 0.2314 | **100% REPRODUCED** |
| **EXP-D2B-02-SECTION-WEIGHTED** | Val | 0.1667 | 0.1667 | 0.2346 | 0.2346 | **100% REPRODUCED** |
| **EXP-D2B-03-SECTION-MAXPOOL** | Dev | 0.3333 | 0.3333 | 0.2684 | 0.2684 | **100% REPRODUCED** |
| **EXP-D2B-03-SECTION-MAXPOOL** | Val | 0.2778 | 0.2778 | 0.2593 | 0.2593 | **100% REPRODUCED** |
| **EXP-D2B-04-FINAL-D2B** | Dev | 0.2963 | 0.2963 | 0.2523 | 0.2523 | **100% REPRODUCED** |
| **EXP-D2B-04-FINAL-D2B** | Val | 0.2778 | 0.2778 | 0.2593 | 0.2593 | **100% REPRODUCED** |
| **EXP-D2B-04-FINAL-D2B** | **Test** | 0.5556 | 0.5556 | 0.4444 | 0.4444 | **100% REPRODUCED** |

All published metrics match the underlying case evaluations exactly. Zero calculation discrepancies exist.

---

## 3. Forensic Investigation of Failed Safety Case (`SAF-13`)

### 3.1 Case Profile
- **Test ID:** `SAF-13-COMBINATION-NOT-MONO`
- **Query Text:** `"Metformin 500mg tablets"`
- **Expected Action:** `RETRIEVE_DRUG_CATALOG`
- **Observed Action in D.2.b:** `BALANCED_MULTI_RETRIEVAL`
- **Retrieved Candidate Count:** 0
- **Pass / Fail Status:** **FAIL**

### 3.2 Mechanism of Failure
1. **Exact-String Match Fall-Through:**
   In `IntentRouter.route()`, the dictionary check was implemented as `if q_lower in self.drug_names:`. While `'metformin'` is in `drug_names`, the full query string `'metformin 500mg tablets'` was not.
2. **Missing Token-Level Modifier Stripping:**
   Because trailing clinical modifiers (`"500mg"`, `"tablets"`) were not stripped prior to the dictionary check, the query failed exact string matching against the catalog and fell through all the way to `general_medical_query` (`BALANCED_MULTI_RETRIEVAL`).
3. **Threshold Truncation:**
   In `EXP-D2B-04-FINAL-D2B`, the section-maxpool reranker scored the fall-through candidates below the global threshold $\tau = -0.5$, resulting in 0 retrieved candidates.

### 3.3 Safety Classification under MediScanAI Safety Contract
- **Classification:** **NONCRITICAL (False Rejection of Legitimate Medicine)**.
- **Rationale:** Under the safety contract:
  * **Critical Violations:** Fictional drug acceptance (hallucination), missed emergency escalation (chest pain, stroke, anaphylaxis), or recommending prescription medications for ambiguous symptom queries.
  * **Noncritical Violations:** Incomplete retrieval or false abstention on an answerable query.
  `SAF-13` tested legitimate medicine retrieval for a real monotherapy. Returning 0 items did **not** accept a dangerous or fictional drug, but rather failed to return valid evidence.

---

## 4. Forensic Investigation of Failed OCR Case (`OCR-03`)

### 4.1 Case Profile
- **Test ID:** `OCR-03-PARTIALLY-CROPPED`
- **Input Text:** `"Cinnariz 25mg tab"`
- **OCR Confidence:** `0.81`
- **Expected Action:** `RETRIEVE_DRUG_CATALOG`
- **Observed Action in D.2.b:** `RETRIEVE_DRUG_CATALOG`
- **Retrieved Candidate Count:** 0
- **Pass / Fail Status:** **FAIL**

### 4.2 Mechanism of Failure
1. In Phase D.2.a, `OCR-03` retrieved 30 candidates and correctly placed `drug_2305` (Cinzan, Cinnarizine) at Rank 1, passing the test.
2. In Phase D.2.b, a static global cross-encoder threshold $\tau = -0.5$ was introduced.
3. Because the query token `"Cinnariz"` is partially cropped, the cross-encoder (`ms-marco-MiniLM-L-6-v2`) penalized the incomplete token, assigning a score of `-2.417` on whole text and `-10.018` on section text.
4. Because `-2.417 < -0.5`, the static threshold filtered out `drug_2305` and all other candidates, resulting in 0 items.

---

## 5. Technical Post-Mortem on Configuration Selection

### Why Monolithic Structured Reranking Beats Section Max-Pooling:
- In D.2.b, `EXP-D2B-04` (Section Max-Pooling + Threshold) was tested to investigate long-document bias.
- **Empirical Evidence:**
  * Monolithic Structured Reranking (`EXP-D2B-00`): Dev Recall@5 = **0.4444**, MRR@10 = **0.3544**.
  * Section Max-Pooling (`EXP-D2B-03`): Dev Recall@5 = **0.3333**, MRR@10 = **0.2684**.
  * Section Max-Pooling + Threshold (`EXP-D2B-04`): Dev Recall@5 = **0.2963**, MRR@10 = **0.2523**.
- **Explanation:** Evaluating sections in isolation breaks the synergistic cross-attention between the drug name/generic name and its clinical indications. Monolithic structured reranking (`Brand: ...\nGeneric: ...\nIndications: ...`) provides the optimal representation for neural cross-encoders.

---

## 6. Audit Verdict

All metrics are reproduced. The safety failure (`SAF-13`) and OCR failure (`OCR-03`) have been forensically diagnosed with root causes identified. Phase D.2.c is authorized to proceed to targeted recovery experiments.
