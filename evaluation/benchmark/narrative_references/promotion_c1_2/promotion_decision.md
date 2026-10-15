# Phase C.1.2 Promotion Decision Report

**Promotion Decision:** **`APPROVED`**  
**Execution Timestamp:** 2026-10-15T12:41:14.937811+00:00  
**Dataset Promoted:** `evaluation/benchmark/narrative_references/correction_c1_1/reference_answers_proposed.jsonl`  
**Active Dataset Destination:** `evaluation/benchmark/narrative_references/reference_answers.jsonl`  

---

## 1. Decision Rationale

All five critical evaluation gates have been independently validated and passed without exception:

1. **Gate 1 (Dataset Integrity):**
   - The original baseline hash matches reported values (`e1008637468bafb58f6345279133108197a981384520d63a6a17630a5883f0bc`).
   - The proposed dataset contains exactly 50 valid JSONL records with contiguous unique case IDs (`MED-BENCH-001` through `MED-BENCH-050`).
   - Query text, category, expected evidence types, and candidate gold evidence IDs remain 100% aligned with `candidate_queries.jsonl`.
   - Character parity between `reference` and `reference_answer` is strictly 100%.
   - Provenance flags strictly retain `human_reviewed: false`, `clinical_reviewed: false`, and `official_human_gold: false`.

2. **Gate 2 (27 Material Changes):**
   - All 27 material changes in `correction_change_log.csv` were verified against actual old and new values.
   - All changes resolve empirical defects (eliminating false source URLs, separating corpus primary keys from narrative facts, and granularizing source attributions).

3. **Gate 3 (Critical Source Replacements):**
   - The 5 Cinnarizine cases (`MED-BENCH-002`, `007`, `018`, `046`, `049`) replaced the mismatched UK EMC Product 4155 (Fosinopril sodium) with the live-verified official NHS Cinnarizine profile (`https://www.nhs.uk/medicines/cinnarizine/`).
   - The 2 Appendicitis cases (`MED-BENCH-040`, `045`) replaced the mismatched MedlinePlus 000202 (Myocardial contusion) with the live-verified MedlinePlus Appendicitis article (`https://medlineplus.gov/ency/article/000256.htm`).

4. **Gate 4 (Source-to-Claim Mapping):**
   - All 166 granular mapping rows in `source_claim_mapping.csv` were validated against actual proposed records. No circular, blanket, or unverified mappings exist.

5. **Gate 5 (Answerability & Clinical Safeguards):**
   - Negative-control abstentions are strictly preserved across `MED-BENCH-041`, `042`, `043`, and `044`.
   - Ambiguous queries (`MED-BENCH-037`, `039`) preserve differential caveats without premature diagnosis.
   - High-acuity emergency triage query `MED-BENCH-038` retains an explicit clinical limitation and remains flagged for qualified medical review.

---

## 2. Integrity Hashes

| Dataset Stage | File Path | SHA-256 Hash |
|---|---|---|
| **Active Before Promotion** | `evaluation/benchmark/narrative_references/reference_answers.jsonl` | `e1008637468bafb58f6345279133108197a981384520d63a6a17630a5883f0bc` |
| **Pre-Promotion Backup** | `evaluation/benchmark/narrative_references/promotion_c1_2/reference_answers_pre_promotion.jsonl` | `e1008637468bafb58f6345279133108197a981384520d63a6a17630a5883f0bc` |
| **Proposed Corrected** | `evaluation/benchmark/narrative_references/correction_c1_1/reference_answers_proposed.jsonl` | `14fb0654f217ac887317d80fd036b9a5d19ff151932db53ba0e80fe08368dd23` |
| **Active After Promotion** | `evaluation/benchmark/narrative_references/reference_answers.jsonl` | `14fb0654f217ac887317d80fd036b9a5d19ff151932db53ba0e80fe08368dd23` |

---

## 3. Compliance & Safeguard Confirmations

- `evaluation/benchmark/gold_judgments.jsonl` remains strictly **0 bytes**.
- `entity_resolution/` was **never inspected, read, searched, referenced, or modified**.
- No production pipelines, retrieval code, FAISS indexes, or external packages were touched.
