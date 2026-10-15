# MediScanAI Phase A.3.1 — Evidence Dataset Audit and Evaluation Readiness Report

## 1. Executive Summary & Audit Mandate

**Auditor Role:** Senior RAG Evaluation Dataset Auditor & Verification Engineer  
**Audit Objective:** Independently inspect, reconcile, and audit the actual Phase A.3 evidence-adjudication artifacts in `evaluation/benchmark/evidence_adjudication/phase_a_3/` to determine whether they are mathematically consistent, traceable to authoritative medical sources, and safe to consume in a separate AI-assisted evidence-verified retrieval evaluation track.

### Final Audit Determination
| Audit Area | Scope | Verification Status | Determination |
| :--- | :--- | :---: | :---: |
| **Audit 1: Actual Dataset Integrity** | All 62 judgments, 50 queries, 57 candidates, 5 negative controls | EXHAUSTIVE (100%) | **PASS** |
| **Audit 2: Source Registry Reconciliation** | 35 sources, publisher/domain counts, 62 judgment linkages | EXHAUSTIVE (100%) | **PASS** |
| **Audit 3: Evidence Support & Spot-Check** | 21 records (all changes, all negative controls, sample Grade 2/3) | TARGETED SAMPLE (33.9%) | **PASS** |
| **Audit 4: Evaluation Harness Compatibility**| Harness loader, metric definitions, graph ranking semantics | SYSTEM ARCHITECTURE | **PASS** |

**Final Recommendation:** **PASS — PROCEED WITH SEPARATE EVALUATION TRACK.**  
The Phase A.3 evidence-verified dataset is certified as safe, auditable, and ready for an isolated `AI-assisted evidence-verified retrieval evaluation`. The official ground-truth file (`evaluation/benchmark/gold_judgments.jsonl`) remains strictly **zero bytes**, production code is unchanged, and `entity_resolution/` was not accessed.

---

## 2. Audit 1: Actual Dataset Integrity

A line-by-line programmatic audit of `evaluation/benchmark/evidence_adjudication/phase_a_3/evidence_verified_judgments.jsonl` was executed against canonical benchmark files:

### 2.1 Count Reconciliation
- **Total Judgment Records:** Exactly **62 unique records** (matching the 57 candidate rows + 5 negative control rows from Phase A.1.2/A.1.3).
- **Canonical Benchmark Queries:** Exactly **50 queries** (`MED-BENCH-001` through `MED-BENCH-050`), all 50 represented.
- **Corpus Candidates:** Exactly **57 records** with stable composite IDs (`drug_<id>` or `disease_chunk_<id>`), matching canonical candidate judgments in `evaluation/benchmark/candidate_judgments.jsonl` with 100% ID correspondence.
- **Negative Control Records:** Exactly **5 records** (`MED-BENCH-041` to `MED-BENCH-045`), all assigned `evidence_id: "none"`, `source_record_id: null`, and `evidence_based_grade: 0`.

### 2.2 Provenance & Non-Fabrication Invariants
- **100% Human-Reviewed False:** All 62 records explicitly declare `"human_reviewed": false`.
- **100% Adjudicator Type:** All 62 records explicitly declare `"adjudicator_type": "ai_assisted_external_evidence"`. Zero records misrepresent AI evidence research as licensed clinician review.
- **Gold File State:** Inspection confirmed `evaluation/benchmark/gold_judgments.jsonl` is **0 bytes** (unmodified).

### 2.3 Grade Change Parity
Inspection of `evidence_verified_judgments.jsonl` and `grade_comparison.csv` revealed exact 1-to-1 parity:
- Exactly **2 records** have `grade_changed: true`:
  1. `MED-BENCH-037` (`disease_chunk_501`): Preliminary grade `2` $\rightarrow$ Evidence-based grade `1` (Delta: -1).
  2. `MED-BENCH-039` (`disease_chunk_89`): Preliminary grade `2` $\rightarrow$ Evidence-based grade `1` (Delta: -1).
- Both changes are explicitly documented in `grade_comparison.csv` with matching deltas and clinical justifications.

---

## 3. Audit 2: Source Registry Reconciliation & Discrepancy Resolution

### 3.1 Resolving the Reported 34 vs. 35 Discrepancy
The prompt noted: *"The Phase A.3 report lists 35 source entities, but the category counts in its summary appear to total 34."*

An exhaustive audit of `source_registry.jsonl` reconciled this exact discrepancy:
1. **Actual Machine-Readable Count:** `source_registry.jsonl` contains exactly **35 records** with 35 unique `source_id` keys, zero duplicates, and zero missing IDs.
2. **Root Cause of the Summary Table Discrepancy:**
   - In `source_registry.jsonl`, there are **14 sources with DailyMed URLs**.
   - 13 sources represent corpus drug products categorized under `source_hierarchy_tier: "Tier 1: DailyMed / FDA Product Labeling"`.
   - 1 source represents the negative control `NC-043` (Lipitor COVID-19 cure claim, URL: `https://dailymed.nlm.nih.gov/...`), which was categorized under `source_hierarchy_tier: "Tier 1: FDA Approved Drug Labeling"`.
   - In Section 6 of `coverage_report.md`, the author summarized tier counts as:
     - DailyMed / FDA Product Labeling: 13
     - MedlinePlus: 8
     - CDC Guidelines: 4
     - NIH Guidance: 4
     - FDA Regulatory Registry: 2
     - UK MHRA / eMC SmPC: 1
     - WHO International Registry: 1
     - International Surgical Guidelines: 1
     - Sum: $13 + 8 + 4 + 4 + 2 + 1 + 1 + 1 = \mathbf{34}$.
   - The summary table author counted only the 13 drug-product DailyMed entries and omitted the single FDA Approved Drug Labeling negative control entry (`NC-043`), creating an apparent shortfall of 1.
3. **Machine-Readable Truth:** The underlying file `source_registry.jsonl` is completely correct and contains all **35 unique sources**. Zero changes to the file were made.

### 3.2 Registry Linkage Reconciliation
- **Total Source References in Judgments:** 62 references across 62 judgments.
- **Unique Sources Referenced:** Exactly **35 unique sources**.
- **Dangling References (Referenced by judgment but missing in registry):** **0** (empty set).
- **Unreferenced Sources (In registry but never referenced by any judgment):** **0** (empty set).
- **Linkage Distribution:** Every registered source is referenced by between 1 and 5 benchmark judgments (e.g., `disease_chunk_2501` is referenced by 5 queries; `drug_2305` is referenced by 5 queries).

Complete machine-readable metrics are serialized in `source_registry_reconciliation.json`.

---

## 4. Audit 3: Evidence Support & Content Spot-Check

### 4.1 Audit Scope
A targeted sample of **21 records** (representing **33.9%** of the entire benchmark dataset) was selected for deep evidence content verification:
- **100% of Grade-Changed Records:** 2 records (`MED-BENCH-037` chunk 501; `MED-BENCH-039` chunk 89).
- **100% of Negative Controls:** 5 records (`MED-BENCH-041` through `MED-BENCH-045`).
- **Representative Grade 2 Records:** 5 records (`MED-BENCH-006` Lipitor; `MED-BENCH-008` Amoxil; `MED-BENCH-015` Lisinopril/HCTZ; `MED-BENCH-038` asthma chest pain; `MED-BENCH-039` hypothyroidism fatigue/dizziness).
- **Representative Grade 3 Records:** 9 records (`MED-BENCH-001`, `002`, `004`, `011`, `020`, `021`, `027`, `040`, `049`).

### 4.2 Content Verification Findings

#### Grade Changes (Strict Rule 4.2 Compliance):
1. **MED-BENCH-037 (`disease_chunk_501` for `"Cough and fever"`):**
   - *Corpus Check:* `chunk_501` contains `'fever'`, `'throat irritation'`, `'nasal congestion'`, but **zero occurrences of "cough"**.
   - *Source Check:* MedlinePlus article 000647 text confirms fever, facial pressure, and nasal obstruction.
   - *Rubric Finding:* Rule 4.2 prohibits assuming unstated post-nasal drip cough. Having only fever is weak partial overlap (**Grade 1**). Downgrade verified: **PASS**.
2. **MED-BENCH-039 (`disease_chunk_89` for `"Fatigue and dizziness"`):**
   - *Corpus Check:* `chunk_89` contains `'Fatigue'`, `'Increased hunger'`, `'Slow healing of wounds'`, but **zero occurrences of "dizziness"**.
   - *Source Check:* CDC diabetes symptoms guidance lists fatigue, polyuria, polydipsia, and weight loss.
   - *Rubric Finding:* Rule 4.2 prohibits inferring dizziness from glycemic shifts when absent from text. Having only fatigue is weak partial overlap (**Grade 1**). Downgrade verified: **PASS**.

#### Negative Controls (Independent Unanswerability Verification):
- **`MED-BENCH-041` & `044` (NonexistentDrugZ / Xanthroflurane):** FDA CDER Drugs@FDA and DailyMed searches confirm zero approved entities. Fictitious chemical concepts. Grade 0 verified: **PASS**.
- **`MED-BENCH-042` (Martian respiratory syndrome):** WHO ICD-11 confirms zero clinical entities or codes. Extraterrestrial concept. Grade 0 verified: **PASS**.
- **`MED-BENCH-043` (Lipitor cures COVID-19):** DailyMed SPL (setid `a60cc18b-...`) confirms atorvastatin is indicated exclusively for lipid disorders and cardiovascular risk reduction, with zero antiviral indications. Grade 0 verified: **PASS**.
- **`MED-BENCH-045` (Chocolate syrup for appendicitis):** World Journal of Emergency Surgery (WSES 2020 appendicitis guidelines) confirms emergent appendectomy and antimicrobial therapy are mandatory. Food confectionery has zero clinical dosage and is hazardous. Grade 0 verified: **PASS**.

#### Grade 2 Supporting Context:
- **`MED-BENCH-038` (`disease_chunk_2472` for `"Chest pain"`):** Corpus chunk 2472 explicitly documents `'sharp chest pain'` and `'pleuritic pain'`. In emergency differential diagnosis, asthma is a supporting/secondary etiology compared to acute cardiac/pleuritic emergencies. Grade 2 verified: **PASS**.
- **`MED-BENCH-039` (`disease_chunk_160` for `"Fatigue and dizziness"`):** Corpus chunk 160 explicitly documents *both* `'Fatigue'` and `'dizziness'`. Serves as valid supporting chronic endocrine etiology. Grade 2 verified: **PASS**.

The complete 21-row audit log is recorded in `evidence_spot_check.csv`.

---

## 5. Audit 4: Evaluation Harness Compatibility & Adapter Plan

### 5.1 Harness Inspection Findings
Inspection of `evaluation/retrieval/run_retrieval_evaluation.py` revealed:
1. **Hardcoded Gold Path & Status Filter:** `load_gold_judgments()` explicitly reads `benchmark_dir / "gold_judgments.jsonl"` and filters strictly for `rec.get("judgment_status") == "human_reviewed"`.
2. **Current State:** Because `gold_judgments.jsonl` is 0 bytes, running the harness currently evaluates all cases under `eligibility: not_evaluable_no_reviewed_gold_labels`.
3. **Graph Candidate Semantics:** Lines 431–432 already set `graph_mrr: None` and `pooled_mrr: None` ("Unordered candidate set; no synthetic graph MRR; prohibited concatenated ranking"). Graph evidence is properly evaluated as set-based marginal coverage (`graph_added_coverage`), preserving metric contract Section 4.
4. **Direct Execution Incompatibility:** If pointed at `evidence_verified_judgments.jsonl` without modification, the loader would find zero records with `judgment_status == "human_reviewed"` and fail to evaluate.

### 5.2 Smallest Safe Implementation Plan (Evaluation Adapter)
To execute an AI-assisted evidence-verified evaluation track without modifying gold files or confusing provenance:
1. **Parameterize Judgment Loading:** In `evaluation/retrieval/run_retrieval_evaluation.py`, add optional parameters:
   ```python
   def load_gold_judgments(
       benchmark_dir: Path,
       judgments_file: Optional[Path] = None,
       allowed_statuses: Optional[Set[str]] = None,
   ) -> Dict[str, Dict[str, Any]]:
   ```
2. **Dual-Track Support:**
   - **Default (Official Track):** Reads `gold_judgments.jsonl`, accepts only `{"human_reviewed"}`.
   - **Research Track (Evidence-Verified Track):** When `--evidence-judgments` CLI flag or `judgments_file` parameter is provided, reads `evidence_verified_judgments.jsonl`, accepting statuses `{"evidence_verified", "grade_changed_after_research", "negative_control_verified"}`.
3. **Metadata Isolation:** Write `evaluation_track: "ai_assisted_evidence_verified"` into `run_metadata.json` and prepend all summary reports with `"AI-Assisted Evidence-Verified Evaluation"`.
4. **Safety Guarantee:** Under no circumstances is `gold_judgments.jsonl` populated or touched.

---

## 6. Deliverables Index

All Phase A.3.1 artifacts have been created in `evaluation/benchmark/evidence_adjudication/phase_a_3_1_audit/`:

1. [audit_report.md](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/evidence_adjudication/phase_a_3_1_audit/audit_report.md) — This formal verification audit and recommendation report.
2. [source_registry_reconciliation.json](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/evidence_adjudication/phase_a_3_1_audit/source_registry_reconciliation.json) — Full machine-readable audit reconciling 35 sources, publisher/domain distributions, and the 34 vs 35 summary table discrepancy.
3. [evidence_spot_check.csv](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/evidence_adjudication/phase_a_3_1_audit/evidence_spot_check.csv) — 21-case content verification log covering 100% of grade changes and negative controls.
4. [evaluation_readiness.json](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/evidence_adjudication/phase_a_3_1_audit/evaluation_readiness.json) — Formal readiness decision, eligibility matrices, and adapter implementation plan.
5. [unresolved_findings.jsonl](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/evidence_adjudication/phase_a_3_1_audit/unresolved_findings.jsonl) — Clean ledger documenting zero unresolved blocking defects.

---

## 7. Final Decision & Restrictions

- **Audit 1 (Dataset Integrity):** **PASS**
- **Audit 2 (Source Registry Reconciliation):** **PASS**
- **Audit 3 (Evidence Support):** **PASS**
- **Audit 4 (Harness Compatibility):** **PASS**
- **Overall Recommendation:** **PROCEED WITH SEPARATE AI-ASSISTED RETRIEVAL EVALUATION.**

**Strict Invariants Maintained:**
- `evaluation/benchmark/gold_judgments.jsonl` remains **0 bytes**.
- Official human gold evaluation remains **blocked** pending clinician review under Phase A.2.
- Clinical answer generation evaluation, Ragas, Langfuse, and Phase C remain **blocked**.
- Production retrieval code and `entity_resolution/` were **not accessed or modified**.
