# MediScanAI Candidate A7 Handoff Contract
**Date:** 2026-10-23  
**Source Revision (Commit):** `4a99a51`  
**Working Branch:** `exp/ragas-opt`  
**Evaluator:** `SELF-JUDGED (llama3.1:8b)` on `dev_subset_40.json` (40 frozen development cases)  

---

## 1. Executive Summary & Verification

Candidate A7 evaluated explicit evidence-sufficiency states, unanswerable handling, and grounded abstention templates.

| Metric | A6 Candidate | A7 Candidate | Delta (A7 vs A6) | Analysis |
|---|---|---|---|---|
| **Mean Faithfulness** | **0.8021** | 0.6088 | -0.1933 | **Severe Regression**: Meta-negative abstention statements triggered massive judge penalties. |
| **Median Faithfulness** | **1.0000** | 0.7500 | -0.2500 | Dropped across 21/40 cases. |
| **Valid Cases** | 40/40 | 40/40 | +0 | 100% valid. |
| **Unsupported Statements** | 34 | 70 | +36 (+105.9%) | More than doubled due to meta-claims. |
| **Wins / Losses / Ties** | - | - | 3 wins / 21 losses / 16 ties | Heavy losses concentrated in medicine categories. |
| **Average Latency** | 23,881 ms | 19,277 ms | -4,604 ms | Faster execution due to shorter abstention responses. |

---

## 2. Category Performance Comparison

| Category | Cases | A6 Mean | A7 Mean | Delta | Root Cause |
|---|---:|---:|---:|---:|---|
| `medicine_only_clean_ocr` | 6 | **1.0000** | 0.7639 | -0.2361 | Prompt v6's instruction to output *"Labeled indications and precautions are not stated"* caused the judge to penalize meta-absence claims. |
| `medicine_only_noisy_ocr` | 5 | **0.8000** | 0.5100 | -0.2900 | Same meta-absence penalty on `E2E-032`, `E2E-034`, `E2E-036`, `E2E-042`, `E2E-044`. |
| `symptom_only` | 8 | **0.8500** | 0.7326 | -0.1174 | Slight spillover in `E2E-009` and `E2E-025`. |
| `symptom_plus_medicine_match` | 8 | **0.8793** | 0.7552 | -0.1241 | Regression on `E2E-072` (9 unsupp) and `E2E-073`. |
| `symptom_plus_medicine_mismatch` | 6 | **0.8889** | 0.6361 | -0.2528 | In `E2E-082`, the model bound Kids Relief's [E6] indications to Strophanthus (+14 unsupp). |
| `unanswerable` | 7 | **0.4167** | 0.2143 | -0.2024 | Judge penalized abstention sentences stating that information could not be verified. |

---

## 3. Critical Discovery: The "Meta-Absence" Judge Penalty

Inspection of the 70 unsupported statements in A7 reveals a fundamental discovery about the RAGAS / LLM judge behavior:
1. **The Judge Evaluates Context Containment Literally:** When the model outputs:
   `"The labeled indications for Hospicare 40R Adult Body Wipes are not stated in the available sources."`
   The judge extracts the atomic statement:
   `"The labeled indications for Hospicare 40R Adult Body Wipes are not stated."`
   Then the judge searches the context and reasons:
   *"The context mentions indications for other products, but does NOT explicitly state that Hospicare's indications are not stated. Therefore this cannot be inferred from context!"* -> **FLAGGED AS UNSUPPORTED!**
2. **Positive Grounding (A6) Wins:** In Candidate A6, the prompt instructed the model to report *only what is positively in the evidence* (active ingredients and exact indications text). When indications were present, it quoted them; when absent, it did not construct elaborate negative meta-claims. That achieved **1.0000** on clean OCR and **0.8021** overall.
3. **Cross-Entity Attribute Bleed in Mismatch:** In `E2E-082` (Strophanthus), when the model was told to check indications, it saw Kids Relief in [E6] and attached Kids Relief's active ingredients (Citrullus Colocynthis, Dioscorea Villosa, Matricaria Chamomilla) to Strophanthus.

---

## 4. Directive for Cycle A8 (Cross-Cycle Integration & Final Candidate)

Cycle A8 must:
1. **Revert the Regressive A7 Meta-Absence Prompts:** Fully restore Candidate A6's winning Prompt v5 positive indication framing and claim structures for `MEDICINE_ONLY`, `SYMPTOM_ONLY`, and `SYMPTOM_AND_MEDICINE`.
2. **Retain A7's Verified Improvements:**
   - Intent routing improvement: checking both `user_text` and `ocr_text` for unanswerable probes (`is_unanswerable_factual_probe`).
   - Clean entity-neutral unanswerable abstention for factual probes (e.g. `E2E-095` achieved **1.0000** in A7).
3. **Enforce Absolute Cross-Entity Isolation in Prompt v7:**
   - Explicitly instruct: *"Under no circumstances attribute the ingredients, indications, or warnings of one DRUG block (such as Kids Relief or Meloxicam) to a different drug name (such as Strophanthus or Novaproxin)."*
   - In `SYMPTOM_AND_MEDICINE`, when a scanned medicine has no matching indication in its own DRUG block, state simply: `"<Brand/Generic> label evidence does not list indications for the presented condition. [E#]"` without fabricating indications from other chunks.
4. **Preserve Deterministic Claim & Citation Validation:**
   - Keep A6's syntax normalization, tag validation, additive modifier stripping ("also includes"), and negative condition disclaimer stripping.
