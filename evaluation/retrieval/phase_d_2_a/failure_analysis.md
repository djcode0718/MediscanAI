# MediScanAI Phase D.2.a — Empirical Failure Analysis & Technical Post-Mortem

**Document Version:** 1.0.0  
**Phase:** Phase D.2.a Hybrid Retrieval Coverage and Intent Routing  
**Date:** 2026-10-16  
**Author:** Senior RAG Retrieval Engineer  
**Scope:** Root-cause analysis of recovered failure modes, remaining coverage gaps, and engineering recommendations for Phase D.2.b.

---

## 1. Executive Summary & Measured Breakthroughs

Phase D.2.a addressed the core coverage bottlenecks identified in Phase D.1, achieving substantial, statistically verified gains across all splits:

| Split | Phase D.1 Recall@5 | Phase D.2.a Recall@5 | Phase D.1 MRR@10 | Phase D.2.a MRR@10 | Improvement Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Development Split** ($N=30$) | 0.2963 | **0.4444** | 0.2222 | **0.3544** | **+50.0% Recall / +59.5% MRR** |
| **Validation Split** ($N=10$) | 0.1667 | **0.4444** | 0.1481 | **0.3056** | **+166.6% Recall / +106.3% MRR** |
| **Held-Out Test Split** ($N=10$) | 0.1111 | **0.6667** | 0.0556 | **0.5370** | **+500.1% (6x) Recall / +865.8% (9.6x) MRR** |

### Key Architectural Fixes:
1. **Resolution of Double-Prefix Bug:** Corrected `disease_chunk_chunk_*` formatting to canonical `disease_chunk_*`, immediately recovering 15 previously missed disease and symptom benchmark cases.
2. **Channel Isolation & Elimination of Context Dilution:** Directed symptom-only and disease queries solely to `diseases`, preventing prescription drugs from monopolizing top ranks.
3. **Upstream Lexical Entity Verification Gate:** 100% intercept rate on negative controls with medical framing words (`Zephastin`, `Virokine`, `Pulmoflux`, `Noxipram`, `Covid-19 cure claim`), eliminating neural cross-encoder false positives.
4. **Emergency Red-Flag Interception:** 100% immediate escalation for acute coronary syndrome, stroke, and anaphylaxis presentations.
5. **100% Pass Rate on Expanded OCR Suite:** Cleanly handled cropped names, spelling noise, generic-only ingredients, and unreadable blur.

---

## 2. Analysis of Remaining Failure Modes

Despite dramatic gains, macro Recall@5 on Dev ($0.4444$) and Val ($0.4444$) leaves a residual gap against the $>0.95$ engineering target. Forensic examination of the candidate pools reveals two primary technical root causes:

### 2.1 Incomplete Relevance Judgments (Benchmark Sparsity on Generic Drugs)
- **Affected Benchmark Cases:** `MED-BENCH-006` (Atorvastatin), `MED-BENCH-008` (Amoxicillin), `MED-BENCH-009` (Ibuprofen), `MED-BENCH-010` (Cetirizine), `MED-BENCH-011` (Metformin), `MED-BENCH-012` (Acetaminophen), `MED-BENCH-013` (Ciprofloxacin), `MED-BENCH-014` (Omeprazole), `MED-BENCH-015` (Lisinopril).
- **Forensic Evidence:**
  * In `data/drugs_faiss_data.jsonl`, there are 332 valid records for Metformin, 180 for Ibuprofen, and 240 for Acetaminophen.
  * For `MED-BENCH-011` ("Metformin"), dense vector retrieval and BM25 returned 10 authoritative, 100% valid FDA Metformin product records (e.g., records `20422`, `76560`, `6269`, `8100`, `42081`).
  * However, the benchmark judgment file (`evidence_verified_judgments.jsonl`) contains **only a single arbitrarily sampled record ID** (`drug_345`).
  * Because unpooled catalog records were left unjudged rather than annotated as equivalent products, the evaluation engine strictly assigned `recall = 0.0` despite the system retrieving 10 flawless Metformin records.
- **BM25 Document-Length Normalization Penalty:**
  * In addition, record `drug_345` contains an exhaustive 4,500-token FDA package insert (full warnings, pharmacokinetics, adverse events).
  * Standard BM25 term weighting penalizes long documents via $b \cdot \frac{|D|}{\text{avgdl}}$. As a result, shorter packaging summaries for Metformin receive higher BM25 scores than `drug_345`.

### 2.2 Relational & Multi-Hop Query Disconnects
- **Affected Cases:** `MED-BENCH-017` (Atorvastatin vs. Lipitor relationship), `MED-BENCH-020` (Metformin renal contraindications), `MED-BENCH-047`, `MED-BENCH-048`.
- **Mechanism:** Text-only retrieval searches isolated chunks. For a query like "Is metformin contraindicated in severe renal impairment?", the specific contraindication sentence is buried deep within the 12th paragraph of the "Warnings and Precautions" section, where dense sentence embeddings dilute relevance compared to short general indication chunks.

---

## 3. Recommended Next Steps for Phase D.2.b

To close the remaining gap in Phase D.2.b without violating evaluation integrity:
1. **Section-Aware Passage Reranking (Phase D.2.b):**
   - Implement structured section segmentation (indexing "Indications", "Contraindications", "Dosage", and "Adverse Reactions" as separate searchable passages rather than monolithic 5,000-word blocks).
2. **Substance-Level Canonical Equivalence Pooling (Evaluation Audit):**
   - Document the benchmark judgment sparsity limitation. Recommend pooling equivalent RxNorm/FDA active ingredient IDs so that retrieving a valid formulation of Metformin is not penalized as an error.
3. **Cross-Encoder Threshold Calibration:**
   - Optimize reranker scoring cutoffs specifically for multi-symptom differential diagnosis.
