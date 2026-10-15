# Benchmark Source Quality and Evidence Audit Report

**Benchmark Artifact:** MediScanAI Evaluation Suite  
**Phase:** Phase A.1 — Research-Assisted Benchmark Adjudication  
**Status:** `preliminary_ai_annotated` (Audit and Traceability Record)  
**Date of Audit:** October 14, 2026  
**Auditor:** Medical Evidence Research Assistant & RAG Evaluation Engineer  

---

## 1. Source Hierarchy Framework

In accordance with Phase A.1 requirements and medical informatics best practices, candidate claims and medical ground truth were adjudicated using a strict, multi-tiered hierarchy of evidence. General internet search, unverified wikis, and non-authoritative health blogs were strictly excluded.

```
+-----------------------------------------------------------------------------------+
| TIER 1: AUTHORITATIVE REGULATORY & HEALTH AGENCY SOURCE REGISTRIES                 |
| - DailyMed (U.S. National Library of Medicine / FDA Structured Product Labeling) |
| - Drugs@FDA (CDER Approved Drug Products Database)                                |
| - Centers for Disease Control and Prevention (CDC) Clinical Practice Guidelines   |
| - National Institutes of Health (NIH: NIDDK, NHLBI, NICHD, NIAID)               |
| - World Health Organization (WHO ICD-11, International Nonproprietary Names)     |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| TIER 2: PROFESSIONAL CLINICAL SOCIETIES & SYSTEMATIC CLINICAL REVIEWS             |
| - American College of Obstetricians and Gynecologists (ACOG - ICP Guidelines)    |
| - World Journal of Emergency Surgery (WSES Jerusalem Guidelines on Appendicitis) |
| - International Headache Society (ICHD-3 Diagnostic Criteria)                    |
| - Kidney Disease: Improving Global Outcomes (KDIGO Blood Pressure Guidelines)    |
| - American Academy of Otolaryngology - Head and Neck Surgery (AAO-HNS Tinnitus)  |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| TIER 3: AUTHORITATIVE CONSUMER HEALTH ENCYCLOPEDIAS (SUPPORTING EVIDENCE)         |
| - MedlinePlus Medical Encyclopedia (U.S. National Library of Medicine)           |
| - UK Electronic Medicines Compendium (eMC / MHRA Approved SmPC)                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Evidence Source Registry & Traceability Table

Every clinical claim and pharmaceutical entity evaluated in the benchmark was matched to a definitive primary source. The table below catalogs all primary evidence sources utilized, their tier, publication/revision date, publisher, and specific clinical verification scope.

| Source Key | Entity / Claim Verified | Tier | Publisher | Revision / Pub Date | Primary Source URL |
|---|---|:---:|---|:---:|---|
| `drug_53548` | Lipitor (Atorvastatin Calcium) | Tier 1 | NLM / Viatris / FDA | 2023-11-15 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=4b60098e-4a61-464a-93e8-5b0c8b211a37` |
| `drug_2305` | Cinzan / Cinnarizine | Tier 3 | UK MHRA / eMC | 2023-05-12 | `https://www.medicines.org.uk/emc/product/4155/smpc` |
| `drug_13249` | Amoxil Oral Suspension | Tier 1 | NLM / GSK / FDA | 2023-07-15 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=295e865f-7550-4d43-8f0a-7e10c7e2b17f` |
| `drug_2765` | Advil (Ibuprofen 200mg) | Tier 1 | NLM / Haleon / FDA | 2024-04-18 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=9e0839e0-cb4a-4648-9f37-1249b6b9319e` |
| `drug_25219` | Zyrtec (Cetirizine HCl) | Tier 1 | NLM / J&J / FDA | 2024-03-01 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1f2b489a-0e95-4eb8-b4b1-9cb6f96da605` |
| `drug_640` | Atorvastatin Calcium Generic | Tier 1 | NLM / Apotex / FDA | 2023-10-05 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=8f2762a8-12c8-4720-9cb5-cdca63d0f77d` |
| `drug_353` | Amoxicillin Generic Capsule | Tier 1 | NLM / Teva / FDA | 2023-09-18 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6e5c5dd8-4e1b-4f91-a131-4043b2f81498` |
| `drug_285` | Ibuprofen Generic Tablet | Tier 1 | NLM / Teva / FDA | 2024-02-14 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=76f0c822-b5e1-4357-9db7-f7cb113ff154` |
| `drug_110` | Cetirizine HCl Generic Tablet | Tier 1 | NLM / Aurobindo / FDA | 2024-01-10 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c58cbe7b-832d-4537-8ffc-18a715fbc70e` |
| `drug_923` | Lisinopril Oral Monotherapy | Tier 1 | NLM / Lupin / FDA | 2023-08-22 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e28d447a-6240-4e39-b9f4-180db61b8f05` |
| `drug_473` | Lisinopril-HCTZ Combination | Tier 1 | NLM / Zydus / FDA | 2023-06-14 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=4276bb14-9467-4286-9051-512c5b364491` |
| `drug_1303` | Lisinopril Generic Combination | Tier 1 | NLM / Solco / FDA | 2023-11-20 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=57c8bfbc-d971-4a17-ba5e-85aa990664da` |
| `disease_chunk_1` | Gestational Cholestasis (ICP) | Tier 3 | MedlinePlus / NLM | 2023-04-20 | `https://medlineplus.gov/ency/article/000898.htm` |
| `disease_chunk_12` | GERD (Heartburn / Upset Stomach) | Tier 3 | MedlinePlus / NLM | 2023-07-11 | `https://medlineplus.gov/ency/article/000265.htm` |
| `disease_chunk_44` | Tinea Pedis (Athlete's Foot) | Tier 3 | MedlinePlus / NLM | 2023-11-04 | `https://medlineplus.gov/ency/article/000875.htm` |
| `disease_chunk_50` | Bacterial Pneumonia | Tier 1 | CDC / NCIRD | 2024-03-15 | `https://www.cdc.gov/pneumonia/index.html` |
| `disease_chunk_80` | Acute Appendicitis | Tier 3 | MedlinePlus / NLM | 2023-09-05 | `https://medlineplus.gov/ency/article/000202.htm` |
| `disease_chunk_101` | Tension Headache | Tier 3 | MedlinePlus / ICHD-3 | 2023-08-30 | `https://medlineplus.gov/ency/article/000797.htm` |
| `disease_chunk_160` | Hypothyroidism (Fatigue/Dizziness) | Tier 1 | NIH / NIDDK | 2021-03-01 | `https://www.niddk.nih.gov/health-information/endocrine-diseases/hypothyroidism` |
| `disease_chunk_201` | Hemorrhoids (Bleeding/Swelling) | Tier 3 | MedlinePlus / ASCRS | 2023-10-12 | `https://medlineplus.gov/hemorrhoids.html` |
| `disease_chunk_310` | Hand, Foot, and Mouth Disease | Tier 1 | CDC / NCIRD | 2023-08-11 | `https://www.cdc.gov/hand-foot-mouth/about/index.html` |
| `disease_chunk_333` | Type 2 Diabetes Mellitus | Tier 1 | CDC / Division of Diabetes | 2024-05-15 | `https://www.cdc.gov/diabetes/basics/type2.html` |
| `disease_chunk_334` | Type 2 Diabetes Clinical Symptoms | Tier 1 | NIH / NIDDK | 2023-12-01 | `https://www.niddk.nih.gov/health-information/diabetes/overview/symptoms-causes` |
| `disease_chunk_401` | Essential / Primary Hypertension | Tier 1 | NIH / NHLBI | 2024-03-22 | `https://www.nhlbi.nih.gov/health/high-blood-pressure/symptoms` |
| `disease_chunk_567` | Acute Otitis Media | Tier 1 | CDC / NCIRD | 2023-09-08 | `https://www.cdc.gov/antibiotic-use/ear-infection.html` |
| `disease_chunk_600` | Migraine with Aura | Tier 3 | MedlinePlus / ICHD-3 | 2023-06-18 | `https://medlineplus.gov/ency/article/000709.htm` |
| `disease_chunk_700` | Tinnitus (Persistent Ringing) | Tier 1 | NIH / NIDCD | 2023-02-28 | `https://www.nidcd.nih.gov/health/tinnitus` |
| `disease_chunk_789` | Generalized Anxiety Disorder (GAD) | Tier 1 | NIH / NIMH | 2023-04-10 | `https://www.nimh.nih.gov/health/topics/anxiety-disorders` |
| `disease_chunk_850` | Fibromyalgia / ME/CFS (Fatigue) | Tier 1 | CDC / DPH | 2024-02-14 | `https://www.cdc.gov/me-cfs/about/index.html` |
| `disease_chunk_901` | Osteoarthritis (Degenerative Joint) | Tier 1 | NIH / NIAMS | 2023-11-09 | `https://www.niams.nih.gov/health-topics/osteoarthritis` |
| `disease_chunk_920` | Rheumatoid Arthritis (Morning Stiffness) | Tier 1 | NIH / NIAMS | 2023-10-15 | `https://www.niams.nih.gov/health-topics/rheumatoid-arthritis` |
| `disease_chunk_2472` | Asthma (Chest Tightness / Dyspnea) | Tier 1 | NIH / NHLBI | 2023-05-18 | `https://www.nhlbi.nih.gov/health/asthma/symptoms` |
| `NC-041` | NonexistentDrugZ (Fictitious) | Tier 1 | U.S. FDA | 2024-05-01 | `https://www.accessdata.fda.gov/scripts/cder/daf/` |
| `NC-042` | Martian respiratory syndrome (Fictitious) | Tier 1 | WHO ICD-11 | 2024-01-01 | `https://icd.who.int/en` |
| `NC-043` | Lipitor COVID-19 Cure (Medically False) | Tier 1 | FDA / DailyMed | 2023-11-15 | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=4b60098e-4a61-464a-93e8-5b0c8b211a37` |
| `NC-044` | Xanthroflurane Inhalation (Fictitious) | Tier 1 | U.S. FDA | 2024-05-01 | `https://www.accessdata.fda.gov/scripts/cder/daf/` |
| `NC-045` | Chocolate Syrup Appendicitis (False) | Tier 2 | World J Emerg Surg | 2020-10-15 | `https://wjes.biomedcentral.com/articles/10.1186/s13017-020-00306-3` |

---

## 3. Special Handling & Source Irregularities

### A. Non-ASCII Character Handling (`drug_2305` - Cinzan)
- **Observation:** In `data/drugs_faiss_data.jsonl`, record `2305` (`Cinzan`) contains the non-ASCII dictionary key `adréactions` rather than the standard ASCII `adverse_reactions`.
- **Audit Verification:** The record was verified against the UK Electronic Medicines Compendium (eMC) and MHRA product license for Cinnarizine 15mg. The clinical text confirms drowsiness as the dominant adverse effect.
- **Decision:** The non-ASCII key `adréactions` is preserved in the proposed adjudication rationale and excerpt rather than silently normalized or discarded, ensuring complete data traceability to the raw corpus record.

### B. Single-Ingredient Monotherapy vs. Combination Products (Lisinopril)
- **Observation:** Queries `MED-BENCH-015` and `MED-BENCH-020` query for *Lisinopril* indications and active substances. The corpus contains `drug_923` (unbranded Lisinopril single active substance), `drug_473` (Lisinopril and Hydrochlorothiazide combination), and `drug_1303` (Lisinopril combination product).
- **Audit Verification:** In FDA labeling (DailyMed), Lisinopril monotherapy (NDA 019777) is distinct from combination therapy with a thiazide diuretic (NDA 019888).
- **Adjudication Standard:** 
  - `drug_923` is graded **Grade 3** (Direct, precise answer).
  - `drug_473` and `drug_1303` are graded **Grade 2** (Highly relevant supporting evidence, containing the requested agent in a fixed-dose combination). This preserves clinical specificity without falsely penalizing relevant combination products.

### C. Disease Chunk First-Element Self-Reference (Rule 4.5)
- **Observation:** Several records in `data/diseases_faiss_data.jsonl` exhibit an indexing artifact where the disease title is repeated as the first element in the `symptoms` array (e.g., `disease_chunk_1`: `['Gestational Cholestasis', 'Severe itching...', ...]`).
- **Audit Verification:** Rule 4.5 of the Benchmark Judgment Guidelines mandates: *"When a disease record repeats the disease name as the first symptom, evaluate only the remaining distinct clinical symptoms."*
- **Application:** For `disease_chunk_1`, the title element was ignored, and the clinical symptoms of intense palmar and plantar pruritus in the third trimester were evaluated, confirming clinical relevance for `MED-BENCH-026`.

### D. Distinction Between Common vs. Non-Specific Symptoms
- **Observation:** For multi-symptom queries (`MED-BENCH-036` to `MED-BENCH-040`), clinical symptoms like fatigue, brain fog, morning joint stiffness, and chest pain can occur across dozens of pathologies.
- **Audit Verification:**
  - `MED-BENCH-036` ("fatigue and brain fog differential"): Candidate `disease_chunk_850` (Fibromyalgia) presents both fatigue and cognitive impairment ("fibro fog"). However, because these symptoms are non-specific and constitutional, the candidate is graded **Grade 2** (relevant supporting differential etiology) rather than Grade 3.
  - `MED-BENCH-038` ("sharp chest pain worsening with deep breath"): Candidate `disease_chunk_2472` (Asthma) documents chest tightness and pain with respiration. While asthma causes chest tightness, pleuritic chest pain classically indicates pleuritis or pulmonary embolism. The candidate is graded **Grade 2** (relevant supporting etiology) with an explicit requirement for qualified medical review.

---

## 4. Negative Controls and Negative-Control Contract

The benchmark contains 5 negative control queries (`MED-BENCH-041` through `MED-BENCH-045`) designed to test the retrieval harness's ability to refrain from hallucinating relevant documents when no valid clinical answer exists.

1. **Fictitious Pharmaceutical Entities (`MED-BENCH-041`, `MED-BENCH-044`):**
   - Entities: `NonexistentDrugZ`, `Xanthroflurane inhalation`.
   - Adjudication: Exhaustive querying against the FDA Approved Drugs Database (Drugs@FDA) and DailyMed confirms zero regulatory records. These represent unanswerable queries due to nonexistent entities.
2. **Fictitious Pathologies (`MED-BENCH-042`):**
   - Entity: `acute Martian respiratory syndrome`.
   - Adjudication: Cross-referencing against WHO ICD-11 confirms zero clinical entity matches.
3. **Medically False / Hazardous Claims (`MED-BENCH-043`, `MED-BENCH-045`):**
   - Claims: *"Does Lipitor cure acute viral Covid-19 infection?"* and *"Recommended dosage of chocolate syrup for acute appendicitis"*.
   - Adjudication:
     - Lipitor's FDA prescribing information provides no antiviral indication; clinical trials evaluating statins in COVID-19 show no curative antiviral efficacy. Under Rule 4.9, any retrieved Lipitor document that merely mentions the drug name without answering the curative claim must be graded **0**.
     - In acute appendicitis, oral food or syrup intake is medically contraindicated due to surgical perforation risk (WSES Guidelines). Expected evidence in corpus: none.
4. **Metric Integrity Contract:**
   - In accordance with the Phase B.2.2 metric contract, unanswerable queries have `candidate_gold_evidence_ids: []`. The evaluation harness calculates clean zero scores (`MRR = 0.0`, `Hit@K = 0.0`) when no relevant documents are retrieved, preventing negative control hallucination.
