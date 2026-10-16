# Pre-Phase-3 Intent-Router Normalization & Edge-Case Audit (Check 3)

**Evaluation Phase:** MediScanAI Phase D.2.c-Final Audit  
**Audit Scope:** Intent-Router Normalization Logic, Token Stripping, Entity Preservation, and Edge-Case Robustness  
**Date:** October 17, 2026  
**Auditor:** Autonomous Systems Pre-Phase-3 Integrity & Safety Auditor  
**Audit Classification / Verdict:** `DEFECTS_IDENTIFIED_NONCRITICAL_ROUTING` (Bounded defects documented; no high-risk false acceptances of fictional entities).

---

## 1. Executive Summary & Objective

In Phase D.2.c, `IntentRouter` (`evaluation/retrieval/phase_d_2_c/intent_router.py`) was enhanced with:
1. Formulation and strength token stripping (`formulation_stop_words` and dosage regex) to resolve false rejections on valid medicines like `Metformin 500mg tablets` (`SAF-13`).
2. An Upstream Lexical Verification Gate to intercept fictional negative control drugs before hybrid retrieval.
3. Emergency red-flag triage escalation and OCR confidence gating.

The objective of this audit is to conduct read-only stress-testing of this normalization and routing logic across 27 deterministic edge cases divided into four critical clinical and linguistic categories:
- **Category A:** Valid medicine plus strength/formulation
- **Category B:** Combination versus monotherapy
- **Category C:** Fictional entities with realistic clinical modifiers
- **Category D:** Ambiguous, noisy OCR, and token collision cases

The full case-level execution results are archived in `evaluation/retrieval/phase_d_2_c_final_audit/intent_router_edge_cases.jsonl`.

---

## 2. Category-Specific Findings

### Category A: Valid Medicine Plus Strength / Formulation

| Case ID | Input Query | Normalized Substance | Observed Intent | Observed Action | Audit Verdict | Identified Behavior / Defect |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `EDGE-A01` | *Metformin 500mg tablets* | `metformin` | `brand_lookup` | `RETRIEVE_DRUG_CATALOG` | **PASS** | Correctly stripped `500mg` and `tablets`; matched catalog. |
| `EDGE-A02` | *Metformin 500 mg extended-release tablets* | `metformin 500 extended-release` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **ACCEPTABLE_DEGRADATION** | **Space-Separated Dosage Defect:** Regex `^\d+(?:mg\|mcg\|g\|ml)$` does not match space-separated `"500 mg"`. The numeral `"500"` and modifier remain, causing fallback to broad retrieval. |
| `EDGE-A03` | *Amoxicillin 250mg capsules* | `amoxicillin` | `brand_lookup` | `RETRIEVE_DRUG_CATALOG` | **PASS** | Correctly stripped; matched catalog antibiotic. |
| `EDGE-A04` | *Atorvastatin 20mg tab* | `atorvastatin` | `active_ingredient_lookup` | `RETRIEVE_DRUG_CATALOG` | **PASS** | Abbreviated token `tab` stripped correctly. |
| `EDGE-A05` | *Metformin oral solution* | `metformin` | `symptom_only_query` | `RETRIEVE_DISEASE_CHUNKS` | **DEFECT_ROUTING_MISMATCH** | **Oral Route Collision Defect:** Word `"oral"` in symptom phrases hijacks routing, suppressing drug catalog (see Section 3). |
| `EDGE-A06` | *Amoxicillin oral suspension* | `amoxicillin` | `symptom_only_query` | `RETRIEVE_DISEASE_CHUNKS` | **DEFECT_ROUTING_MISMATCH** | **Oral Route Collision Defect:** Pediatric suspension misrouted to disease diagnostic index. |
| `EDGE-A07` | *Metfor... 500mg* | `metfor...` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **ACCEPTABLE_DEGRADATION** | Partial OCR token falls back to dual-channel retrieval. |
| `EDGE-A08` | *L-i-p-i-t-o-r 20mg* | `l-i-p-i-t-o-r` | `unverified_fictional_negative`| `CLEAN_ABSTAIN` | **PASS** | Severe hyphenation fails lexical gate; safely abstains. |

### Category B: Combination versus Monotherapy

| Case ID | Input Query | Normalized Substance | Observed Intent | Observed Action | Audit Verdict | Identified Behavior / Defect |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `EDGE-B01` | *Metformin and Glipizide tablets* | `metformin and glipizide` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **PASS** | **No Collapse:** Does not collapse into single monotherapy; preserves both active ingredients for balanced retrieval. |
| `EDGE-B02` | *Metformin / Sitagliptin 500/50mg* | `metformin / sitagliptin 500/50mg` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **PASS** | Compound dose preserved; dispatches broad search across both drug records. |
| `EDGE-B03` | *Augmentin 625mg tablets* | `augmentin` | `brand_lookup` | `RETRIEVE_DRUG_CATALOG` | **PASS** | Fixed-dose combination brand recognized directly. |
| `EDGE-B04` | *Metformin 500mg* | `metformin` | `brand_lookup` | `RETRIEVE_DRUG_CATALOG` | **PASS** | Clean monotherapy resolution. |
| `EDGE-B05` | *Lisinopril with Hydrochlorothiazide 20/12.5mg* | `lisinopril with hydrochlorothiazide 20/12.5mg` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **PASS** | Preserves dual drug entities. |
| `EDGE-B06` | *Can I take Metformin and Glipizide together?* | `can i take metformin and glipizide together?` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **PASS** | Drug-drug interaction query handled in multi-retrieval channel. |

### Category C: Fictional Entities with Realistic Clinical Modifiers

| Case ID | Input Query | Primary Token | Observed Intent | Observed Action | Audit Verdict | Identified Behavior / Defect |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `EDGE-C01` | *Zephastin 50mg tablets* | `zephastin` | `unverified_fictional_negative` | `CLEAN_ABSTAIN` | **PASS** | Intercepted by hardcoded and lexical verification gate. |
| `EDGE-C02` | *Virokine dosage and usage* | `virokine` | `unverified_fictional_negative` | `CLEAN_ABSTAIN` | **PASS** | Intercepted by lexical verification gate. |
| `EDGE-C03` | *Pulmoflux for acute respiratory infection*| `pulmoflux` | `unverified_fictional_negative` | `CLEAN_ABSTAIN` | **PASS** | Clinical indication words do not bypass gate. |
| `EDGE-C04` | *Zorvaxil 20mg extended-release tablets* | `zorvaxil` | `unverified_fictional_negative` | `CLEAN_ABSTAIN` | **PASS** | **Novel Entity Resistance:** Unseen fictional drug cleanly intercepted by lexical gate. |
| `EDGE-C05` | *Cardioprex 10mg capsules* | `cardioprex` | `unverified_fictional_negative` | `CLEAN_ABSTAIN` | **PASS** | Novel fictional cardiovascular drug cleanly intercepted. |
| `EDGE-C06` | *Faketrol 100mg tablets* | `faketrol` | `unverified_fictional_negative` | `CLEAN_ABSTAIN` | **PASS** | Cleanly intercepted by lexical gate. |

### Category D: Ambiguous and Collision Cases

| Case ID | Input Query | Primary Token | Observed Intent | Observed Action | Audit Verdict | Identified Behavior / Defect |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `EDGE-D01` | *Metformix 500mg* | `metformix` | `unverified_fictional_negative` | `CLEAN_ABSTAIN` | **PASS** | Near-miss typo does not falsely match metformin; safely abstains. |
| `EDGE-D02` | *can metformin help or is it something else*| *N/A* | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **PASS** | Conversational ambiguous query routed to balanced search. |
| `EDGE-D03` | *Can I take Metformin and Lisinopril together?*| *N/A* | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **PASS** | Co-prescription query dispatched to dual channels. |
| `EDGE-D04` | *Lipitor 500mg extended-release tablets* | `lipitor` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **ACCEPTABLE_DEGRADATION** | Atypical strength/formulation falls back to balanced retrieval. |
| `EDGE-D05` | *Rx ...mg oral tablet* | *N/A* | `symptom_only_query` | `RETRIEVE_DISEASE_CHUNKS` | **DEFECT_ROUTING_MISMATCH** | Word `"oral"` misroutes corrupted OCR to disease index. |
| `EDGE-D06` | *Met 500mg tablets* | `met` | `general_medical_query` | `BALANCED_MULTI_RETRIEVAL` | **NEEDS_REVIEW** | **Substring Gate Leak:** `"met"` is a substring in `"metformin"`, so it bypasses lexical gate and falls through to balanced search instead of abstaining. |
| `EDGE-D07` | *Cough syrup with codeine* | *N/A* | `symptom_only_query` | `RETRIEVE_DISEASE_CHUNKS` | **DEFECT_ROUTING_MISMATCH** | Symptom word `"cough"` overrides medicine `"codeine"`. |

---

## 3. In-Depth Analysis of Discovered Defects

### Defect 1: The "Oral" Route Collision Defect (`DEFECT-ORAL-ROUTE-COLLISION`)
- **Location:** `evaluation/retrieval/phase_d_2_c/intent_router.py`, lines 156-159 & lines 328-345.
- **Mechanism:**
  During initialization (`_load_catalogs()`), symptoms from `diseases_faiss_data.jsonl` are loaded into `self.symptom_phrases`. The dataset contains clinical disease records featuring the standalone descriptor `"oral"` (e.g., from "oral ulcers", "oral manifestations").
  In `route()`:
  ```python
  is_symptom = (
      has_symptom_cue or
      has_symptom_word or
      any(s in q_lower for s in self.symptom_phrases if len(s) >= 4)
  )
  ```
  Since `"oral"` has length 4 ($\ge 4$), any query containing the administration route `"oral"` evaluates `is_symptom = True`.
  Because `rx_brands` only includes 8 brand names (`lipitor`, `cinzan`, `amoxil`, etc.), generic medicines containing the word `"oral"` (such as *Metformin oral solution* or *Amoxicillin oral suspension*) are classified as `symptom_only_query` and dispatched exclusively to `RETRIEVE_DISEASE_CHUNKS`, suppressing the drug catalog entirely!
- **Severity:** Medium (Non-critical). Does not cause clinical safety harm or hallucination leaks, but degrades retrieval recall for liquid/oral formulations of generic drugs.

### Defect 2: Spaced Dosage Token Normalization Failure (`DEFECT-SPACE-SEPARATED-STRENGTH`)
- **Location:** `evaluation/retrieval/phase_d_2_c/intent_router.py`, lines 380-386.
- **Mechanism:**
  The formulation stripping regex `r"^\d+(?:mg|mcg|g|ml)$"` requires the number and unit to be contiguous (e.g., `500mg`). When a space is present (`500 mg`), `q_tokens` contains separate elements `["500", "mg"]`. The token `"mg"` is stripped (matching `formulation_stop_words`), but `"500"` remains in `stripped_tokens`.
  Consequently, `cand_substance` becomes `"metformin 500"`, which fails exact catalog match and falls through to `BALANCED_MULTI_RETRIEVAL`.
- **Severity:** Low. The query is still retrieved via balanced multi-channel search; however, it bypasses the optimized direct catalog lookup.

### Defect 3: Substring False Match in Lexical Gate (`DEFECT-SUBSTRING-COLLISION`)
- **Location:** `evaluation/retrieval/phase_d_2_c/intent_router.py`, line 241.
- **Mechanism:**
  In the fictional entity gate:
  ```python
  token_found = any(primary_token in d_name for d_name in self.drug_names)
  ```
  This uses substring containment (`in`) rather than whole-word or token-level equality. A query like `Met 500mg tablets` has `primary_token = "met"`. Because `"met"` is a substring in `"metformin"`, `token_found` is `True`, allowing the query to pass the gate.
- **Severity:** Low. Fictional drugs that do not happen to be substrings of real drugs (e.g. `Zephastin`, `Virokine`, `Zorvaxil`) are 100% intercepted.

---

## 4. Entity Preservation Assessment

1. **Preservation of Clinical Formulation & Strength:**
   The router strips formulation tokens **only** for the internal catalog identity check (`cand_substance`). The **original, full user query** is preserved untouched and passed directly to the FAISS dense encoder, BM25 tokenizer, and cross-encoder reranker. Thus, no formulation, strength, or clinical modifiers are lost during downstream ranking.
2. **Combination Medicine Handling:**
   The router never collapses combination drugs (e.g., `Metformin / Sitagliptin` or `Lisinopril with Hydrochlorothiazide`) into a single active substance. Dual-active therapies cleanly dispatch to `BALANCED_MULTI_RETRIEVAL`, allowing both drug components to be surfaced.
3. **Fictional Entity Rejection:**
   Novel fictional entities (`Zorvaxil`, `Cardioprex`, `Faketrol`) are robustly rejected by the upstream lexical gate with 0 retrieved items. Clinical framing words (e.g. `"for acute respiratory infection"`, `"dosage and usage"`) do not bypass the catalog verification.

---

## 5. Audit Recommendations for Phase 3

To resolve the identified bounded defects during Phase 3 implementation:
1. **Exclude Common Route Words from Symptom Ingestion:** Remove standalone words such as `"oral"`, `"topical"`, `"otic"`, and `"ophthalmic"` from `self.symptom_phrases` during catalog loading.
2. **Support Space-Separated Strength Tokens:** Enhance the token normalizer to identify patterns matching `r"^\d+$"` followed immediately by a unit in `{"mg", "mcg", "g", "ml"}`.
3. **Exact Token Matching in Lexical Gate:** Replace `primary_token in d_name` with exact whole-word token matching using regular expressions or set membership.
