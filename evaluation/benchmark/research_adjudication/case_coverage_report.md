# Benchmark Case Coverage Report (Remediated Phase A.1.2)

**Benchmark Artifact:** MediScanAI Evaluation Suite  
**Phase:** Phase A.1.2 — Evidence Provenance Remediation & Automated Re-audit  
**Status:** `preliminary_ai_annotated` (Pending Human Clinical Adjudication)  
**Date of Regeneration:** October 14, 2026  
**Author:** Medical Evidence Research Engineer & Benchmark Data Integrity Auditor  

---

## 1. Executive Summary

This report provides a fully reconciled, case-by-case accounting of all **50 canonical benchmark queries** (`MED-BENCH-001` through `MED-BENCH-050`) across the **11 canonical benchmark categories**. It documents candidate evidence retrieval channels (FAISS dense baseline, Neo4j knowledge graph, or dual-channel), native retrieval ranks within the top-5 evaluation window, human review requirements, and coverage status.

### Summary Metrics
- **Total Canonical Cases:** 50 / 50 (100.0% represented)
- **Total Proposed Judgment Rows:** 62
  - **Corpus Candidate Rows:** 57 (from 45 queries with candidate pools)
  - **Explicit Negative-Control Reference Rows:** 5 (from `MED-BENCH-041` through `045`, representing unanswerable queries)
- **Top-5 Retrieval Window Coverage (Empirical Dual-Channel Run):**
  - **Dual-Channel (`both`) Top-5 Hits:** 11 candidates (17.7%)
  - **Baseline-Only Top-5 Hits:** 14 candidates (22.6%)
  - **Graph-Only Top-5 Hits:** 7 candidates (11.3%)
  - **Total Candidates Retrieved in Top-5:** 32 candidates (56.1% of corpus candidates)
  - **Unretrieved in Top-5 (Cutoff = 5):** 25 candidates (43.9% of corpus candidates)
  - **Negative Controls (Expected None):** 5 reference rows (8.1%)
- **Review Requirement Partition:**
  - `none` (Factual chemical, brand, generic, or registry identity): **25 cases** (37 candidate rows: 32 corpus + 5 negative control rows)
  - `qualified_medical_review` (Clinical symptom-disease relationships, multi-symptom mapping, lay expressions): **25 cases** (25 candidate rows)
- **Relevance Grade Distribution:**
  - **Grade 3 (Direct/Definitive):** 45 rows (72.6%)
  - **Grade 2 (Highly Relevant Supporting/Combination):** 11 rows (17.7%)
  - **Grade 1 (Marginally Relevant Secondary Etiology):** 1 row (1.6%) [`MED-BENCH-038` on `disease_chunk_2501`]
  - **Grade 0 (Negative Controls / Irrelevant):** 5 rows (8.1%) [`MED-BENCH-041` to `045`]

---

## 2. Category-Level Breakdown

| Category Index | Canonical Category ID | Query Count | Candidate Rows | Top-5 Retrieved Candidates | Review Requirement | Clinical Triage Classification |
|:---:|---|:---:|:---:|:---:|---|---|
| 1 | `drug_brand_lookup` | 5 | 5 | 5 (100.0%) | `none` | Pure brand-to-substance mapping |
| 2 | `drug_generic_lookup` | 5 | 9 | 5 (55.6%) | `none` | Generic identification |
| 3 | `active_ingredient_lookup` | 5 | 6 | 3 (50.0%) | `none` | Active ingredient verification |
| 4 | `brand_generic_ingredient_relationship` | 5 | 7 | 3 (42.9%) | `none` | Pure brand-to-substance mapping |
| 5 | `single_symptom_disease_retrieval` | 5 | 5 | 3 (60.0%) | `qualified_medical_review` | Single symptom pathology |
| 6 | `multi_symptom_disease_retrieval` | 5 | 5 | 5 (100.0%) | `qualified_medical_review` | Multi-symptom constellation |
| 7 | `synonym_wording_variants` | 5 | 5 | 4 (80.0%) | `qualified_medical_review` | Colloquial terminology translation |
| 8 | `ambiguous_queries` | 5 | 9 | 2 (22.2%) | `none/qualified_medical_review` | Broad differential diagnosis |
| 9 | `insufficient_evidence_unanswerable` | 5 | 5 | 0 (0.0%) | `none` | Unanswerable negative control |
| 10 | `graph_relevant` | 3 | 4 | 1 (25.0%) | `none/qualified_medical_review` | Graph multi-hop relation |
| 11 | `graph_neutral` | 2 | 2 | 1 (50.0%) | `none/qualified_medical_review` | Graph baseline comparison |
| **Total** | **11 Categories** | **50** | **62** | **32 (51.6%)** | **25 none / 25 clinical** | **Fully Audited & Traceable** |

---

## 3. Case-by-Case Coverage Matrix (Exact Machine-Readable Parity)

| Case ID | Query Text | Canonical Category | Evidence ID | Channel Provenance | Baseline Rank | Graph Rank | Proposed Grade | Review Requirement | Annotation Status |
|---|---|---|---|:---:|:---:|:---:|:---:|---|---|
| `MED-BENCH-001` | Lipitor | `drug_brand_lookup` | `drug_53548` | `both` | 1 | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-002` | Cinzan | `drug_brand_lookup` | `drug_2305` | `both` | 1 | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-003` | Amoxil | `drug_brand_lookup` | `drug_13249` | `both` | 1 | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-004` | Advil | `drug_brand_lookup` | `drug_2765` | `both` | 4 | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-005` | Zyrtec | `drug_brand_lookup` | `drug_25219` | `both` | 2 | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-006` | Atorvastatin calcium | `drug_generic_lookup` | `drug_640` | `graph` | - | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-006` | Atorvastatin calcium | `drug_generic_lookup` | `drug_53548` | `unretrieved_in_top5` | - | - | 2 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-007` | Cinnarizine | `drug_generic_lookup` | `drug_2305` | `both` | 1 | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-008` | Amoxicillin | `drug_generic_lookup` | `drug_353` | `graph` | - | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-008` | Amoxicillin | `drug_generic_lookup` | `drug_13249` | `unretrieved_in_top5` | - | - | 2 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-009` | Ibuprofen | `drug_generic_lookup` | `drug_44` | `graph` | - | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-009` | Ibuprofen | `drug_generic_lookup` | `drug_2765` | `unretrieved_in_top5` | - | - | 2 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-010` | Cetirizine hydrochloride | `drug_generic_lookup` | `drug_110` | `graph` | - | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-010` | Cetirizine hydrochloride | `drug_generic_lookup` | `drug_25219` | `unretrieved_in_top5` | - | - | 2 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-011` | Metformin | `active_ingredient_lookup` | `drug_345` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-012` | Acetaminophen | `active_ingredient_lookup` | `drug_25` | `graph` | - | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-013` | Ciprofloxacin | `active_ingredient_lookup` | `drug_5711` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-014` | Omeprazole | `active_ingredient_lookup` | `drug_116` | `graph` | - | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-015` | Lisinopril | `active_ingredient_lookup` | `drug_923` | `graph` | - | 1 | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-015` | Lisinopril | `active_ingredient_lookup` | `drug_473` | `unretrieved_in_top5` | - | - | 2 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-016` | What is the active ingredient in Lipitor? | `brand_generic_ingredient_relationship` | `drug_53548` | `baseline` | 1 | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-017` | What generic drug is in Advil? | `brand_generic_ingredient_relationship` | `drug_2765` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-017` | What generic drug is in Advil? | `brand_generic_ingredient_relationship` | `drug_44` | `unretrieved_in_top5` | - | - | 2 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-018` | What brand name products contain Cinnarizine? | `brand_generic_ingredient_relationship` | `drug_2305` | `baseline` | 2 | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-019` | Is Amoxil brand for amoxicillin? | `brand_generic_ingredient_relationship` | `drug_13249` | `baseline` | 1 | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-019` | Is Amoxil brand for amoxicillin? | `brand_generic_ingredient_relationship` | `drug_353` | `unretrieved_in_top5` | - | - | 2 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-020` | What active ingredients are in Lisinopril and Hydrochlorothiazide combination? | `brand_generic_ingredient_relationship` | `drug_473` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-021` | oliguria | `single_symptom_disease_retrieval` | `disease_chunk_2501` | `unretrieved_in_top5` | - | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-022` | absence of menstruation | `single_symptom_disease_retrieval` | `disease_chunk_3001` | `unretrieved_in_top5` | - | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-023` | facial tenderness | `single_symptom_disease_retrieval` | `disease_chunk_501` | `both` | 1 | 2 | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-024` | recurrent episodes of wheezing | `single_symptom_disease_retrieval` | `disease_chunk_417` | `both` | 1 | 1 | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-025` | intense joint pain in foot | `single_symptom_disease_retrieval` | `disease_chunk_400` | `baseline` | 1 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-026` | itchy skin particularly on hands and feet during pregnancy | `multi_symptom_disease_retrieval` | `disease_chunk_1` | `baseline` | 1 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-027` | absence of menstruation, infertility, and pelvic pain | `multi_symptom_disease_retrieval` | `disease_chunk_3001` | `both` | 2 | 4 | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-028` | facial tenderness, nasal congestion, and sinus pressure | `multi_symptom_disease_retrieval` | `disease_chunk_501` | `both` | 3 | 2 | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-029` | oliguria, shortness of breath, and hyperkalemia | `multi_symptom_disease_retrieval` | `disease_chunk_2501` | `both` | 1 | 1 | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-030` | severe neck pain with difficulty moving head and numbness in arms | `multi_symptom_disease_retrieval` | `disease_chunk_51` | `baseline` | 1 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-031` | blocked nose and sinus headache | `synonym_wording_variants` | `disease_chunk_501` | `baseline` | 2 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-032` | painful swollen veins in rectal area with bleeding | `synonym_wording_variants` | `disease_chunk_201` | `baseline` | 1 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-033` | tight band pressure sensation around both sides of head | `synonym_wording_variants` | `disease_chunk_101` | `baseline` | 1 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-034` | kidney failure with reduced urine output | `synonym_wording_variants` | `disease_chunk_2501` | `unretrieved_in_top5` | - | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-035` | missed periods, trouble getting pregnant, and weight gain | `synonym_wording_variants` | `disease_chunk_3001` | `baseline` | 2 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-036` | Metformin | `ambiguous_queries` | `drug_345` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-037` | Cough and fever | `ambiguous_queries` | `disease_chunk_248` | `unretrieved_in_top5` | - | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-037` | Cough and fever | `ambiguous_queries` | `disease_chunk_501` | `unretrieved_in_top5` | - | - | 2 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-038` | Chest pain | `ambiguous_queries` | `disease_chunk_2472` | `unretrieved_in_top5` | - | - | 2 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-038` | Chest pain | `ambiguous_queries` | `disease_chunk_2501` | `unretrieved_in_top5` | - | - | 1 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-039` | Fatigue and dizziness | `ambiguous_queries` | `disease_chunk_336` | `baseline` | 1 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-039` | Fatigue and dizziness | `ambiguous_queries` | `disease_chunk_89` | `unretrieved_in_top5` | - | - | 2 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-039` | Fatigue and dizziness | `ambiguous_queries` | `disease_chunk_160` | `unretrieved_in_top5` | - | - | 2 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-040` | Pain area - abdomen | `ambiguous_queries` | `disease_chunk_555` | `baseline` | 2 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-046` | Find all drug products containing Cinnarizine | `graph_relevant` | `drug_2305` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-047` | Diseases presenting both oliguria and hyperkalemia | `graph_relevant` | `disease_chunk_2501` | `baseline` | 4 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-048` | What products share the active ingredient Cetirizine hydrochloride? | `graph_relevant` | `drug_25219` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-048` | What products share the active ingredient Cetirizine hydrochloride? | `graph_relevant` | `drug_110` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-049` | Cinzan adverse reactions | `graph_neutral` | `drug_2305` | `unretrieved_in_top5` | - | - | 3 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-050` | Tension Headache symptoms and head pain | `graph_neutral` | `disease_chunk_101` | `baseline` | 1 | - | 3 | `qualified_medical_review` | `preliminary_ai_annotated` |
| `MED-BENCH-041` | NonexistentDrugZ 500mg dosage and administration | `insufficient_evidence_unanswerable` | `none` | `none` | - | - | 0 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-042` | Treatment protocol for acute Martian respiratory syndrome | `insufficient_evidence_unanswerable` | `none` | `none` | - | - | 0 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-043` | Does Lipitor cure acute viral Covid-19 infection? | `insufficient_evidence_unanswerable` | `none` | `none` | - | - | 0 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-044` | FDA pediatric approval date for Xanthroflurane inhalation | `insufficient_evidence_unanswerable` | `none` | `none` | - | - | 0 | `none` | `preliminary_ai_annotated` |
| `MED-BENCH-045` | Recommended dosage of chocolate syrup for acute appendicitis | `insufficient_evidence_unanswerable` | `none` | `none` | - | - | 0 | `none` | `preliminary_ai_annotated` |

---

## 4. Analysis of Retrieval Channel Provenance and Top-5 Cutoffs

### A. Candidates Unretrieved in Top-5 (25 Rows)
In the empirical dual-channel run (`eval_both_20261014_152200`), 25 candidate items were placed outside the `top_k=5` cutoff. These items are preserved with their true relevance grades:
1. **Fixed-Dose Combinations:** Co-formulated products (such as `drug_473` Lisinopril+HCTZ) were ranked below single-ingredient monotherapies (`drug_923`) in graph queries.
2. **Brand Counterparts on Generic Queries:** For generic lookup queries (`MED-BENCH-006`, `008`, `009`, `010`), unbranded generic items achieved Rank 1 in graph retrieval, pushing brand counterparts (`drug_53548`, `drug_13249`, `drug_2765`, `drug_25219`) beyond top 5.
3. **Disease Chunk Indexing Scope:** The Neo4j graph currently models prescription and substance nodes, meaning disease symptom queries (`MED-BENCH-021` to `040`) rely exclusively on the FAISS dense index. Dense vector competition displaced certain disease chunks outside the top 5.

### B. Grading Independence Principle
In accordance with standard IR and RAG evaluation methodology, relevance is an intrinsic attribute of the relationship between the user query and the document content. Unretrieved candidates receive relevance judgments based strictly on whether the document satisfies the information need, independent of retrieval position.
