# Recommended Changes for Narrative Reference Dataset

This document lists specific, proposed corrections for benchmark cases identified during the Phase C.1 audit of `evaluation/benchmark/narrative_references/reference_answers.jsonl`.

**In accordance with audit protocol, these changes are proposed recommendations only and have NOT been applied to the reference dataset.**

---

## 1. High-Severity Source URL Mismatches

### Cases: MED-BENCH-002, MED-BENCH-007, MED-BENCH-018, MED-BENCH-046, MED-BENCH-049 (Cinnarizine / Cinzan)
- **Current Problem:** 
  The reference answers cite `https://www.medicines.org.uk/emc/product/4155/smpc` with the title "Cinzan / cinnarizine product information". 
  Live HTTP inspection confirms that EMC Product 4155 is actually:
  **"Fosinopril sodium 10mg tablets - Summary of Product Characteristics (SmPC)"**
  Fosinopril sodium is an ACE inhibitor used for hypertension and heart failure. It has zero relationship to Cinnarizine (an antihistamine/calcium channel blocker used for vertigo and motion sickness) or the Indian brand Cinzan.
- **Evidence Supporting Finding:**
  Direct live HTTP 200 response from EMC shows title `Fosinopril sodium 10mg tablets - Summary of Product Characteristics (SmPC) - (emc) | 4155` and composition `Each tablet contains 10 mg fosinopril sodium`.
- **Recommended Change:**
  Replace the cited URL with a verified Cinnarizine product source. For example:
  - UK EMC SmPC for Cinnarizine 15mg tablets: `https://www.medicines.org.uk/emc/product/2427/smpc` (Stugeron 15mg Tablets / Cinnarizine).
  - Or an authoritative international reference / Indian pharmacopeial entry confirming Cinzan brand identity.
- **New Source Research Needed:** Yes (fetch and verify the replacement Cinnarizine SmPC URL).
- **Qualified Clinical Review Needed:** No (this is a straightforward factual correction of an erroneous URL/product ID).

---

### Cases: MED-BENCH-040, MED-BENCH-045 (Appendicitis / Abdominal Pain)
- **Current Problem:**
  The reference answers cite `https://medlineplus.gov/ency/article/000202.htm` with the title "Appendicitis".
  Live inspection reveals that article 000202 on MedlinePlus is:
  **"Myocardial contusion: MedlinePlus Medical Encyclopedia"** (a bruise of the heart muscle).
  It does not describe appendicitis or abdominal pain.
- **Evidence Supporting Finding:**
  Live HTTP 200 response from MedlinePlus confirms title `Myocardial contusion: MedlinePlus Medical Encyclopedia`. The text describes blunt trauma to the chest and cardiac complications.
- **Recommended Change:**
  Replace `000202.htm` with the correct MedlinePlus article for Appendicitis:
  `https://medlineplus.gov/ency/article/000259.htm` (Appendicitis: MedlinePlus Medical Encyclopedia).
  In `MED-BENCH-045`, the secondary source (WSES 2020 Jerusalem guidelines) is verified and supports the abstention from chocolate syrup, but `000202.htm` should still be corrected or removed.
- **New Source Research Needed:** Yes (verify `000259.htm` reachability and content).
- **Qualified Clinical Review Needed:** No (direct URL mapping fix).

---

## 2. Structural & Evaluative Cleanliness: Internal Corpus References

### Cases: MED-BENCH-013, MED-BENCH-015, MED-BENCH-018, MED-BENCH-037, MED-BENCH-039, MED-BENCH-046, MED-BENCH-048, MED-BENCH-049
- **Current Problem:**
  Several reference answers hardcode internal benchmark dataset IDs and corpus idiosyncrasies into the `key_facts` and `reference_answer` text. For example:
  - `MED-BENCH-015`: "drug_923 represents lisinopril monotherapy... drug_473 represents lisinopril plus hydrochlorothiazide"
  - `MED-BENCH-018`: "Candidate corpus record: drug_2305"
  - `MED-BENCH-049`: "Source key anomaly: `adréactions`"
  - `MED-BENCH-037`: "The sinusitis candidate does not document cough in the cited chunk"
- **Evidence Supporting Finding:**
  When evaluating generative models using Ragas (Faithfulness, Answer Relevance), the generated medical answer is expected to answer the user's clinical question (e.g. "What active ingredients are in Lisinopril and Hydrochlorothiazide combination?"). It cannot and should not predict internal synthetic IDs like `drug_923` or dataset typos like `adréactions`. Including these in `key_facts` penalizes valid clinical answers.
- **Recommended Change:**
  Separate clinical ground truth from corpus provenance. Move internal identifiers (`drug_923`, `drug_473`, `drug_2305`, `adréactions`) exclusively into `source_record_context` or `benchmark_intent_notes`. Keep `reference_answer` and `key_facts` focused strictly on the external medical facts.
- **New Source Research Needed:** No.
- **Qualified Clinical Review Needed:** No (benchmark engineering refinement).

---

## 3. Cases Requiring Qualified Clinical Review

### Case: MED-BENCH-038 (Chest Pain)
- **Current Problem:**
  The query "Chest pain" is inherently high-acuity and non-specific. The narrative reference provides triage advice ("Red-flag chest pain requires emergency assessment", distinguishing asthma chest tightness, kidney failure, and acute coronary syndrome).
- **Evidence Supporting Finding:**
  Providing concrete triage criteria and differential priorities in a benchmark reference answer requires alignment with recognized emergency medical protocols (e.g. AHA/ACC chest pain evaluation guidelines).
- **Recommended Change:**
  Have a qualified clinician review the reference answer text to ensure that the triage language, red flag warnings, and condition priorities accurately reflect standard emergency practice before freezing for production evaluation.
- **New Source Research Needed:** Optional (AHA/ACC emergency guidelines).
- **Qualified Clinical Review Needed:** **Yes**.

---

## 4. Source-to-Claim Mapping Corrections (Blanket Supports List)

### Cases: MED-BENCH-035, MED-BENCH-037, MED-BENCH-038, MED-BENCH-039
- **Current Problem:**
  In multi-source cases, the reference dataset copied the identical blanket list of all `key_facts` into every source's `supports` field. For example, in `MED-BENCH-038`, the NIDDK Kidney Failure page is listed as supporting "Asthma can cause chest tightness".
- **Evidence Supporting Finding:**
  The Kidney Failure source documents oliguria, fluid retention, and uremic symptoms, but does not discuss asthma.
- **Recommended Change:**
  Map each cited source specifically to the exact subclaim it supports:
  - NHS Chest Pain -> supports "Chest pain is nonspecific" and "Red-flag chest pain requires emergency assessment".
  - NHLBI Asthma -> supports "Asthma can cause chest tightness".
  - NIDDK Kidney Failure -> supports that systemic conditions can present with fluid overload/chest discomfort.
- **New Source Research Needed:** No.
- **Qualified Clinical Review Needed:** No.
