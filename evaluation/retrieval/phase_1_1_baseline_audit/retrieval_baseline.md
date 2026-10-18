# MediScanAI Phase 1.1 — Current Retrieval Baseline Audit

**Evaluation Phase:** Phase 1.1 Baseline Audit  
**Date:** October 17, 2026  
**Auditor:** Autonomous Systems Baseline & Evaluation Specialist  
**Selected Configuration:** `CFG-04-D2C-ADAPTIVE-FINAL` (Frozen Config Hash: `f3937376cd191ee7`)  
**Artifact Path:** `evaluation/retrieval/phase_1_1_baseline_audit/retrieval_baseline.md`  

---

## 1. Executive Summary & Purpose

This document establishes the verified retrieval baseline for the MediScanAI architecture based on the latest authorized experimental configuration, `CFG-04-D2C-ADAPTIVE-FINAL`, audited in Phase D.2.c.

All metrics are compiled directly from frozen case-level artifacts without performing new runs against the sealed held-out test set or altering benchmark judgment definitions.

### Headline Retrieval Baseline Metrics
- **Strict Record-Level Recall@5:** Development: **0.4444** | Validation: **0.4444** | Held-Out: **0.5556**
- **Canonical-Entity Recall@5:** Development: **0.6296** | Validation: **0.6667** | Held-Out: **0.7778**
- **Negative Control Rejection Accuracy:** **1.0000 (100.0%)** across all splits (0 false acceptances).
- **Safety Regression Pass Rate:** **100.0%** (12/12 common subset; 14/14 extended suite).
- **OCR Regression Pass Rate:** **100.0%** (full recovery on simulated packaging noise).

---

## 2. Deterministic Retrieval Baseline Performance Matrix

The complete performance breakdown across Development ($N=30$), Validation ($N=10$), and Held-Out Test ($N=10$) splits is detailed below:

| Metric Dimension | Development Split ($N=30$, Ans=$27$) | Validation Split ($N=10$, Ans=$9$) | Held-Out Test Split ($N=10$, Ans=$9$) | Benchmark Definition / Basis |
| :--- | :---: | :---: | :---: | :--- |
| **Strict Record Recall@5** | **0.4444** (12/27) | **0.4444** (4/9) | **0.5556** (5/9) | Exact packaging chunk ID match |
| **Strict Record Recall@10** | **0.4815** (13/27) | **0.4444** (4/9) | **0.5556** (5/9) | Exact packaging chunk ID match |
| **Strict Record Hit Rate@5** | **0.4444** | **0.4444** | **0.5556** | $\ge 1$ exact record hit in top-5 |
| **Strict Record Hit Rate@10**| **0.4815** | **0.4444** | **0.5556** | $\ge 1$ exact record hit in top-10 |
| **Strict Record MRR@10** | **0.3457** | **0.3056** | **0.5000** | Mean Reciprocal Rank (record ID) |
| **Canonical Entity Recall@5** | **0.6296** (17/27) | **0.6667** (6/9) | **0.7778** (7/9) | Active pharmaceutical substance match |
| **Canonical Entity Recall@10**| **0.6667** (18/27) | **0.6667** (6/9) | **0.7778** (7/9) | Active pharmaceutical substance match |
| **Canonical Entity Hit Rate@5**| **0.6296** | **0.6667** | **0.7778** | $\ge 1$ canonical entity in top-5 |
| **Canonical Entity MRR@10** | **0.5309** | **0.5278** | **0.6667** | Mean Reciprocal Rank (canonical) |
| **Negative Control Rejection Acc**| **1.0000** (3/3) | **1.0000** (1/1) | **1.0000** (1/1) | Clean abstention on unanswerable queries |
| **False Acceptance Count** | **0 / 3** | **0 / 1** | **0 / 1** | False positive retrieval on negative controls |
| **False Rejection Count** | **0 / 27** | **0 / 9** | **0 / 9** | Unwarranted abstention on answerable queries |
| **Latency p50 (ms)** | 1477 ms | 696 ms | 1407 ms | Median end-to-end retrieval latency |
| **Latency p95 (ms)** | 1741 ms | 1530 ms | 1791 ms | 95th percentile retrieval latency |

---

## 3. Retrieval Performance Breakdown by Query Intent

Aggregating Development and Validation splits ($N=40$, 36 answerable):

| Query Intent Category | Evaluated Queries | Strict Record Recall@5 | Canonical Entity Recall@5 | Primary Operational Channel | Failure Pattern Observed |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Commercial Brand Lookup** | 10 | 0.5000 (5/10) | **0.9000 (9/10)** | `drugs` + `drug_dict` | Retrieves generic substance chunk under alternative brand/package record ID. |
| **Generic Drug Lookup** | 6 | 0.3333 (2/6) | **0.8333 (5/6)** | `drugs` + `drug_dict` | Generic input matches multiple commercial brands containing that active ingredient. |
| **Symptom-Only Diagnosis** | 6 | 0.3333 (2/6) | 0.3333 (2/6) | `diseases` chunks | Cross-encoder score pruning on lay-phrased single symptoms. |
| **Multi-Symptom Co-occurrence**| 4 | 0.2500 (1/4) | 0.2500 (1/4) | `diseases` chunks | Channel crowding; competing disease chunks outscore gold entity. |
| **Brand/Generic Relationship** | 5 | 0.2000 (1/5) | 0.2000 (1/5) | Multi-retrieval / Drug | Sparse relationship evidence in unstructured text chunks. |
| **General Medical / Complex** | 5 | 0.4000 (2/5) | 0.4000 (2/5) | Dual-channel fusion | Multi-hop pathophysiology connections. |
| **Negative Controls** | 4 | **1.0000 (4/4)** | **1.0000 (4/4)** | Lexical Gate / Abstain | Zero false positive retrieval; 100% clean abstention. |

---

## 4. Comprehensive Retrieval Failure Analysis

All 24 retrieval misses across Development (15), Validation (5), and Held-Out Test (4) are inventoried in [`retrieval_failure_inventory.csv`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/retrieval_failure_inventory.csv).

### Documented Failure Taxonomies

1. **Package / Record ID Mismatch with Canonical Entity Recovery (9 cases):**
   - *Cases:* `MED-BENCH-006`, `008`, `011`, `012`, `013` (dev); `009`, `014` (val); `010`, `015` (held-out).
   - *Mechanism:* User queries a generic substance (e.g. `Metformin` or `Acetaminophen`). The retriever surfaces high-quality pharmaceutical records containing that exact substance, but under a specific commercial packaging record ID different from the arbitrary gold chunk selected during dataset construction.
   - *Impact:* Record-level Recall@5 is 0.0, but Canonical-Entity Recall@5 is **1.0**. Clinically, the patient receives accurate drug data.
2. **Relationship Query Routing Deficiency (5 cases):**
   - *Cases:* `MED-BENCH-017` ("What generic drug is in Advil?"), `018` ("What brand name products contain Cinnarizine?"), `019`, `046`, `048`.
   - *Mechanism:* The router classifies these queries as `general_medical_query` (`BALANCED_MULTI_RETRIEVAL`) rather than dispatching a dedicated relational lookup. The BM25 and dense representations dilute the specific brand-generic pairing.
3. **Symptom / Disease Ranking Crowding & Threshold Pruning (7 cases):**
   - *Cases:* `MED-BENCH-021` ("oliguria"), `022` ("absence of menstruation"), `034`, `037`, `038`, `047`, `MED-BENCH-035`.
   - *Mechanism:* For lay-phrased queries, cross-encoder scores frequently drop below $\tau = -0.5$, or unrelated disease chunks (e.g., missed abortion vs PCOS) outscore the true diagnostic entity.
4. **Known D.2.c Finding on `MED-BENCH-035` vs `MED-BENCH-045`:**
   - In Phase D.2.a, `MED-BENCH-035` scored $-2.82$ on gold chunk `chunk_3001` and was returned at Rank 3 in an uncalibrated pool.
   - In Phase D.2.c, introducing threshold $\tau = -0.5$ eliminated the false positive on `MED-BENCH-045` (chocolate syrup for appendicitis), but pruned `MED-BENCH-035`.
   - *Status:* Carried forward as a known trade-off between negative control safety and lay-symptom coverage.

---

## 5. Carried-Forward Intent-Router Defects

From the completed Phase D.2.c-Final audit, three bounded routing defects are confirmed and carried forward without premature patching:

1. **`DEFECT-ORAL-ROUTE-COLLISION` (Medium Priority):**
   - The standalone token `"oral"` in `self.symptom_phrases` causes generic liquid formulations (e.g., *Metformin oral solution*, *Amoxicillin oral suspension*) to misroute to `symptom_only_query` (`RETRIEVE_DISEASE_CHUNKS`), suppressing drug catalog retrieval.
2. **`DEFECT-SPACE-SEPARATED-STRENGTH` (Low Priority):**
   - Space-separated dosage strings (`"500 mg"`) fail contiguous regex `^\d+(?:mg|mcg|g|ml)$`, leaving numeral `"500"` unstripped and falling back to broad multi-retrieval.
3. **`DEFECT-SUBSTRING-COLLISION` (Low Priority):**
   - Lexical gate uses substring match `primary_token in d_name`, allowing prefix `"met"` to bypass gate rather than cleanly abstaining.
