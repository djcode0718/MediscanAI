# Phase C.1.1 — Narrative Reference Answers Correction Directory

## Scope & Objective

This directory contains the proposed, evidence-backed corrections for the 50 narrative reference answers evaluated during Phase C.1.

The objective of Phase C.1.1 is to address the specific empirical findings of the Phase C.1 audit:
1. Replace mismatched source URLs with verified authoritative sources for Cinnarizine and Appendicitis.
2. Remove internal database primary keys (`drug_923`, `drug_473`, `drug_2305`, `drug_25219`, `drug_110`) and corpus metadata quirks (`adréactions`) from clinical narrative answers, preserving them in benchmark metadata.
3. Replace blanket source-to-claim mappings in multi-source cases with specific, traceable subclaim mappings.
4. Maintain answerability safeguards, abstentions for negative controls, and clinical caveat disclaimers.

**In accordance with project restrictions, this proposed dataset is isolated and has NOT replaced the active benchmark file `evaluation/benchmark/narrative_references/reference_answers.jsonl`. It awaits review and authorization before promotion.**

---

## Directory Contents

| File | Description |
|---|---|
| `reference_answers_baseline.jsonl` | Exact bit-for-bit baseline copy of the original 50-record reference dataset (SHA-256 `e1008637...`). |
| `reference_answers_proposed.jsonl` | Proposed corrected 50-record reference dataset with verified sources and cleaned narrative text (SHA-256 `14fb0654...`). |
| `correction_change_log.csv` | Granular log of all 27 material changes with case ID, field, old value, proposed value, rationale, and live verification status. |
| `source_claim_mapping.csv` | Explicit mapping (166 rows) connecting every cited source to the specific subclaims it directly supports. |
| `unresolved_findings.jsonl` | Documented limitations, including cases requiring licensed clinical review or jurisdiction-specific registry lookups. |
| `correction_integrity_report.json` | Machine-readable validation manifest verifying schema alignment, record counts, SHA-256 hashes, and non-modification of gold files. |

---

## Key Corrections Implemented

### 1. Source URL Replacements
- **Cinnarizine / Cinzan (`MED-BENCH-002`, `007`, `018`, `046`, `049`):**
  - *Audit Finding:* The original reference cited `https://www.medicines.org.uk/emc/product/4155/smpc`, which is Fosinopril sodium 10mg tablets (an ACE inhibitor), completely unrelated to Cinnarizine.
  - *Correction:* Replaced with the official NHS Cinnarizine medicine profile: `https://www.nhs.uk/medicines/cinnarizine/` (Title: "Cinnarizine: medicine for travel sickness and vertigo - NHS"). Live verified HTTP 200.
- **Appendicitis / Abdominal Pain (`MED-BENCH-040`, `045`):**
  - *Audit Finding:* The original reference cited `https://medlineplus.gov/ency/article/000202.htm`, which is Myocardial contusion (heart muscle bruise), not appendicitis.
  - *Correction:* Replaced with the verified MedlinePlus appendicitis article: `https://medlineplus.gov/ency/article/000256.htm` (Title: "Appendicitis: MedlinePlus Medical Encyclopedia"). Live verified HTTP 200.

### 2. Separation of Clinical Ground Truth from Corpus Metadata
In 8 cases (`MED-BENCH-013`, `015`, `018`, `037`, `039`, `046`, `048`, `049`), internal dataset IDs (`drug_923`, `drug_473`, `drug_2305`, `drug_25219`, `drug_110`) and corpus metadata typos (`adréactions`) were removed from `reference`, `reference_answer`, and `key_facts`.
- *Rationale:* Ragas evaluates generative output on Faithfulness and Answer Relevance against user questions. LLM outputs should not be penalized for failing to reproduce internal synthetic primary keys or OCR errors.
- *Preservation:* All internal candidate IDs remain fully preserved in `source_record_context`, `candidate_gold_evidence_ids`, and `benchmark_intent_notes` for retrieval and provenance tracking.

### 3. Granular Source-to-Claim Mapping
In multi-source cases (`MED-BENCH-015`, `035`, `037`, `038`, `039`, `045`, `048`), blanket mappings were replaced with specific subclaim attributions. Each source is linked only to the facts it directly documents.

---

## Limitations & Review Requirements

1. **Clinical Review Requirement (`MED-BENCH-038`):**
   - The query "Chest pain" includes emergency triage criteria and red-flag warnings. While responsible, this language has not been reviewed by a licensed physician and must be reviewed prior to freezing for clinical benchmarking.
2. **AI-Assisted Research Status:**
   - All proposed references are AI-assisted research and must **never** be labeled as human gold, clinician-reviewed, or official gold ground truth.
   - Provenance flags remain strictly: `human_reviewed: false`, `clinical_reviewed: false`, `official_human_gold: false`.
3. **Gold File Integrity:**
   - `evaluation/benchmark/gold_judgments.jsonl` remains strictly 0 bytes.
