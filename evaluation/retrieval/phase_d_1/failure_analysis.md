# MediScanAI Phase D.1 — Empirical Failure Analysis & Technical Post-Mortem

**Document Version:** 1.0.0  
**Phase:** Phase D.1 Evaluation Analysis  
**Date:** 2026-10-16  
**Author:** Senior RAG Retrieval Engineer  
**Scope:** Root-cause investigation of negative control leakages, held-out split generalization drop, and cross-encoder scoring dynamics.

---

## 1. Executive Summary of Observed Failures

Phase D.1 implemented significant structural improvements over the baseline:
- **Startup Indexing Acceleration:** BM25 indexing time dropped from **40.54s** to **7.15s** (over 5x faster) by removing destructive SymSpell word replacements.
- **Brand Match Fidelity:** Known brand names (`Lipitor`, `Cinzan`, `Amoxil`, `Augmentin`, `Panadol`) are preserved verbatim without corruption into common English words (`visitor`, `conan`, `mobil`, `augmenting`, `paradox`).
- **OCR Readability Gating:** Low-confidence / blurry images are successfully flagged as `UNREADABLE_UNCERTAIN`, triggering zero-retrieval and user clarification instead of hallucinatory nearest-neighbor matches.

However, two major technical failure modes were revealed during the empirical evaluation:
1. **Semantic Leakage in Fictional Entity Queries (`SR-01`, `SR-02`, `SR-03`):** While completely fictional drug queries with non-medical framing (`SR-05` Noxipram) were cleanly rejected, fictional queries containing valid clinical framing words (`"50mg indications"`, `"dosage and usage"`, `"for acute respiratory infection"`) passed the cross-encoder with positive scores ($+1.18$ to $+3.50$).
2. **Generalization Drop on Held-Out Split:** Macro Recall@5 dropped from `0.2963` on the Development split to `0.1111` on the Held-Out Test split, demonstrating that candidate slot competition between diseases and drugs dilutes top-5 hits in the absence of query-intent routing.

---

## 2. Root Cause Analysis: The "Framing Word" Leakage Phenomenon

### 2.1 The Observation
In [`safety_regression_results.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/safety_regression_results.json), the Safety Regression Suite evaluated 5 unanswerable / fictional entity cases:

| Case ID | Query Text | Target | Observed Result | Cross-Encoder Top Score | Retrieved Brand |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SR-01`** | `Zephastin 50mg indications` | 0 items (Rejection) | **FAIL** (5 items) | $+1.1860$ | Haloperidol Decanoate |
| **`SR-02`** | `Virokine dosage and usage` | 0 items (Rejection) | **FAIL** (5 items) | $+3.5023$ | Doxycycline Hyclate |
| **`SR-03`** | `Pulmoflux for acute respiratory infection` | 0 items (Rejection) | **FAIL** (4 items) | $+2.0574$ | Azithromycin |
| **`SR-04`** | `Does Lipitor cure acute viral Covid-19 infection?` | Statin grounding | **PASS** (5 items) | $+1.8071$ | Lipitor |
| **`SR-05`** | `Noxipram side effects` | 0 items (Rejection) | **PASS** (0 items) | None (all $< -2.0$) | *None (Clean Abstention)* |

### 2.2 Mechanism of Failure
Why did `SR-05` (Noxipram side effects) cleanly produce 0 items, whereas `SR-01`, `SR-02`, and `SR-03` produced positive scores?

1. **Domain Mismatch of the Cross-Encoder:**
   - The reranker is `cross-encoder/ms-marco-MiniLM-L-6-v2`, trained on general web search queries from the MS-MARCO dataset.
   - It operates on token cross-attention: Query tokens attend to Document tokens.
2. **Over-Attention to Clinical Modifiers:**
   - In `SR-01`, the tokens `"50mg"` and `"indications"` match hundreds of real drug records in `drugs_faiss_data.jsonl` that state `50mg` in dosage and contain `indications and usage`.
   - In `SR-02`, `"dosage and usage"` matches the standard FDA section header verbatim.
   - In `SR-03`, `"acute respiratory infection"` is a high-frequency indication across macrolide antibiotics (Azithromycin).
3. **The Insufficiency of Static Score Thresholding:**
   - The cross-encoder assigned high positive similarity to the real clinical phrases in the query, completely ignoring the fact that the primary chemical entity (`Zephastin`, `Virokine`, `Pulmoflux`) does not exist.
   - Raising the threshold $\tau$ to $+3.6$ would reject `SR-02`, but would simultaneously wipe out legitimate medical queries like `Lipitor cure claim` ($+1.80$) and vague symptom queries (which average $+0.5$ to $+2.0$).

### 2.3 Required Phase D.2 Engineering Solution
Static score thresholding alone is insufficient to prevent hallucinated drug retrievals.
**Architectural Solution for Phase D.2:** Implement an **Upstream Lexical Entity Verification Gate**:
- Before executing vector and reranker retrieval, extract the candidate chemical/brand token.
- Verify whether the candidate token exists in the unified dictionary (`drugs` + `drug_dict`).
- If an extracted drug token does not exist in the corpus catalog, the query must be intercepted by the rejection gate **before** cross-encoder candidate scoring.

---

## 3. Analysis of Held-Out Generalization Gap

### 3.1 Empirical Split Performance Comparison

| Split | Cases | Macro Recall@5 | Macro Hit Rate@5 | Macro MRR@10 | Macro nDCG@10 | Rejection Acc@5 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Development Split** | 30 | **0.2963** | **0.2963** | **0.2222** | **0.2416** | **33.3%** |
| **Validation Split** | 10 | **0.1667** | **0.2222** | **0.1389** | **0.1353** | **0.0%** |
| **Held-Out Test Split** | 10 | **0.1111** | **0.1111** | **0.0556** | **0.0701** | **0.0%** |

### 3.2 Root Cause of the Held-Out Drop
1. **Category Skew in Small Sample Subsets:**
   - The Held-Out Test split ($N=10$) contains only 9 answerable queries. One missed case reduces Recall by $\approx 11\%$.
   - Held-Out cases included multi-symptom variants (e.g., `MED-BENCH-030` and `MED-BENCH-035`) and clinical contraindication queries (`MED-BENCH-020`).
2. **Context Dilution from Monolithic Retrieval:**
   - In the baseline and D.1 hybrid architectures, both `diseases` and `drugs` are searched for every text query.
   - For a contraindication query like `"Is metformin contraindicated in severe renal impairment?"`, the pipeline retrieves 5 disease chunks and 5 drug chunks. Because both channels compete for candidate slots without intent routing, the specific FDA contraindication record was pushed to lower ranks ($>5$).
3. **Absence of Query Expansion:**
   - Queries with clinical phrasing (e.g., `"pyrexia and cephalalgia"`) fail sparse BM25 matching when corpus chunks use lay phrasing (`"fever and headache"`).

---

## 4. Assessment Against Target Engineering Metrics

The target metrics specified for Phase D.1 were:
- **Faithfulness: > 0.98**
- **Context Recall: > 0.95**
- **Context Precision: > 0.90**

### Auditor Determination:
- These ambitious targets **were not met on the held-out retrieval evaluation**.
- Context Recall on held-out test data achieved `0.1111` (top-5) and `0.1111` (top-10).
- **Engineering Verdict:** Non-destructive tokenization (D1-1) and `drug_dict` integration (D1-2) successfully fixed brand-name corruption and accelerated BM25 by 5x, but **retrieval-side grounding cannot achieve $>0.95$ recall without Phase D.2 Intent Routing and Clinical Query Expansion**.

---

## 5. Technical Recommendations for Phase D.2

1. **Implement Rule-Based Intent Routing (EXP-07):**
   - Direct brand/generic lookups to `drugs` and `drug_dict` only; suppress `diseases`.
   - Direct symptom-only queries to `diseases` only; suppress prescription drugs.
2. **Implement Lexical Entity Verification for Negative Controls:**
   - Enforce exact-match dictionary lookup on primary subject entities before running neural rerankers.
3. **Biomedical Synonym Expansion (EXP-06):**
   - Expand lay terms (`headache`) to clinical synonyms (`cephalalgia, tension headache, migraine`).
4. **Expand Cross-Encoder Candidate Pool from 15 to 30 (EXP-03/05):**
   - Allow more candidates into the reranker before final top-k truncation.
