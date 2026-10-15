# Phase C.1.4 — Candidate Judgment Grade Corrections

## Scope & Objective

This directory contains the artifacts for Phase C.1.4, applying evidence-based relevance grade corrections to `evaluation/benchmark/candidate_judgments.jsonl` in accordance with the Phase C.1.3 audit findings.

In the original candidate judgments dataset, all 57 records were uniformly assigned **Grade 3 (Directly Relevant)**. The Phase C.1.3 audit established that 15 records had overstated grades due to:
1. **Rule 4.2 Violations:** Free-text clinical inference of unstated symptoms on `disease_chunk_2501` (`MED-BENCH-021`, `029`, `047`).
2. **Combination vs. Monotherapy:** Multi-ingredient combination product `drug_473` evaluated against single-agent query `MED-BENCH-015`.
3. **Generic vs. Brand Relationships:** Generic counterparts `drug_44` and `drug_353` evaluated against brand relationship queries `MED-BENCH-017` and `019`.
4. **Partial Symptom Matches:** Disease chunks omitting one of multiple queried symptoms (`MED-BENCH-032`, `034`, `035`, `037`, `039`).
5. **Emergency Triage Acuity:** High-acuity query `MED-BENCH-038` ("Chest pain") evaluated against secondary causes of chest tightness (`disease_chunk_2472` and `disease_chunk_2501`).

---

## Directory Contents

| File | Description |
|---|---|
| `candidate_judgments_baseline.jsonl` | Exact byte-for-byte backup of original 57 candidate judgments (SHA-256 `8d4557dfd0e93f9e0578a3d8af524a9797687233fc562bbbbc1ceae21367de84`). |
| `candidate_judgments_corrected.jsonl` | Corrected 57-record dataset with updated relevance grades (SHA-256 `504ec88f4e5c72288f7ed4dcc8b36adc8a4c96dca7cec7edcc8b9574481b835a`). |
| `grade_change_log.csv` | Granular audit log of all 15 applied grade changes with case ID, evidence ID, old grade, new grade, and clinical rationale. |
| `unresolved_judgment_limitations.jsonl` | Documentation of unresolved limitations, including provisional grades for `MED-BENCH-038` and brand jurisdiction for `MED-BENCH-002`. |
| `correction_integrity.json` | Machine-readable validation report detailing hashes, distributions, and compliance assertions. |

---

## Grade Distribution Summary

| Grade | Label | Baseline Count | Corrected Count | Net Change |
|:---:|:---|:---:|:---:|:---:|
| **3** | Directly Relevant | 57 (100.0%) | 42 (73.7%) | -15 |
| **2** | Relevant Supporting | 0 (0.0%) | 9 (15.8%) | +9 |
| **1** | Weakly Related | 0 (0.0%) | 5 (8.8%) | +5 |
| **0** | Not Relevant / False Positive | 0 (0.0%) | 1 (1.8%) | +1 |
| **Total** | | **57** (100.0%) | **57** (100.0%) | **0** |

---

## Compliance Confirmations

- `evaluation/benchmark/gold_judgments.jsonl` remains strictly **0 bytes**.
- `entity_resolution/` was **never inspected, read, searched, referenced, imported, or modified**.
- No candidate queries, narrative references, retrieval code, FAISS indexes, or external dependencies were modified.
