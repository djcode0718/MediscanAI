# MediScanAI Phase D.1 — Implementation Audit & Verification Report

**Audit Phase:** Phase D.1 Pre-Implementation Audit  
**Date:** 2026-10-16  
**Auditor:** Senior RAG Retrieval Engineer  
**Objective:** Independently verify the reported Phase D.0 architectural findings directly against the active codebase prior to implementing any code changes.

---

## 1. Executive Verification Summary

Every key finding reported in the Phase D.0 architecture audit was systematically tested and verified against the running codebase (`app/retriever.py`, `app/embeddings.py`, `app/utils.py`, `app/core.py`).

| Claim / Finding | Verified Code Location | Empirical Verification Result | Status |
| :--- | :--- | :--- | :--- |
| **1. Destructive SymSpell Corruption** | `app/utils.py:139` (`normalize_text`) | `Cinzan` -> `conan`<br>`Lipitor` -> `visitor`<br>`Amoxil` -> `mobil`<br>`Augmentin` -> `augmenting`<br>`Panadol` -> `paradox` | **CONFIRMED DEFECT** |
| **2. Startup Indexing Overhead** | `app/retriever.py:254` (`BM25Index.__init__`) | `_tokenize()` called `normalize_text()` on all 79,518 docs, taking **35.95s** of CPU time at startup running SymSpell lookups. | **CONFIRMED BOTTLENECK** |
| **3. Asymmetric `drug_dict` Omission** | `app/core.py:260-307` (`Pipeline.run`) | `user_text` only queries `diseases` and `drugs`. `drug_dict` is only queried when `ocr_text` from an uploaded image is present. Text queries omit 58,332 drug names. | **CONFIRMED DEFECT** |
| **4. Omitted BM25 Fields in Drug Index** | `app/retriever.py:40-45` (`extract_text_for_bm25`) | Only searches `brand_name`, `generic_name`, `substance_name`, `indications_and_usage`. Ommits `warnings_and_cautions`, `adverse_reactions`, and `dosage_and_administration`. | **CONFIRMED DEFECT** |
| **5. Cross-Encoder Context Window & Truncation** | `app/retriever.py:165` (`CrossEncoderReranker.rerank`) | Model is `cross-encoder/ms-marco-MiniLM-L-6-v2` with a hard 512-token limit. Ingests raw untagged concatenation from `extract_text_for_bm25`. | **CONFIRMED DEFECT** |
| **6. Unconditional Top-$K$ Retrieval (No Gating)** | `app/retriever.py:175-176` (`CrossEncoderReranker.rerank`) | Slices `[:top_k]` with zero score thresholding. On fictional query `"Zephastin 50mg indications"`, returns 5 Haloperidol Decanoate records with positive score (+0.6080). | **CONFIRMED SAFETY DEFECT** |
| **7. Separate Unrouted Prompt Sections** | `app/core.py:226-235` (`_format_retrievals`) | Formats separate sections for `DISEASES` and `DRUGS`. Non-medical symptom queries receive unsolicited drug records; brand lookups receive irrelevant disease chunks. | **CONFIRMED DEFECT** |

---

## 2. In-Depth Empirical Verification Notes

### 2.1 The SymSpell Medical Mangling Phenomenon
Running `normalize_text()` on representative pharmaceutical and anatomical terms yielded:
```text
Term                 Normalized Output       Impact on Search
Cinzan               conan                   FAISS & BM25 search for "conan", failing exact brand lookup
Lipitor              visitor                 FAISS & BM25 search for "visitor", suppressing statin match
Amoxil               mobil                   BM25 search misses Amoxil antibiotic packages
Augmentin            augmenting              Corrupts high-volume pediatric amoxicillin/clavulanate
Panadol              paradox                 Corrupts universal paracetamol brand name
```
Because `BM25Index` builds its inverted index by running `self._tokenize(text)` over the 79,518 corpus documents at startup, the corpus documents themselves had their brand names mangled if they matched common English words within Levenshtein edit distance $\le 2$.

### 2.2 Unanswerable Query False-Positive Behavior
Running the baseline retriever on `"Zephastin 50mg indications"` produced:
- Rank 1: `Key: 38081, Score: 0.6080, Brand: Haloperidol Decanoate`
- Rank 2: `Key: 51689, Score: 0.6080, Brand: Haloperidol Decanoate`
- Rank 3: `Key: 58789, Score: 0.6080, Brand: Haloperidol Decanoate`
- Rank 4: `Key: 66098, Score: 0.6080, Brand: Haloperidol Decanoate`
- Rank 5: `Key: 66233, Score: 0.6080, Brand: haloperidol decanoate`

**Clinical Risk Assessment:** Returning a first-generation high-potency antipsychotic (Haloperidol Decanoate) for a non-existent fictional drug compound because the string contained `"50mg"` and `"indications"` demonstrates the severe danger of forced top-$K$ retrieval without relevance gating.

---

## 3. Scope of Phase D.1 Interventions

To systematically address these verified bottlenecks while preserving the baseline, Phase D.1 implements:

1. **`MedicalTokenizer` (Experiment D1-1):**
   - Pure, non-destructive tokenization: Lowercase conversion, whitespace normalization, punctuation and hyphen preservation (`co-amoxiclav`, `l-carnitine`, `500mg`, `10mg/ml`).
   - Zero SymSpell English dictionary replacements.
   - Raw query string retained for exact lexical matching.
2. **`drug_dict` Integration for Text Queries (Experiment D1-2):**
   - Controlled retrieval against `data/drug_dict_faiss_data.jsonl` (58,332 records) for brand and generic entities.
   - Unified composite ID resolution (`drug_dict_<id>`).
   - Intent-aware channel weighting (active on brand/generic/ingredient queries; suppressed on pure symptom queries).
3. **Structured Section-Aware Passage Reranking & Relevance Gating (Experiment D1-3):**
   - Formats candidate drug records into structured, labeled sections (`Brand`, `Generic`, `Ingredients`, `Indications`, `Warnings`, `Dosage`).
   - Implements calibrated logit thresholding $\tau$ calibrated on development cases to cleanly reject unanswerable/fictional entities (returning 0 candidates).
4. **First-Class OCR-Only Input Pipeline:**
   - Evaluates images and OCR strings without user-supplied questions.
   - Distinct extraction of brand names, active ingredients, strengths, and dosage forms.
   - Uncertainty handling for low-confidence or blurry OCR representations.
5. **Deterministic Benchmark & Safety Regression Evaluation:**
   - Evaluates Recall@5/10, Hit Rate@5/10, MRR@10, and nDCG@10 across stratified Dev (30), Val (10), and Held-Out (10) splits.
   - 12-case Safety Regression Suite covering negative controls, chest pain emergency triage (`MED-BENCH-038`), stroke, and pediatric toxicity.
