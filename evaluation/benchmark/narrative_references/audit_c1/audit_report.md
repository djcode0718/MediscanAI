# Phase C.1 — Independent Audit of Narrative Reference Answers

**Dataset Audited:** `evaluation/benchmark/narrative_references/reference_answers.jsonl`  
**Audit Output Location:** `evaluation/benchmark/narrative_references/audit_c1/`  
**Audit Date / Timestamp:** 2026-10-15 UTC  
**Adjudication Type:** AI-Assisted Independent Evidence Audit & Structural Validation  
**Clinical Review Status:** AI-Assisted Research Audit (NOT human gold, NOT licensed clinical adjudication)

---

## Executive Summary

An independent, read-only audit of the 50 narrative reference answers in `evaluation/benchmark/narrative_references/` was executed prior to running Ragas-based generation evaluations.

The audit programmatically validated all 50 records, live-verified all 34 unique external cited sources (68 case-to-source associations) via direct network requests, broke down all reference answers into 132 independently assessable factual claims, and evaluated research suitability.

### Key Metrics Summary
| Metric | Count | Percentage |
|---|---|---|
| **Total Cases Evaluated** | 50 | 100.0% |
| **Total Source Associations** | 68 | 100.0% |
| **Unique Source URLs** | 34 | 100.0% |
| **Total Factual Claims Assessed** | 132 | 100.0% |
| **Claims Supported** | 114 | 86.4% |
| **Claims Partially Supported** (Corpus-internal) | 9 | 6.8% |
| **Claims Unsupported** (Source Mismatches) | 9 | 6.8% |
| **Claims Contradicted** | 0 | 0.0% |
| **Claims Source Unavailable** | 0 | 0.0% |

### Research Suitability Classification
| Classification Category | Case Count | Case IDs |
|---|---|---|
| **`ready_for_research_review`** | 36 (72.0%) | MED-BENCH-001, 003–006, 008–017, 019–036, 048, 050 |
| **`needs_correction`** | 7 (14.0%) | MED-BENCH-002, 007, 018, 040, 045, 046, 049 |
| **`needs_clinical_review`** | 1 (2.0%) | MED-BENCH-038 (Chest pain emergency triage) |
| **`ambiguous_or_unanswerable`** | 6 (12.0%) | MED-BENCH-037, 039, 041, 042, 043, 044 |
| **`insufficient_evidence`** | 0 (0.0%) | — |

---

## 1. Audit Scope & Methodology

### 1.1 Scope
The audit examined:
1. `evaluation/benchmark/narrative_references/reference_answers.jsonl` (128,335 bytes, SHA-256 `e1008637...`)
2. `evaluation/benchmark/candidate_queries.jsonl` (27,935 bytes, SHA-256 `00174580...`)
3. `evaluation/benchmark/narrative_references/README.md`
4. `evaluation/benchmark/narrative_references/reference_answers_review.csv`
5. `evaluation/benchmark/narrative_references/integrity_check.json`
6. `evaluation/benchmark/gold_judgments.jsonl` (confirmed 0 bytes)

### 1.2 Separation of Independent Observations vs Automated Checks
- **Independent Live Observations:** Direct network retrieval (HTTP GET, redirects, TLS certificates, status codes, and DOM text inspection) was performed on all 34 unique cited URLs.
- **Automated Validation:** Structural parity, field presence, schema conformity, and cross-reference hashing were performed via Python scripts.
- **Model / Audit Judgments:** Claim breakdown, mapping of local corpus identifiers, and research suitability ratings were conducted according to the Phase C.1 audit guidelines.

---

## 2. Structural Validation Results

1. **Record Count & Case IDs:** Exactly 50 records exist, formatted contiguously from `MED-BENCH-001` through `MED-BENCH-050`. No duplicated or missing case IDs.
2. **Alignment with Benchmark:** 100% congruence with `candidate_queries.jsonl` in `case_id`, `query`, `query_category`, `expected_evidence_types`, and `candidate_gold_evidence_ids`.
3. **Reference Parity:** `reference` and `reference_answer` are 100% character-identical in all 50 records.
4. **Answerability Labels:** Valid schema values used across all cases:
   - `answerable`: 20 cases (40.0%)
   - `answerable_with_caveat`: 21 cases (42.0%)
   - `ambiguous`: 4 cases (8.0%)
   - `unanswerable`: 5 cases (10.0%)
5. **Verification Provenance:** All 50 records properly declare `human_reviewed: false`, `clinical_reviewed: false`, `official_human_gold: false`, and `adjudicator_type: "assistant_authored_source_backed_research"`.

---

## 3. External Source Availability & Verification Findings

External internet access was active and verified. All 34 unique URLs were resolved live (HTTP 200). However, **two critical URL content/identity mismatches** were identified where the cited URL does not match the product or disease in the reference answer.

### Summary of Live Source Probing
| Source Publisher / Domain | Unique URLs | Access Result | Content Concordance |
|---|---|---|---|
| **DailyMed (U.S. NLM / FDA)** | 9 | HTTP 200 | 100% concordant with drug identity and labeling |
| **MedlinePlus (NIH)** | 11 | HTTP 200 | 10 concordant; **1 critical mismatch** (`000202.htm`) |
| **electronic Medicines Compendium (UK EMC)** | 1 | HTTP 200 | **1 critical mismatch** (`product/4155/smpc`) |
| **NIDDK (NIH)** | 2 | HTTP 200 | 100% concordant |
| **NHLBI (NIH)** | 2 | HTTP 200 | 100% concordant |
| **NHS (UK National Health Service)** | 3 | HTTP 200 | 100% concordant |
| **CDC (Centers for Disease Control)** | 2 | HTTP 200 (HTTP/2) | 100% concordant |
| **Royal College of Obstetricians & Gynaecologists (RCOG)** | 1 | HTTP 200 | 100% concordant |
| **FDA (Drugs@FDA Portal)** | 1 | HTTP 200 | 100% concordant |
| **World Health Organization (ICD-11)** | 1 | HTTP 200 | 100% concordant |
| **Springer Nature / WSES (BioMed Central)** | 1 | HTTP 200 | 100% concordant |

---

## 4. Critical Findings & Factual Defects

### Finding 1: Mismatched Drug Source (EMC Product 4155)
- **Affected Cases:** `MED-BENCH-002`, `MED-BENCH-007`, `MED-BENCH-018`, `MED-BENCH-046`, `MED-BENCH-049` (5 cases).
- **The Issue:** The reference answers cite `https://www.medicines.org.uk/emc/product/4155/smpc` as "Cinzan / cinnarizine product information". Live inspection proves this URL is actually:
  **"Fosinopril sodium 10mg tablets - Summary of Product Characteristics (SmPC) - (emc) | 4155"**
  Fosinopril sodium is an ACE inhibitor used for hypertension and heart failure. It is completely unrelated to Cinnarizine (an antihistamine/calcium channel blocker used for vertigo and travel sickness) or the Indian brand Cinzan.
- **Impact:** 8 factual claims in these cases are formally **unsupported** by the cited URL.

### Finding 2: Mismatched Disease Article (MedlinePlus 000202)
- **Affected Cases:** `MED-BENCH-040`, `MED-BENCH-045` (2 cases).
- **The Issue:** The reference answers cite `https://medlineplus.gov/ency/article/000202.htm` with the title "Appendicitis". Live inspection proves this article is:
  **"Myocardial contusion: MedlinePlus Medical Encyclopedia"** (a bruise of the heart muscle from blunt chest trauma).
  MedlinePlus's actual article for Appendicitis is `000259.htm`.
- **Impact:** 1 factual claim in `MED-BENCH-040` is formally **unsupported** by the cited source. In `MED-BENCH-045`, the secondary source (WSES guidelines) supports the claim, but the primary cited URL remains factually mismatched.

### Finding 3: Internal Corpus Identifiers Hardcoded in Clinical Key Facts
- **Affected Cases:** `MED-BENCH-013`, `MED-BENCH-015`, `MED-BENCH-018`, `MED-BENCH-037`, `MED-BENCH-039`, `MED-BENCH-046`, `MED-BENCH-048`, `MED-BENCH-049` (8 cases, 9 claims).
- **The Issue:** Key facts and narrative answers include internal database record IDs (`drug_923`, `drug_473`, `drug_2305`, `drug_25219`, `drug_110`) and corpus metadata typos (`adréactions`).
- **Impact:** When evaluating LLM generation with Ragas, valid clinical answers cannot predict synthetic corpus primary keys. These claims are classified as **partially_supported** (supported by internal benchmark metadata, but not verifiable in published clinical literature).

### Finding 4: Blanket Copy-Paste of Key Facts in Multi-Source Cases
- **Affected Cases:** `MED-BENCH-035`, `MED-BENCH-037`, `MED-BENCH-038`, `MED-BENCH-039` (4 cases).
- **The Issue:** The dataset generator copied the entire array of `key_facts` into every supporting source's `supports` list. For instance, in `MED-BENCH-038`, the NIDDK Kidney Failure page is listed as supporting "Asthma can cause chest tightness".
- **Impact:** Defective source-to-claim mapping.

---

## 5. Detailed Breakdown of Claim Audit (132 Claims)

| Verification Status | Claim Count | Description / Rationale |
|---|---|---|
| **Supported** | 114 (86.4%) | Direct factual concordance between the claim text and live verified official drug label or medical encyclopedia. |
| **Partially Supported** | 9 (6.8%) | Claims describing local corpus IDs (`drug_923`, `drug_473`, `drug_2305`, `drug_25219`, `drug_110`), candidate chunk limitations, or dataset anomalies (`adréactions`). |
| **Unsupported** | 9 (6.8%) | Claims relying on mismatched URLs (8 claims citing EMC 4155 for Cinnarizine; 1 claim citing MedlinePlus 000202 for Appendicitis). |
| **Contradicted** | 0 (0.0%) | No claims were directly contradicted by authoritative medical facts. |
| **Source Unavailable** | 0 (0.0%) | All 34 unique URLs were accessible live. |
| **Not Independently Verified** | 0 (0.0%) | All claims were evaluated against fetched DOM content. |
| **Total** | **132 (100.0%)** | Full dataset coverage. |

---

## 6. Cases Needing Qualified Clinical Review

### `MED-BENCH-038` (Chest pain)
- **Reason:** The reference answer provides explicit emergency triage advice ("Red-flag chest pain requires emergency assessment", distinguishing asthma chest tightness, renal fluid overload, and acute coronary syndrome).
- **Recommendation:** While general triage warnings are responsible, the specific clinical wording and differential priorities should be reviewed by a qualified clinician before being frozen as benchmark ground truth.

---

## 7. Audit Artifacts Produced

The following 6 files have been generated in `evaluation/benchmark/narrative_references/audit_c1/`:

1. `audit_report.md`: This comprehensive independent audit report.
2. `source_verification.csv`: 68 rows (one per case-source association) recording original and final URLs, HTTP statuses, actual page titles, publishers, revision dates, evidence excerpts, and verification notes.
3. `claim_audit.jsonl`: 132 JSON lines auditing each factual claim with case ID, claim type, supporting sources, exact live excerpts, verification status, and audit rationale.
4. `case_audit.csv`: 50 rows detailing structural validity, source verification status, unsupported/contradicted claim counts, answerability, suitability, clinical review flags, and recommended actions.
5. `recommended_changes.md`: Case-by-case proposed corrections for the 7 mismatched cases, 8 corpus-internal cases, and 1 clinical triage case (strictly proposed, not applied).
6. `audit_integrity.json`: Machine-readable audit manifest with UTC timestamp, input file SHA-256 hashes, exact counts, live network verification flags, and integrity confirmations.

---

## 8. Final Integrity & Compliance Verification

1. **All 50 cases evaluated:** Yes (`MED-BENCH-001` through `MED-BENCH-050`).
2. **All 68 source occurrences accounted for:** Yes (68 rows in `source_verification.csv`).
3. **All 132 claims assessed:** Yes (132 lines in `claim_audit.jsonl`).
4. **All report counts verified:** Yes, exact parity across Markdown, CSV, and JSONL artifacts.
5. **Original reference dataset untouched:** Confirmed (`reference_answers.jsonl` SHA-256 `e1008637...` matches initial state).
6. **`gold_judgments.jsonl` untouched:** Confirmed (0 bytes, SHA-256 `e3b0c442...`).
7. **`entity_resolution/` untouched:** Confirmed strictly uninspected, unreferenced, and unmodified.
8. **Clinical claims caveat:** This audit is an AI-assisted research audit and does not claim to be licensed clinical or official human gold adjudication.
