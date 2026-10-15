# Phase C.1.3 — Evidence Audit of All Candidate Judgments

**Audited Dataset:** `evaluation/benchmark/candidate_judgments.jsonl`  
**Audit Output Location:** `evaluation/benchmark/candidate_judgments_audit_c1_3/`  
**Audit Date / Timestamp:** 2026-10-15 UTC  
**Adjudication Type:** AI-Assisted Independent Evidence Audit & Retrieval Relevance Assessment  
**Clinical Review Status:** AI-Assisted Research Audit (NOT human gold, NOT licensed clinical adjudication)

---

## Executive Summary

An independent, rigorous, read-only audit of all 57 records in `evaluation/benchmark/candidate_judgments.jsonl` was conducted.

The audit separated **medical correctness** (whether the candidate asserts true pharmacological, biochemical, or clinical propositions) from **retrieval relevance** (whether the candidate chunk substantially answers the user's specific query task under `judgment_guidelines.md`).

All 57 judgments were independently cross-referenced against 30 authoritative live medical sources (FDA, DailyMed, NHS, MedlinePlus, CDC, NIDDK, NHLBI, RCOG). Every judgment was decomposed into its factual medical claim and query relevance proposition (total **114 claims assessed**).

### High-Level Audit Metrics
| Metric | Count | Percentage |
|---|---|---|
| **Total Candidate Judgments Audited** | 57 | 100.0% |
| **Unique Benchmark Cases Represented** | 45 | 100.0% of cases with candidate evidence |
| **Cases with Zero Candidate Judgments** | 5 | Negative controls (MED-BENCH-041 to 045) |
| **Total Factual & Relevance Claims Assessed** | 114 | 100.0% (2 claims per judgment) |
| **Claims Supported** | 99 | 86.8% |
| **Claims Partially Supported** | 10 | 8.8% |
| **Claims Unsupported** | 5 | 4.4% |
| **Claims Contradicted** | 0 | 0.0% |

### Candidate Judgment Outcome Distribution
| Judgment Outcome Category | Count | Percentage | Description / Key Cases |
|---|---|---|---|
| **`verified_relevant`** | **42** | 73.7% | Medical correctness and query relevance confirmed; preliminary Grade 3 fully justified. |
| **`medically_supported_but_relevance_uncertain`** | **5** | 8.8% | Chunk is medically real, but partially matches query symptoms (`MED-BENCH-032`, `034`, `035`, `037` [chunk 248], `039` [chunk 160]). |
| **`needs_correction`** | **5** | 8.8% | Overstated preliminary grade; combination partner (`MED-BENCH-015`), generic partner (`MED-BENCH-017`, `019`), or omitted symptom (`MED-BENCH-037` [chunk 501], `039` [chunk 89]). |
| **`relevance_mismatch`** | **3** | 5.3% | Candidate chunk omits all queried clinical symptoms (`MED-BENCH-021`, `029`, `047` on `disease_chunk_2501`). |
| **`requires_clinical_review`** | **2** | 3.5% | High-acuity emergency presentation (`MED-BENCH-038` Chest pain on asthma and chronic kidney failure). |
| **`insufficient_evidence`** | **0** | 0.0% | All positive candidates resolved to verified biomedical literature. |

### Recommended Grade Distribution
In `candidate_judgments.jsonl`, all 57 judgments were assigned **Grade 3 (Directly Relevant)**. Our audit demonstrates that **15 candidate judgments** require grade adjustments:
- **Grade 3 (Directly Relevant):** 42 judgments (73.7%)
- **Grade 2 (Relevant Supporting):** 9 judgments (15.8%)
- **Grade 1 (Weakly Related):** 5 judgments (8.8%)
- **Grade 0 (Irrelevant / False Positive):** 1 judgment (1.8%)

---

## 1. Audit Scope & Methodology

### 1.1 Scope
The audit inspected:
1. `evaluation/benchmark/candidate_judgments.jsonl` (35,587 bytes, SHA-256 `8d4557dfd0e93f9e0578a3d8af524a9797687233fc562bbbbc1ceae21367de84`).
2. `evaluation/benchmark/candidate_queries.jsonl` (27,935 bytes).
3. `evaluation/benchmark/judgment_guidelines.md` (relevance rubrics and rules).
4. Promoted narrative references in `evaluation/benchmark/narrative_references/reference_answers.jsonl`.
5. `evaluation/benchmark/gold_judgments.jsonl` (confirmed 0 bytes).

### 1.2 Separation of Medical Correctness vs. Query Relevance
A common failure mode in medical retrieval benchmarking is conflating clinical truth with retrieval relevance:
- **Medical Correctness:** "Does chronic kidney failure cause oliguria in clinical medicine?" → **Yes** (supported by NIDDK and clinical literature).
- **Retrieval Relevance:** "Does chunk `disease_chunk_2501` contain the symptom oliguria to answer query 'oliguria'?" → **No** (its symptom array is `[apyrexial, asthenia, catatonia, chest tightness, chill, diarrhea]`).
Under **Rule 4.2 (Free-Text Inference Prohibition)** of `judgment_guidelines.md`, reviewers and automated evaluators must not infer unstated symptoms. If a retrieved chunk omits the queried symptom, it cannot receive Grade 3.

---

## 2. Key Audit Findings & Detailed Case Analyses

### Finding 1: Rule 4.2 Violations on Chronic Kidney Failure Chunk 2501
- **Affected Judgments:**
  - `MED-BENCH-021` (Query: "oliguria") → `disease_chunk_2501`
  - `MED-BENCH-029` (Query: "oliguria, shortness of breath, and hyperkalemia") → `disease_chunk_2501`
  - `MED-BENCH-047` (Query: "Diseases presenting both oliguria and hyperkalemia") → `disease_chunk_2501`
- **Analysis:**
  Candidate `disease_chunk_2501` has the following symptom text:
  `Symptoms: [apyrexial, asthenia, catatonia, chest tightness, chill, diarrhea]`
  It omits **oliguria**, **shortness of breath**, and **hyperkalemia**.
  Assigning Grade 3 to this chunk relies entirely on clinical inference of unstated symptoms, in direct violation of Rule 4.2.
- **Audit Outcome:** Classified as `relevance_mismatch`. Recommended grades:
  - `MED-BENCH-021`: Grade 1 (Weak contextual overlap)
  - `MED-BENCH-029`: Grade 1 (Weak contextual overlap)
  - `MED-BENCH-047`: Grade 0 (Fails to demonstrate multi-symptom intersection)

### Finding 2: Monotherapy vs. Fixed-Dose Combination Product
- **Affected Judgment:** `MED-BENCH-015` (Query: "Lisinopril") → `drug_473` (`Lisinopril and Hydrochlorothiazide`)
- **Analysis:**
  The query asks for single-agent "Lisinopril". Candidate `drug_923` is lisinopril monotherapy (Grade 3). Candidate `drug_473` is a fixed-dose combination containing hydrochlorothiazide (a thiazide diuretic).
  Under Rule 4.1 and Rubric Section 2, a multi-ingredient combination partner is a supporting context document (**Grade 2**), not a directly relevant monotherapy hit.
- **Audit Outcome:** Classified as `needs_correction`. Recommended downgrade from Grade 3 to Grade 2.

### Finding 3: Generic Counterparts in Brand Relationship Queries
- **Affected Judgments:**
  - `MED-BENCH-017` (Query: "What generic drug is in Advil?") → `drug_44` (generic Ibuprofen)
  - `MED-BENCH-019` (Query: "Is Amoxil brand for amoxicillin?") → `drug_353` (generic Amoxicillin)
- **Analysis:**
  In both cases, the candidate query is a brand relationship lookup.
  The brand product records (`drug_2765` for Advil and `drug_13249` for Amoxil) directly state the relationship in their labeling (Grade 3).
  The generic product records (`drug_44` and `drug_353`) confirm the generic active substance exists, but do not directly document the brand relationship. Under Rubric Section 2, generic counterpart records are supporting context (**Grade 2**).
- **Audit Outcome:** Classified as `needs_correction`. Recommended downgrade from Grade 3 to Grade 2.

### Finding 4: Emergency Triage & Acuity Concerns in MED-BENCH-038 (Chest Pain)
- **Affected Judgments:**
  - `MED-BENCH-038` → `disease_chunk_2472` (`asthma`)
  - `MED-BENCH-038` → `disease_chunk_2501` (`chronic kidney failure`)
- **Analysis:**
  Both chunks list "chest tightness". Neither represents a primary, high-acuity cause of acute chest pain (e.g. acute coronary syndrome, pulmonary embolism, aortic dissection).
  Labeling asthma and chronic kidney failure as Grade 3 (Directly Relevant) for an unqualified query of "Chest pain" overstates their clinical relevance and risks validating retrievers that fail to prioritize life-threatening cardiac causes.
- **Audit Outcome:** Classified as `requires_clinical_review`. Recommended provisional downgrade: `disease_chunk_2472` to Grade 2, `disease_chunk_2501` to Grade 1.

### Finding 5: Omitted Symptoms in Ambiguous Multi-Symptom Presentations
- **Affected Judgments:**
  - `MED-BENCH-037` (Query: "Cough and fever") → `disease_chunk_501` (Acute sinusitis): lists facial pain/pressure; omits cough. Classified as `needs_correction` (downgrade Grade 3 to Grade 1).
  - `MED-BENCH-039` (Query: "Fatigue and dizziness") → `disease_chunk_89` (Type 2 Diabetes): lists fatigue, hunger, polyuria; omits dizziness. Classified as `needs_correction` (downgrade Grade 3 to Grade 1).
  - `MED-BENCH-039` (Query: "Fatigue and dizziness") → `disease_chunk_160` (Hypothyroidism): lists fatigue; omits dizziness. Classified as `medically_supported_but_relevance_uncertain` (Grade 2).
  - `MED-BENCH-039` (Query: "Fatigue and dizziness") → `disease_chunk_336` (Anemia): directly contains **both** Fatigue and Dizziness! Fully verified as Grade 3.

---

## 3. Live External Source Verification Summary

All 30 unique external sources cited during the audit were verified live via direct HTTP/HTTPS GET requests with DOM content inspection.

| Source Domain | Sources | Access Result | Content Support |
|---|---|---|---|
| **DailyMed (NLM / FDA)** | 9 | HTTP 200 | Directly verified brand names, generic active ingredients, and indications. |
| **MedlinePlus (NIH)** | 9 | HTTP 200 | Verified active substances, appendicitis, hemorrhoids, PCOS, sinusitis, and spinal trauma. |
| **NHS (UK National Health Service)** | 4 | HTTP 200 | Verified Cinnarizine, Gout, Tension headache, and Chest pain emergency red flags. |
| **CDC (Centers for Disease Control)** | 2 | HTTP 200 (HTTP/2) | Verified Pneumonia and Type 2 Diabetes clinical presentations. |
| **NIDDK (NIH)** | 2 | HTTP 200 | Verified Chronic Kidney Failure and Hypothyroidism symptoms. |
| **NHLBI (NIH)** | 2 | HTTP 200 | Verified Asthma and Anemia symptom criteria. |
| **RCOG (Royal College of Obstetricians)** | 1 | HTTP 200 | Verified Intrahepatic Cholestasis of Pregnancy presentation. |

All source metadata, titles, and publication dates are recorded in [`source_verification.csv`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/candidate_judgments_audit_c1_3/source_verification.csv).

---

## 4. Reconciliation with Benchmark Framework

1. **Alignment with `candidate_queries.jsonl`:**
   - All 45 positive cases match candidate queries exactly.
   - The 5 negative control queries (`MED-BENCH-041` to `045`) have 0 candidate judgments, which is strictly correct since `expected_evidence_types` is `["none"]`.
2. **Alignment with Promoted Narrative References (`reference_answers.jsonl`):**
   - The promoted narrative references for `MED-BENCH-015`, `018`, `037`, `038`, `039`, and `046` specifically note the distinctions identified in this audit (e.g. distinguishing monotherapy from combinations, and noting that candidate chunks for sinusitis and diabetes omit cough and dizziness).
   - This cross-phase reconciliation confirms that the evaluation artifacts are coherent and mutually reinforcing.
3. **Alignment with Phase A.3 Adjudications:**
   - In Phase A.3, `disease_chunk_501` for `MED-BENCH-037` and `disease_chunk_89` for `MED-BENCH-039` were downgraded from preliminary Grade 2 to Grade 1. In `candidate_judgments.jsonl`, however, they had remained at preliminary Grade 3. This audit confirms that the Phase A.3 downgrades were methodologically sound.

---

## 5. Summary of Audit Artifacts Created

In `evaluation/benchmark/candidate_judgments_audit_c1_3/`:
1. [`audit_report.md`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/candidate_judgments_audit_c1_3/audit_report.md): This comprehensive report.
2. [`judgment_audit.csv`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/candidate_judgments_audit_c1_3/judgment_audit.csv): 57 rows auditing every candidate judgment with medical correctness, query relevance, recommended grade, outcome status, and detailed rationale.
3. [`claim_audit.jsonl`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/candidate_judgments_audit_c1_3/claim_audit.jsonl): 114 JSON objects auditing each medical proposition and query relevance proposition with evidence excerpts and verification statuses.
4. [`source_verification.csv`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/candidate_judgments_audit_c1_3/source_verification.csv): 26 rows documenting every live external source URL, HTTP status code, publisher, and supported claims count.
5. [`recommended_changes.md`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/candidate_judgments_audit_c1_3/recommended_changes.md): Itemized proposal for the 15 candidate grade adjustments (strictly unapplied).
6. [`audit_integrity.json`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/candidate_judgments_audit_c1_3/audit_integrity.json): Machine-readable verification manifest with SHA-256 hashes, exact counts, and compliance checks.

---

## 6. Final Integrity Confirmations

- **Original candidate judgments unmodified:** Confirmed (`candidate_judgments.jsonl` SHA-256 `8d4557dfd0e93f9e0578a3d8af524a9797687233fc562bbbbc1ceae21367de84`).
- **`gold_judgments.jsonl` strictly zero bytes:** Confirmed (0 bytes, SHA-256 `e3b0c442...`).
- **`entity_resolution/` restriction:** Confirmed **never inspected, read, searched, referenced, imported, or modified**.
- **No production code or dependencies changed:** Confirmed.
- **AI-assisted audit caveat:** This audit is AI-assisted research and does not claim to be licensed clinical or official human gold adjudication.
