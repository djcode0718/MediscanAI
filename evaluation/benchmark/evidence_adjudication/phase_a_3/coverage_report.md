# MediScanAI — Phase A.3 Source Coverage & Evidence Adjudication Report

## 1. Executive Summary

This report documents the independent, online evidence-based adjudication of all 62 benchmark records in the MediScanAI retrieval benchmark suite.

This assessment was conducted by an automated, research-assisted evaluation engine adhering strictly to the **MediScanAI Human Judgment Protocol** (`judgment_guidelines.md`), authoritative federal and international regulatory labeling (FDA/DailyMed, UK MHRA), official clinical references (NIH NHLBI/NIDDK/NICHD, CDC, MedlinePlus), and clinical classification registries (WHO ICD-11, WSES).

> [!IMPORTANT]
> **Adjudication Notice & Provenance Declaration**  
> All records in this dataset are classified under `adjudicator_type: "ai_assisted_external_evidence"` with `human_reviewed: false`.  
> This evaluation is an auditable, source-backed benchmark dataset created to enable objective automated research benchmarking without misrepresenting AI-derived evidence assessments as licensed human clinical sign-off. The official gold file (`evaluation/benchmark/gold_judgments.jsonl`) remains strictly zero bytes.

---

## 2. Reconciled Benchmark Counts & Status Breakdown

Every canonical query, candidate judgment, and negative control was independently audited. Zero records were omitted or fabricated.

| Dimension | Expected Count | Audited Count | Coverage Rate | Status |
| :--- | :---: | :---: | :---: | :--- |
| **Canonical Queries** | 50 | 50 | 100.0% | Complete parity |
| **Corpus Candidate Rows** | 57 | 57 | 100.0% | Traceable to source JSONL |
| **Negative Control Rows** | 5 | 5 | 100.0% | Independent negative verification |
| **Total Evaluated Judgments** | **62** | **62** | **100.0%** | All 62 rows represented |
| **Authoritative Source Entities** | 35 | 35 | 100.0% | Active Tier 1 authoritative sources |
| **Unresolved Records** | 0 | 0 | 0.0% | Zero unresolved |
| **Insufficient Evidence Records** | 0 | 0 | 0.0% | Zero unverified claims |

### Adjudication Outcome Breakdown

| Judgment Status | Count | Percentage | Operational Meaning |
| :--- | :---: | :---: | :--- |
| `evidence_verified` | 55 | 88.7% | Preliminary AI grade confirmed by authoritative source text |
| `grade_changed_after_research` | 2 | 3.2% | Grade downgraded following strict Rule 4.2 compliance |
| `negative_control_verified` | 5 | 8.1% | Independent registry verification confirmed unanswerability |
| `unresolved` | 0 | 0.0% | Ambiguities requiring clinician arbitration |
| `insufficient_source_evidence` | 0 | 0.0% | Records lacking authoritative documentation |
| **Total** | **62** | **100.0%** | **Full benchmark adjudication complete** |

---

## 3. Relevance Grade Distribution: Preliminary vs. Evidence-Based

Adjudication strictly enforced **Rule 4.2 (Free-Text Inference Prohibition)** and the 4-point ordinal rubric from `judgment_guidelines.md`. Two candidates previously graded as `2` (Relevant Supporting) were corrected to `1` (Weakly Related) because the actual disease chunk texts omitted key query symptoms that the preliminary AI model had speculatively inferred from clinical training priors.

| Relevance Grade | Preliminary AI Count | Evidence-Based Count | Net Delta | Benchmark Interpretation |
| :---: | :---: | :---: | :---: | :--- |
| **Grade 3 (Directly Relevant)** | 45 (72.6%) | 45 (72.6%) | 0 | Substantially answers the primary retrieval task with direct factual support |
| **Grade 2 (Relevant Supporting)** | 11 (17.7%) | 9 (14.5%) | -2 | Substantially relates or provides essential supporting context |
| **Grade 1 (Weakly Related)** | 1 (1.6%) | 3 (4.8%) | +2 | Contains partial/weak topical overlap; lacks core query co-symptoms |
| **Grade 0 (Not Relevant / Negative)** | 5 (8.1%) | 5 (8.1%) | 0 | Unanswerable negative controls; zero valid supporting evidence |
| **Total** | **62 (100.0%)** | **62 (100.0%)** | **0** | **100% accounted for** |

---

## 4. In-Depth Analysis of Grade Changes

Independent evidence research identified two critical discrepancies where preliminary AI annotations hallucinated clinical symptoms not present in the underlying disease chunks:

### Case 1: MED-BENCH-037 — `disease_chunk_501` (Acute Sinusitis)
- **Query:** `"Cough and fever"`
- **Query Category:** `ambiguous_queries`
- **Candidate Evidence:** `disease_chunk_501` (source record id: `500`)
- **Preliminary Grade:** `2` (Rationale: *"Supporting respiratory infection etiology: Acute sinusitis frequently presents with low-grade fever and post-nasal drip induced cough..."*)
- **Evidence-Based Grade:** `1` (`grade_changed: true`)
- **Independent Findings:**
  1. Inspection of the underlying corpus record `chunk_501` in `data/diseases_faiss_data.jsonl` revealed the following symptoms list:
     `['Acute sinusitis', 'Pain area - back of the eyes', 'Pain area - ear', 'Pain area - face', 'Pain area - forehead', 'Pain area - sinuses', 'distorted sense of smell', 'facial tenderness', 'fatigue', 'fever', 'headache', 'inflammation of ear', 'itchy nose', 'loss of smell', 'malaise', 'mouth breathing', 'nasal congestion', 'phlegm', 'pus', 'runny nose', 'sinus pressure', 'sleeping difficulty', 'sneezing', 'swelling', 'throat irritation']`
  2. The record explicitly documents `'fever'`, `'throat irritation'`, and `'nasal congestion'`, but **completely omits `'cough'`**.
  3. In medical practice, post-nasal drip from sinusitis may provoke a secondary cough, but **Rule 4.2 (Free-Text Inference Prohibition)** explicitly mandates: *"Never infer clinical facts, off-label indications, contraindications, or side effects that are not explicitly stated in the source record."*
  4. Per the benchmark rubric, a record containing only one nonspecific constitutional symptom (`fever`) without the primary co-symptom (`cough`) exhibits weak contextual overlap. It cannot be considered `Relevant Supporting` (Grade 2) for a compound query targeting both symptoms. It is properly graded **Grade 1 (Weakly Related)**.

### Case 2: MED-BENCH-039 — `disease_chunk_89` (Type 2 Diabetes)
- **Query:** `"Fatigue and dizziness"`
- **Query Category:** `ambiguous_queries`
- **Candidate Evidence:** `disease_chunk_89` (source record id: `88`)
- **Preliminary Grade:** `2` (Rationale: *"Relevant supporting metabolic etiology: Type 2 Diabetes presents with chronic fatigue and intermittent dizziness due to glycemic fluctuations..."*)
- **Evidence-Based Grade:** `1` (`grade_changed: true`)
- **Independent Findings:**
  1. Inspection of the underlying corpus record `chunk_89` in `data/diseases_faiss_data.jsonl` revealed the following symptoms list:
     `['Type 2 Diabetes', 'Fatigue', 'Increased hunger', 'Slow healing of wounds', 'fatigue', 'frequent urination', 'increased thirst']`
  2. The record explicitly documents `'Fatigue'`, but **completely omits `'dizziness'`**.
  3. In contrast, candidate `disease_chunk_160` (Hypothyroidism, evaluated for the same query) explicitly documents *both* `'Fatigue'` and `'dizziness'` (`['Hypothyroidism', 'Fatigue', ..., 'dizziness', ...]`), properly justifying Grade 2.
  4. The preliminary AI annotation speculatively inferred dizziness from glycemic swings. Because `dizziness` is absent from the text of `chunk_89`, Rule 4.2 prohibits treating it as verified. Presenting only fatigue (a universal, nonspecific symptom) without dizziness renders this chunk **Grade 1 (Weakly Related)**.

---

## 5. Category-by-Category Coverage Matrix

| Query Category | Case Count | Row Count | Evidence Verified | Grade Changed | Neg Control Verified | Primary Source Types |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `drug_brand_lookup` | 5 | 5 | 5 | 0 | 0 | DailyMed / UK MHRA SPL |
| `drug_generic_lookup` | 5 | 9 | 9 | 0 | 0 | DailyMed / FDA SPL |
| `active_ingredient_lookup` | 5 | 6 | 6 | 0 | 0 | DailyMed FDA Package Inserts |
| `brand_generic_ingredient_relationship` | 5 | 7 | 7 | 0 | 0 | DailyMed / FDA Drug Database |
| `single_symptom_disease_retrieval` | 5 | 5 | 5 | 0 | 0 | NIH / CDC / MedlinePlus |
| `multi_symptom_disease_retrieval` | 5 | 5 | 5 | 0 | 0 | NIH / MedlinePlus Guidelines |
| `synonym_wording_variants` | 5 | 5 | 5 | 0 | 0 | DailyMed / MedlinePlus |
| `ambiguous_queries` | 5 | 9 | 7 | **2** | 0 | MedlinePlus / CDC / NIH NHLBI |
| `graph_relevant` | 3 | 4 | 4 | 0 | 0 | DailyMed / MedlinePlus / MHRA |
| `graph_neutral` | 2 | 2 | 2 | 0 | 0 | UK MHRA / MedlinePlus |
| `insufficient_evidence_unanswerable` | 5 | 5 | 0 | 0 | **5** | FDA CDER / WHO / DailyMed / WSES |
| **Total** | **50** | **62** | **55** | **2** | **5** | **100% Verified** |

---

## 6. Source Registry Authority Hierarchy

The 35 unique sources registered in `source_registry.jsonl` represent exclusively Tier 1 public health and regulatory repositories:

| Hierarchy Tier | Source Count | Publishers | Associated Evidence Types | Verification Method |
| :--- | :---: | :--- | :--- | :--- |
| **Tier 1: DailyMed / FDA Product Labeling** | 13 | U.S. National Library of Medicine / FDA | Approved Rx & OTC Drug Products | Active SPL package insert XML/HTML verification |
| **Tier 1: MedlinePlus Reference** | 8 | U.S. National Library of Medicine (NLM) | Disease chunks, symptom profiles, OTC meds | Clinical topic review & terminology alignment |
| **Tier 1: CDC Clinical Guidelines** | 4 | Centers for Disease Control and Prevention | Infectious disease, rheumatology, metabolic | Public health diagnostic & symptom criteria |
| **Tier 1: NIH Institute Guidance** | 4 | NHLBI, NIDDK, NICHD | Asthma, anemia, endocrinology, PCOS | Clinical practice guidelines & consensus criteria |
| **Tier 1: FDA Regulatory Registry** | 2 | FDA CDER / Drugs@FDA | Negative controls (fictitious entities) | Exhaustive registry search (zero records confirmed) |
| **Tier 1: UK MHRA / eMC SmPC** | 1 | UK Medicines and Healthcare products Agency | Cinzan (Cinnarizine monotherapy) | European regulatory Summary of Product Characteristics |
| **Tier 1: WHO International Registry** | 1 | World Health Organization (WHO) | Negative control (extraterrestrial disease) | ICD-11 classification registry search |
| **Tier 1: International Surgical Guidelines**| 1 | World Journal of Emergency Surgery | Negative control (appendicitis protocol) | WSES 2020 consensus appendicitis guidelines |
| **Total Unique Source Entities** | **35** | — | — | **100% Tier 1 Authoritative** |

---

## 7. Negative Control Verification Summary

All five negative controls (`MED-BENCH-041` through `MED-BENCH-045`) were independently audited to ensure that their assignment to Grade 0 is medically and operationally grounded:

1. **MED-BENCH-041 (`NonexistentDrugZ 500mg dosage and administration`):**
   - Registry check: FDA Drugs@FDA, DailyMed, RxNorm, and Orange Book.
   - Outcome: Zero active or historical drug entities named "NonexistentDrugZ".
   - Grade: **0**. Valid negative control.
2. **MED-BENCH-042 (`Treatment protocol for acute Martian respiratory syndrome`):**
   - Registry check: WHO ICD-11, CDC, MeSH.
   - Outcome: Fictitious extraterrestrial clinical concept with zero medical taxonomy or treatment protocols.
   - Grade: **0**. Valid negative control.
3. **MED-BENCH-043 (`Does Lipitor cure acute viral Covid-19 infection?`):**
   - Registry check: Official FDA Prescribing Information for Lipitor (atorvastatin calcium, NDA 020702).
   - Outcome: Atorvastatin is an HMG-CoA reductase inhibitor indicated solely for hyperlipidemia and cardiovascular risk reduction. It has zero approved antiviral indications for SARS-CoV-2/COVID-19. Clinical trials demonstrated no curative or antiviral efficacy. The therapeutic assertion is false.
   - Grade: **0**. Valid negative control.
4. **MED-BENCH-044 (`FDA pediatric approval date for Xanthroflurane inhalation`):**
   - Registry check: FDA CDER database, PubChem, ChemSpider.
   - Outcome: Fabricated chemical nomenclature; no such anesthetic substance or pediatric approval exists.
   - Grade: **0**. Valid negative control.
5. **MED-BENCH-045 (`Recommended dosage of chocolate syrup for acute appendicitis`):**
   - Registry check: World Journal of Emergency Surgery (WSES 2020 appendicitis guidelines) / MedlinePlus.
   - Outcome: Acute appendicitis requires immediate surgical consultation, appendectomy, and intravenous antimicrobial therapy. Food confectionery has zero therapeutic dosage and poses severe aspiration and peritonitis hazards. Assertion is clinically absurd and dangerous.
   - Grade: **0**. Valid negative control.

---

## 8. Integrity & Safety Attestation

1. **Zero Gold File Mutation:** `evaluation/benchmark/gold_judgments.jsonl` was not touched, written to, or altered; it remains strictly zero bytes.
2. **No Production Modifications:** Production retrieval code, FAISS vector indexes, Neo4j graph instances, and source datasets were untouched.
3. **Restricted Directory Protection:** `entity_resolution/` was not inspected, accessed, traversed, or referenced.
4. **No Synthetic Human Claims:** All output records explicitly declare `adjudicator_type: "ai_assisted_external_evidence"` and `human_reviewed: false`.
