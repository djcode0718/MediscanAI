# MediScanAI Phase D.2.a — Architecture & Empirical Failure Audit

**Document Version:** 1.0.0  
**Phase:** Phase D.2.a Hybrid Retrieval Coverage and Intent Routing  
**Date:** 2026-10-16  
**Author:** Senior RAG Retrieval Engineer  
**Status:** COMPLETE & VERIFIED  

---

## 1. Executive Summary & Audit Mandate

Phase D.2.a conducts an exhaustive, evidence-backed audit of the Phase D.1 hybrid retrieval baseline and experimental components. The audit evaluates candidate retrieval across **50 benchmark queries** partitioned deterministically into:
- **Development Split:** 30 cases (60%)
- **Validation Split:** 10 cases (20%)
- **Held-Out Test Split:** 10 cases (20%) — sealed during router development and candidate tuning.

The audit identified three major structural bottlenecks responsible for missed relevant evidence, low recall, and safety regression vulnerabilities in D.1:
1. **Critical Evaluator Normalization Bug (`disease_chunk_chunk_*`):**
   In Phase D.1 (`evaluation/retrieval/phase_d_1/run_experiments.py`, line 90), disease chunks were formatted as `f"disease_chunk_{chunk_id}"`. Because chunk records in `data/diseases_faiss_data.jsonl` already carry the `"chunk_"` prefix (e.g., `"chunk_2501"`), this logic produced `"disease_chunk_chunk_2501"`. Every disease retrieval candidate failed string matching against the canonical evidence IDs (`"disease_chunk_2501"`), resulting in an artificial reported Recall@5/10 of `0.0000` across all 15 disease-related benchmark queries.
2. **Channel Competition & Monolithic Concatenation:**
   The baseline and D.1 retrievers indiscriminately queried both `drugs` and `diseases` for every input text, concatenating 10 drug items followed by 10 disease items (`retrieved_drugs + retrieved_diseases`). For symptom-only queries, the top 5 slots were monopolized by irrelevant prescription drug inserts. For drug lookups, disease records competed with target pharmaceutical products.
3. **Lexical Leakage of Medical Framing Words in Negative Controls:**
   Fictional drug queries containing authentic clinical modifiers (e.g., `Zephastin 50mg indications`, `Virokine dosage and usage`, `Pulmoflux for acute respiratory infection`) bypassed cross-encoder thresholding because `cross-encoder/ms-marco-MiniLM-L-6-v2` attends heavily to common clinical phrasing (`"50mg"`, `"dosage"`, `"indications"`), scoring them positively despite non-existent primary chemical entities.

---

## 2. Root Cause Classification of All 50 Benchmark Queries

Each query was inspected at the candidate ID and channel rank level across Dense FAISS, BM25, and RRF fusion:

| Root Cause Category | Query Count | Benchmark Query IDs | Technical Explanation |
| :--- | :---: | :--- | :--- |
| **None (Success in D.1)** | 11 | `MED-BENCH-001`, `002`, `003`, `004`, `005`, `007`, `016`, `018`, `019`, `046`, `049` | Direct brand lookup or distinct chemical name cleanly retrieved in top 5 by BM25 + dense fusion. |
| **Evaluation Bug + Channel Competition** | 15 | `MED-BENCH-021` to `MED-BENCH-035` | (1) `disease_chunk_chunk_*` formatting prevented canonical match; (2) Drugs concatenated ahead of diseases crowded top 5 ranks. In fact, 12 of these 15 cases retrieved the true gold disease chunk in top 5 of the disease index. |
| **Incomplete Relevance Judgments (Sparsity)** | 9 | `MED-BENCH-006`, `008`, `009`, `010`, `011`, `012`, `013`, `014`, `015` | High-frequency generic drugs (e.g. Metformin, Acetaminophen, Ibuprofen) have 100–350+ valid catalog records. The benchmark only annotated a single arbitrary sampled row (`drug_345` for Metformin). Top retrieval returned 10 valid Metformin records, but scored 0 against unpooled single-row gold. Additionally, BM25 penalized `drug_345` due to document length normalization. |
| **Incorrect Intent / Ambiguity Handling** | 5 | `MED-BENCH-036` to `MED-BENCH-040` | Ambiguous queries (e.g. `diabetes`, `hypertension`, `cough`) were dispatched blindly to monolithic retrieval without multi-route support or clarification disambiguation. |
| **Wrong Index Selection / Channel Competition** | 2 | `MED-BENCH-017`, `020` | Relational queries (brand vs. generic) retrieved monolithic inserts rather than paired entity relationship evidence. |
| **Channel Competition / Pool Truncation** | 3 | `MED-BENCH-047`, `048`, `050` | Multi-hop / graph queries where relevant textual evidence fell outside top 15 RRF candidate cutoff. |
| **Negative Control / Safety Abstention Target** | 5 | `MED-BENCH-041` to `MED-BENCH-045` | Unanswerable queries intended for clean zero-retrieval / abstention. |
| **Total Benchmark Cohort** | **50** | `MED-BENCH-001` through `MED-BENCH-050` | **100% Accounted For** |

---

## 3. Split Assignment Verification & Leakage Audit

The 50 benchmark queries were partitioned into Stratified Splits:
- **Development Split (30 cases):** `MED-BENCH-001..003`, `006..008`, `011..013`, `016..018`, `021..023`, `026..028`, `031..033`, `036..038`, `041..043`, `046..047`, `049`.
- **Validation Split (10 cases):** `MED-BENCH-004`, `009`, `014`, `019`, `024`, `029`, `034`, `039`, `044`, `048`.
- **Held-Out Test Split (10 cases):** `MED-BENCH-005`, `010`, `015`, `020`, `025`, `030`, `035`, `040`, `045`, `050`.

### Integrity Findings:
1. **Zero Duplicate Queries:** Every query text across the 50 cases is strictly unique.
2. **Category Balance:** Each of the 10 categories has 3 Dev, 1 Val, 1 Test (or 2 Dev, 1 Val for 3-case categories; 1 Dev, 1 Test for 2-case categories).
3. **Sealed Held-Out Policy:** All router rules, candidate pool thresholds, and feature flags are designed and validated exclusively on Dev and Val splits. The Held-Out split is evaluated strictly once at the end of D.2.a.
4. **Gold File Restriction Maintained:** `evaluation/benchmark/gold_judgments.jsonl` remains **0 bytes**.

---

## 4. Architectural Interventions for Phase D.2.a

To resolve the audited root causes, Phase D.2.a implements:
1. **Query Intent Router (`IntentRouter`):**
   - Classifies query into 12 taxonomy intents:
     * `brand_lookup`, `generic_lookup`, `active_ingredient`, `drug_purpose_indication` -> Route to `drugs` + `drug_dict`.
     * `symptom_only`, `disease_only`, `multi_symptom` -> Route to `diseases`.
     * `brand_generic_comparison` -> Route to `drugs` (multi-entity union).
     * `ambiguous_underspecified` -> Multi-route or clarification flag.
     * `ocr_medicine_image` -> Route OCR tokens to `drugs` + `drug_dict`.
     * `unverified_fictional_negative` -> Upstream Lexical Verification Gate (immediate abstention).
     * `emergency_escalation` -> Immediate Red-Flag triage interception.
2. **Upstream Lexical Entity Verification Gate:**
   - Verifies extracted candidate drug/brand tokens against unified catalog. Intercepts `Zephastin`, `Virokine`, `Pulmoflux` before neural reranking.
3. **Corrected Canonical Evidence ID Normalization:**
   - Uses `normalize_disease_chunk_id` (`disease_chunk_<number>`) to guarantee 100% compatibility with benchmark judgments.
4. **Expanded Candidate Pool (30 items):**
   - Expands candidate pool from 15 to 30 items for RRF fusion, preventing candidate loss before cross-encoder scoring.
