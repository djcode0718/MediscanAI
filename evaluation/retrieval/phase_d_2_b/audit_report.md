# MediScanAI Phase D.2.b — Audit Report & Mandatory Verification Gate

**Document Version:** 1.0.0  
**Phase:** Phase D.2.b Cross-Encoder Thresholding and Section-Aware Passage Reranking  
**Date:** 2026-10-16  
**Author:** Senior RAG Retrieval Engineer  
**Status:** COMPLETE & VERIFIED  

---

## 1. Mandatory Verification Gate Decisions

Before commencing experimental reranking work in Phase D.2.b, all three outstanding concerns required by the project protocol were forensically audited and verified:

| Verification Gate | Focus Area | Audit Status | Gate Decision |
| :--- | :--- | :---: | :---: |
| **Gate A** | Generic-Drug Judgment Sparsity & Equivalence Criteria | Audited & Validated | **PASS** |
| **Gate B** | Metric and Judgment Provenance & Reproduction | 100% Reproduced | **PASS** |
| **Gate C** | Clinical Safety, Abstention, and Invariant Suites | 100% Verified | **PASS** |

---

## 2. Gate A: Generic-Drug Judgment Sparsity & Equivalence Criteria

### 2.1 Empirical Findings on Benchmark Sparsity
An inspection of `data/drugs_faiss_data.jsonl` demonstrates why generic drug lookups (e.g., `MED-BENCH-011` Metformin) exhibited artificial 0.0 Recall in Phase D.1 and D.2.a under strict record ID matching:
- **Metformin (`MED-BENCH-011`):** 332 individual records in `drugs_faiss_data.jsonl` contain `METFORMIN HYDROCHLORIDE`.
- **Acetaminophen (`MED-BENCH-012`):** 240+ records contain `ACETAMINOPHEN`.
- **Ibuprofen (`MED-BENCH-009`):** 180+ records contain `IBUPROFEN`.
- In `evidence_verified_judgments.jsonl`, only **one single sampled catalog row** (e.g. `drug_345` for Metformin, `drug_25` for Acetaminophen) was labeled as relevant.
- During D.2.a retrieval, the system retrieved 10 authoritative FDA Metformin monotherapy records (records `20422`, `76560`, `6269`, `8100`, etc.), yet strict string matching against `drug_345` yielded `recall = 0.0`.

### 2.2 Strict Equivalence Rules (No False Assumptions)
We do **not** assume that identical chemical names imply bioequivalent formulations:
1. **Monotherapy vs. Combination Distinction:** A monotherapy product (`substance_name == ["METFORMIN HYDROCHLORIDE"]`) cannot be credited as matching a combination product (e.g., Metformin + Glipizide or Metformin + Sitagliptin).
2. **Strength & Release Mechanism Preservation:** Where a query specifies a strength (e.g., `500mg ER`), only matching extended-release formulations are valid.
3. **Dual Reporting Requirement:** Phase D.2.b will report two distinct tracks:
   - **Track 1: Record-Level Metrics** (strictly matching explicit IDs in `evidence_verified_judgments.jsonl`).
   - **Track 2: Canonical-Entity Metrics** (crediting records matching the verified active substance and monotherapy constraint via a separate adapter).

---

## 3. Gate B: Metric & Judgment Provenance Audit

### 3.1 Provenance of `evidence_verified_judgments.jsonl`
- **File Path:** `evaluation/benchmark/evidence_adjudication/phase_a_3/evidence_verified_judgments.jsonl`
- **File Size:** 54,088 bytes
- **SHA256 Digest:** `f43ecc8d0f8e7ff82deefd0b39b2cda41c0cb4a8ac261c3192c77ba090fa4584`
- **Record Count:** 62 judgments covering 50 benchmark cases
- **Adjudicator Type:** `ai_assisted_external_evidence`
- **Human Reviewed Field:** **`False` for 100% of records**
- **Explicit Limitations:** *"AI-assisted research evaluation against authoritative labeling; not licensed human clinical sign-off."*
- **Official Gold File:** `evaluation/benchmark/gold_judgments.jsonl` is verified at **exactly 0 bytes**.
- **Auditor Determination:** `evidence_verified_judgments.jsonl` represents provisional, AI-assisted benchmark judgments. It must **never** be misrepresented as licensed clinical gold.

### 3.2 Independent Recomputation of Phase D.2.a Metrics
Using the saved case-level rankings in `evaluation/retrieval/phase_d_2_a/case_level_results.jsonl`, all metrics were independently recomputed:

| Split | Published Recall@5 | Recomputed Recall@5 | Published MRR@10 | Recomputed MRR@10 | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Development ($N=30$)** | 0.4444 | 0.4444 | 0.3544 | 0.3544 | **100% REPRODUCED** |
| **Validation ($N=10$)** | 0.4444 | 0.4444 | 0.3056 | 0.3056 | **100% REPRODUCED** |
| **Held-Out Test ($N=10$)** | 0.6667 | 0.6667 | 0.5370 | 0.5370 | **100% REPRODUCED** |

Zero discrepancies exist. All reported numbers are completely verifiable.

### 3.3 Verification of Disease-Chunk ID Normalization
- In `data/diseases_faiss_data.jsonl`, record chunks are formatted as `{"id": "chunk_2501", ...}`.
- In `evidence_verified_judgments.jsonl`, canonical evidence IDs are formatted as `"disease_chunk_2501"`.
- `normalize_disease_chunk_id("chunk_2501")` extracts digits and produces `"disease_chunk_2501"`.
- Regression test confirmed: Both prefixed (`chunk_2501`) and unprefixed (`2501`) strings correctly map to `"disease_chunk_2501"`.

---

## 4. Gate C: Clinical Safety, Abstention & Hard Invariants

### 4.1 Verified Invariants:
1. **Fictional Entity Interception:** Queries with clinical framing words (`Zephastin 50mg indications`, `Virokine dosage and usage`, `Pulmoflux for acute respiratory infection`) are intercepted by the Upstream Lexical Entity Verification Gate with **0 candidates retrieved** (`CLEAN_ABSTAIN`).
2. **Emergency Red-Flag Escalation:** Chest pain radiating to arm, stroke signs, and anaphylaxis are routed to `TRIAGE_ESCALATE` with **0 candidates retrieved**.
3. **Symptom-Only Non-Prescribing:** Queries like "I have a headache" and "oliguria" retrieve disease etiology records without prescribing medications.
4. **OCR Uncertainty Gating:** Unreadable blurred images trigger `CLARIFICATION_REQUIRED` without hallucinating nearest-neighbor products.

**Gate Decision Summary:** All three gates (A, B, C) are **PASSED**. Experimental reranking investigation is authorized.
