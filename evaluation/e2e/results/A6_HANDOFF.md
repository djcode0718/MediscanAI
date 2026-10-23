# MediScanAI Candidate A6 Handoff Contract
**Date:** 2026-10-23  
**Source Revision (Commit):** `4bbc392`  
**Working Branch:** `exp/ragas-opt`  
**Evaluator:** `SELF-JUDGED (llama3.1:8b)` on `dev_subset_40.json` (40 frozen development cases)  

---

## 1. Executive Summary & Verification

Candidate A6 introduced **Claim-Level Grounding, Positive Indication Framing, and Deterministic Claim/Citation Sanitization** (via Prompt v5 and `validate_and_sanitize_claims`).

| Metric | A5 Baseline | A6 Candidate | Delta |
|---|---|---|---|
| **Mean Faithfulness** | **0.7538** | **0.8021** | **+0.0483** (+6.4%) |
| **Median Faithfulness** | **0.8000** | **1.0000** | **+0.2000** |
| **Valid Scores** | 40/40 (100%) | 40/40 (100%) | +0 |
| **Unsupported Statements** | 40 | 34 | -6 (-15.0%) |
| **Invalid Citation Tags** | 0 | 0 | 0 |
| **Paired Wins / Losses / Ties** | - | - | 11 wins / 7 losses / 22 ties |
| **Average Latency** | 24,339 ms | 23,881 ms | -458 ms |
| **Full Fast Test Suite** | 204 passing | 204 passing | +1 new test |

---

## 2. Category Performance Comparison

| Category | Cases | A5 Mean | A6 Mean | Delta | Analysis |
|---|---:|---:|---:|---:|---|
| `medicine_only_clean_ocr` | 6 | 0.9667 | **1.0000** | +0.0333 | Perfect 1.0000 across all 6 cases. |
| `medicine_only_noisy_ocr` | 5 | 0.9333 | 0.8000 | -0.1333 | 4/5 cases at 1.0000, 1 case (`E2E-041`) regressed due to cross-entity attribute hallucination. |
| `symptom_only` | 8 | 0.6628 | **0.8500** | **+0.1872** | **Major breakthrough recovery**: eliminating "also includes" and negative disclaimers resolved previous regressions. |
| `symptom_plus_medicine_match` | 8 | 0.8604 | **0.8793** | +0.0189 | Solid preservation and slight gain; bounded claim templates avoided run-on inferences. |
| `symptom_plus_medicine_mismatch` | 6 | 0.8056 | **0.8889** | +0.0833 | Positive indication framing prevented negative symptom enumeration penalties. |
| `unanswerable` | 7 | 0.3809 | 0.4167 | +0.0358 | Modest gain (`E2E-091` jumped from 0.0 to 1.0000), but remaining probe penalties persist. |

---

## 3. What A6 Resolved vs What Remained Broken

### Resolved:
1. **Symptom-Only Narrative Inflation:** In A5, cases like `E2E-008`, `E2E-024`, and `E2E-025` suffered from "also includes" additive leaps. In A6, these all achieved 1.0000.
2. **Mismatch Negative Enumerations:** Positive indication framing prevented enumerating unindicated user symptoms (e.g. `E2E-080` jumped from 0.5 to 1.0000; `E2E-081` from 0.6667 to 1.0000).
3. **Clean OCR Entity Grounding:** Reached 100% (1.0000) mean score across clean OCR medicine cases.

### Top Remaining Failures (34 total unsupported statements):
1. **`E2E-041` (Score: 0.0000, 10 unsupp):** Noisy OCR read "Glibenclarnide". Drug dict found "glyburide", but top retrieved drug chunk was "Allopurinol". The model hallucinated that Glibenclarnide is Allopurinol and attributed Allopurinol's indications/warnings to Glibenclarnide.
2. **`E2E-097` (Score: 0.2500, 3 unsupp):** Fictitious probe "Novaproxin 100mg". Retrieval returned "Meloxicam". The model hallucinated that Novaproxin's active ingredient is Meloxicam.
3. **`E2E-100` & `E2E-094` (Scores: 0.0000, 4 unsupp total):** Fictitious probe names ("Glycozempra", "Xanthroflurane"). When the model emitted "The requested medication information about Glycozempra could not be verified", the judge penalized mentioning the entity as an unsupported factual claim because Glycozempra does not appear in the context.
4. **`E2E-082` (Score: 0.3333, 2 unsupp):** Mismatch case where unrelated retrieved context was attributed to Strophanthus as an indication for induced abortion.
5. **`E2E-062` (Score: 0.5000, 3 unsupp):** Multi-ingredient survivalist kit where the model attributed an unverified indication (confusion/memory) to Aconitum Napellus.

---

## 4. Requirements & Blueprint for Cycle A7

Cycle A7 must build directly upon A6 and implement **Evidence Sufficiency, Unanswerable Handling, and Grounded Abstention**:

1. **Explicit Evidence Sufficiency State Engine:**
   - Detect when retrieved drug evidence does not match the scanned OCR medicine name or dictionary match (e.g., `Glibenclarnide` vs `Allopurinol`, `Novaproxin` vs `Meloxicam`).
   - Trigger `UNCERTAIN_MEDICINE_IDENTITY` or `INSUFFICIENT_EVIDENCE` state deterministically before calling the generator or within prompt routing.
2. **Entity-Neutral Abstention Templates:**
   - Completely prohibit naming fictitious/unretrieved query entities in negative claims.
   - For `UNANSWERABLE` or `INSUFFICIENT_EVIDENCE`, use clean, grounded abstention:
     *"The available clinical sources do not contain verified product information, indications, or dosing guidelines for this medication inquiry."*
   - Avoid mentioning specific drug names unless they are explicitly present in the retrieved evidence chunks.
3. **Strict Cross-Entity Attribution Guard:**
   - When evidence chunk belongs to Drug X (e.g. Allopurinol) and query refers to Drug Y (e.g. Glibenclarnide / Novaproxin), explicitly forbid asserting that Drug Y has the properties, indications, or active ingredients of Drug X.
