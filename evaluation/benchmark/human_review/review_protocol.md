# MediScanAI Human Adjudication Protocol

**Benchmark Suite:** MediScanAI Retrieval Benchmark  
**Phase:** Phase A.2 — Human Adjudication Protocol & Disagreement Procedures  
**Status:** Canonical Review Protocol  
**Authority:** Benchmark Operations & Medical Governance  

---

## 1. Purpose and Governance

This protocol establishes the standardized, objective procedure for conducting human relevance reviews of candidate evidence pooled across the dense baseline (FAISS) and knowledge graph (Neo4j) retrieval channels. It enforces strict separation between AI-proposed hypotheses and human ground truth, operationalizes domain-specific clinical adjudication rubrics, and formalizes multi-reviewer consensus and disagreement resolution.

---

## 2. Decision Framework and Outcome Classifications

Human reviewers evaluate each candidate row in [review_template.csv](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/human_review/review_template.csv) and select one of four mutually exclusive operational outcomes:

### 1. `agree` (Concurrence with AI Hypothesis)
- **Definition:** The reviewer independently examines the query, evidence, and official source, and concurs that the AI-proposed grade and rationale accurately reflect clinical/factual ground truth.
- **Action:**
  - `human_decision`: `"agree"`
  - `reviewed_grade`: Set identical to `proposed_grade` ($0, 1, 2, 3$).
  - `reviewer_rationale`: Provide independent confirmatory justification citing verified source elements.
  - `adjudication_status`: `"reviewed"`

### 2. `disagree` (Correction of AI Hypothesis)
- **Definition:** The reviewer determines that the AI-proposed grade overestimates, underestimates, or mischaracterizes relevance based on the source evidence.
- **Action:**
  - `human_decision`: `"disagree"`
  - `reviewed_grade`: Assign the correct integer grade ($0, 1, 2, 3$).
  - `reviewer_rationale`: Explicitly document why the proposed grade was erroneous and explain the clinical or pharmacological justification for the new grade.
  - `adjudication_status`: `"reviewed"`

### 3. `insufficient_evidence` (Corpus or Source Failure)
- **Definition:** The candidate document or cited external source does not contain adequate factual or clinical proof to substantiate the relationship asserted in the query, or the evidence is contradictory or inconclusive.
- **Action:**
  - `human_decision`: `"insufficient_evidence"`
  - `reviewed_grade`: Assign `0` (or `1` if peripheral mention exists, strictly documented).
  - `reviewer_rationale`: Document exactly which factual attributes or clinical proofs are missing from the record.
  - `adjudication_status`: `"reviewed"`

### 4. `escalate` (Referral to Consensus Panel)
- **Definition:** The clinical relationship is highly nuanced, controversial, outside the primary reviewer's subspecialty, or presents an ambiguous borderline between relevance grades (e.g. between Grade 2 and Grade 3).
- **Action:**
  - `human_decision`: `"escalate"`
  - `reviewed_grade`: Leave blank (`""` / `null`) pending consensus.
  - `reviewer_rationale`: Outline the competing clinical interpretations requiring panel adjudication.
  - `adjudication_status`: `"escalated"`

---

## 3. Domain-Specific Adjudication Rubrics

### 3.1 Drug Product and Active Ingredient Queries
- **Monotherapy vs. Combination Rule:**
  - A query asking for a single active ingredient (e.g. `MED-BENCH-015` "Lisinopril") must receive **Grade 3** on an unbranded single-ingredient product (`drug_923`).
  - A fixed-dose combination product containing that ingredient plus another agent (e.g. `drug_473` Lisinopril + Hydrochlorothiazide) must receive **Grade 2** (supporting evidence). It must **never** be graded 3 for a monotherapy query.
  - If the query specifically requests the combination product (e.g. `MED-BENCH-020`), the combination record (`drug_473`) receives **Grade 3**.
- **Brand-Generic Counterparts:**
  - When querying for generic active substances (e.g. `MED-BENCH-006` "Atorvastatin calcium"), the unbranded generic product (`drug_640`) receives **Grade 3**. The innovator brand counterpart (`drug_53548` Lipitor) receives **Grade 2**.
  - When querying for brand names (e.g. `MED-BENCH-001` "Lipitor"), the exact brand record (`drug_53548`) receives **Grade 3**.
- **Preservation of Raw Key Irregularities:**
  - In `drug_2305` (`Cinzan`), the source dictionary contains the non-ASCII key `adréactions`. The UK MHRA/eMC SmPC confirms drowsiness as the dominant adverse effect. Reviewers must accept this verified text without disqualifying the record due to raw indexing formatting.

### 3.2 Clinical Disease and Symptom Queries
- **Rule 4.5 Enforcement (Self-Referential Disease Titles):**
  - If a disease chunk repeats the disease name as the first element in its `symptoms` array (e.g. `disease_chunk_1` for Gestational Cholestasis), reviewers must disregard the self-referential title element and evaluate solely the remaining clinical symptoms (intense palmar/plantar pruritus in the third trimester).
- **Pathognomonic vs. Non-Specific Symptoms:**
  - *Grade 3:* Symptoms that are highly characteristic, defining, or pathognomonic (e.g. bilateral tight band-like headache for Tension Headache; unilateral throbbing headache with photophobia for Migraine).
  - *Grade 2:* Legitimate secondary etiologies or constitutional symptoms that form part of a differential diagnosis but are not individually diagnostic (e.g. fatigue/dizziness for Hypothyroidism `disease_chunk_160` or Type 2 Diabetes `disease_chunk_89`).
  - *Grade 1:* Weak, indirect, or peripheral associations (e.g. pleuritic chest pain in advanced uremic pericarditis for Chronic Kidney Failure `disease_chunk_2501` on a broad "Chest pain" query `MED-BENCH-038`).

### 3.3 Negative Controls and Unanswerable Queries (`MED-BENCH-041` to `045`)
- Reviewers must distinguish between:
  1. **Fictitious / Nonexistent Entities (`MED-BENCH-041`, `042`, `044`):** Exhaustive search across Drugs@FDA and WHO ICD-11 confirms zero approval or nosological records. Reviewers assign **Grade 0** with `evidence_id: "none"`.
  2. **Medically False / Hazardous Claims (`MED-BENCH-043`, `045`):** Curative statin claims for acute viral COVID-19 and chocolate syrup for acute appendicitis are clinically false and hazardous. Reviewers assign **Grade 0** with `evidence_id: "none"`.
- Under the benchmark negative-control contract, unanswerable queries must never be assigned positive relevance grades based on superficial keyword matches.

---

## 4. Multi-Reviewer Adjudication & Agreement Measurement

When multi-reviewer adjudication is conducted:

### 1. Independent Review Phase
- Reviewers conduct assessments independently in private workbooks. Reviewers are strictly forbidden from discussing pending queries or viewing peers' provisional scores prior to official consensus meetings.

### 2. Inter-Reviewer Agreement Metrics
- For two reviewers: Calculate **Cohen's Quadratic Weighted $\kappa$** ($\kappa_w$) across the 4-level ordinal scale ($0, 1, 2, 3$).
- For three or more reviewers: Calculate **Fleiss's $\kappa$**.
- Target benchmark standard: $\kappa_w \ge 0.75$ (substantial agreement) for clinical cases, and $\kappa_w \ge 0.90$ for nonclinical identity lookups.

### 3. Disagreement Identification & Flagging
- Any candidate item where $|\text{grade}_A - \text{grade}_B| \ge 1$, or where any reviewer designated `escalate` or `insufficient_evidence`, is automatically flagged for an Adjudication Consensus Conference.

### 4. Consensus Conference Procedure
1. **Case Presentation:** The Lead Adjudicator introduces the canonical query, retrieved evidence excerpt, and competing reviewer grades.
2. **Evidence Deliberation:** Reviewers examine authoritative primary sources (FDA DailyMed SPL, CDC/NIH guidelines, peer-reviewed clinical consensus).
3. **Consensus Rule:**
   - If consensus is reached, the agreed grade is entered with `adjudication_status="consensus_resolved"` and `adjudication_notes="Consensus agreed: <rationale>"`.
   - If consensus cannot be achieved after full deliberation, the **conservative lower grade** is recorded to avoid artificial inflation, and the differing clinical interpretations are explicitly documented in `adjudication_notes`.

### 5. Single-Reviewer Transparency Clause
If logistically only a single reviewer is available for a subset of cases, `benchmark_metadata.json` must explicitly state:
```json
"inter_reviewer_agreement": "N/A - Single Reviewer"
```
Synthesizing, fabricating, or imputing multi-reviewer scores is strictly prohibited.
