# Recommended Changes for Candidate Judgments

This document details proposed relevance grade corrections and benchmark refinements based on the Phase C.1.3 evidence audit of `evaluation/benchmark/candidate_judgments.jsonl`.

**In accordance with project restrictions, these changes are proposed recommendations only and have NOT been applied to the candidate judgments dataset.**

---

## 1. Summary of Proposed Grade Revisions

In the original `candidate_judgments.jsonl`, all 57 candidate judgments were uniformly assigned **Grade 3 (Directly Relevant)**.
Our independent audit identified **14 candidate judgments** where preliminary Grade 3 is medically or methodologically overstated:

| Case ID | Query | Evidence ID | Entity / Candidate | Prelim Grade | Recommended Grade | Reason / Benchmark Rule |
|---|---|---|---|:---:|:---:|---|
| **MED-BENCH-015** | Lisinopril | `drug_473` | Lisinopril and Hydrochlorothiazide | 3 | **2** | Combination product is a supporting partner (Grade 2), not primary monotherapy for a single-agent query. |
| **MED-BENCH-017** | What generic drug is in Advil? | `drug_44` | Ibuprofen (Generic) | 3 | **2** | Supporting generic record (Grade 2); brand record `drug_2765` directly answers the brand query. |
| **MED-BENCH-019** | Is Amoxil brand for amoxicillin? | `drug_353` | Amoxicillin (Generic) | 3 | **2** | Supporting generic record (Grade 2); brand record `drug_13249` directly answers the relationship. |
| **MED-BENCH-021** | oliguria | `disease_chunk_2501` | chronic kidney failure | 3 | **1** | Rule 4.2: Candidate chunk text omits oliguria; clinical inference of unstated symptoms is prohibited. |
| **MED-BENCH-029** | oliguria, shortness of breath, and hyperkalemia | `disease_chunk_2501` | chronic kidney failure | 3 | **1** | Rule 4.2: Candidate chunk text omits all three queried symptoms. |
| **MED-BENCH-032** | painful swollen veins in rectal area with bleeding | `disease_chunk_201` | Hemorrhoids | 3 | **2** | Partial match: chunk contains rectal pain and swelling, but omits bleeding. |
| **MED-BENCH-034** | kidney failure with reduced urine output | `disease_chunk_2501` | chronic kidney failure | 3 | **2** | Disease entity matches, but chunk omits the queried symptom (reduced urine output). |
| **MED-BENCH-035** | missed periods, trouble getting pregnant, and weight gain | `disease_chunk_3001` | PCOS | 3 | **2** | Partial match: chunk contains amenorrhea and infertility, but omits weight gain. |
| **MED-BENCH-037** | Cough and fever | `disease_chunk_248` | Pneumonia | 3 | **2** | Partial match: chunk contains cough, but omits fever from symptoms array. |
| **MED-BENCH-037** | Cough and fever | `disease_chunk_501` | Acute sinusitis | 3 | **1** | Rule 4.2: Chunk omits cough; weak contextual overlap for acute cough and fever presentation. |
| **MED-BENCH-038** | Chest pain | `disease_chunk_2472` | asthma | 3 | **2** | Clinical Review: Chunk documents chest tightness, not acute chest pain. Secondary supporting differential. |
| **MED-BENCH-038** | Chest pain | `disease_chunk_2501` | chronic kidney failure | 3 | **1** | Clinical Review: Renal fluid overload / pericarditis is a peripheral, weak differential for chest pain. |
| **MED-BENCH-039** | Fatigue and dizziness | `disease_chunk_89` | Type 2 Diabetes | 3 | **1** | Rule 4.2: Chunk omits dizziness; weak contextual overlap for fatigue + dizziness pair. |
| **MED-BENCH-039** | Fatigue and dizziness | `disease_chunk_160` | Hypothyroidism | 3 | **2** | Partial match: Chunk contains fatigue, but omits dizziness. |
| **MED-BENCH-047** | Diseases presenting both oliguria and hyperkalemia | `disease_chunk_2501` | chronic kidney failure | 3 | **0** | Relevance Mismatch: Chunk omits both oliguria and hyperkalemia; cannot answer graph intersection. |

---

## 2. Rule 4.2 Violations on Chronic Kidney Failure Chunk 2501

In `MED-BENCH-021`, `029`, and `047`, candidate `disease_chunk_2501` (`chronic kidney failure`) was assigned Grade 3 for queries explicitly demanding "oliguria" and "hyperkalemia".
However, the actual text in `disease_chunk_2501` is:
`Symptoms: [apyrexial, asthenia, catatonia, chest tightness, chill, diarrhea]`

Under **Rule 4.2 (Free-Text Inference Prohibition)**:
> *"Never infer clinical facts, off-label indications, contraindications, or side effects that are not explicitly stated in the source record... If record Y does not state condition X in indications_and_usage/symptoms, the record cannot be graded 3 for treating/presenting condition X."*

**Recommended Change:**
Downgrade `disease_chunk_2501` to Grade 1 for single-symptom `MED-BENCH-021` and multi-symptom `MED-BENCH-029`, and Grade 0 for graph intersection `MED-BENCH-047`. Alternatively, identify whether an alternative kidney failure chunk in `data/diseases_faiss_data.jsonl` explicitly documents oliguria.

---

## 3. High-Acuity Emergency Symptom Review: MED-BENCH-038 (Chest Pain)

Candidates assigned to "Chest pain":
- `disease_chunk_2472` (`asthma`): documents "chest tightness", but not acute chest pain.
- `disease_chunk_2501` (`chronic kidney failure`): documents "chest tightness".

Neither candidate represents a primary, high-acuity cause of acute chest pain (such as acute coronary syndrome, pulmonary embolism, or aortic dissection). Assigning Grade 3 to asthma and kidney failure for an unqualified query of "Chest pain" risks training/evaluating retrieval systems to surface secondary or non-urgent differentials ahead of life-threatening cardiac causes.

**Recommended Change:**
Submit `MED-BENCH-038` to licensed clinical consensus. Provisionally cap both candidates at Grade 2 and Grade 1 respectively.
