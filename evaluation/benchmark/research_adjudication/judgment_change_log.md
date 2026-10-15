# Benchmark Proposed Judgment Change Log (Phase A.1.2)

**Benchmark Artifact:** MediScanAI Evaluation Suite  
**Phase:** Phase A.1.2 — Evidence Provenance Remediation  
**Date:** October 14, 2026  
**Auditor:** Medical Evidence Research Engineer & Benchmark Data Integrity Auditor  

---

## 1. Executive Summary

This changelog records all updates applied to [proposed_judgments.jsonl](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/research_adjudication/proposed_judgments.jsonl), [source_evidence.jsonl](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/research_adjudication/source_evidence.jsonl), and [reviewer_packet.csv](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/research_adjudication/reviewer_packet.csv) during Phase A.1.2.

- **Total Canonical Cases:** 50 (100% preserved)
- **Total Proposed Judgment Rows:** 62 (100% preserved)
- **Total Relevance Grades Modified:** **0** (All 62 proposed relevance grades confirmed by authentic source labeling)
- **Total Source Provenance URLs Remediated:** **27 rows** across 14 unique DailyMed SPL records
- **Annotation Status:** 100% preserved as `preliminary_ai_annotated` with `reviewed_at: null`

---

## 2. Relevance Grade Continuity Audit

In accordance with Phase A.1.2 requirements, no relevance grades were silently modified. Every proposed relevance grade was audited against the authentic, live DailyMed labeling:

| Grade Value | Phase A.1 Initial Count | Phase A.1.2 Remediated Count | Net Change | Clinical / Regulatory Rationale |
|:---:|:---:|:---:|:---:|---|
| **Grade 3** | 45 | 45 | 0 | Definitive answers confirmed by FDA product labeling (exact brand lookups, unbranded generic monotherapies, primary pathognomonic symptoms). |
| **Grade 2** | 11 | 11 | 0 | Supporting evidence confirmed (Lisinopril+HCTZ combination products on single-ingredient queries; brand counterparts on generic queries; valid supporting differential etiologies). |
| **Grade 1** | 1 | 1 | 0 | Marginally relevant secondary etiology confirmed (`MED-BENCH-038` "Chest pain" on `disease_chunk_2501` Chronic Kidney Failure, reflecting uremic pericarditis). |
| **Grade 0** | 5 | 5 | 0 | Negative controls confirmed (`MED-BENCH-041` to `045`, verified against Drugs@FDA, WHO ICD-11, and WSES guidelines as unanswerable/fictitious/false). |
| **Total** | **62** | **62** | **0** | **100% Grade Continuity Maintained** |

---

## 3. Detailed Record Change Log (Source Provenance Remediation)

The 27 proposed judgment rows updated with authentic DailyMed package insert metadata are cataloged below:

| Case ID | Query Text | Evidence ID | Remediated Field | Old (Phase A.1) Value | New (Phase A.1.2) Remediated Value |
|---|---|---|---|---|---|
| `MED-BENCH-001` | Lipitor | `drug_53548` | `source_url` | `setid=4b60098e-4a61-464a-93e8-5b0c8b211a37` | `setid=a60cc18b-0631-4cf0-b021-9f52224ece65` |
| `MED-BENCH-003` | Amoxil | `drug_13249` | `source_url` | `setid=295e865f-7550-4d43-8f0a-7e10c7e2b17f` | `setid=ec7dd735-dc92-3d29-e053-2a95a90af549` |
| `MED-BENCH-004` | Advil | `drug_2765` | `source_url` | `setid=9e0839e0-cb4a-4648-9f37-1249b6b9319e` | `setid=1a665e64-9f30-be37-4a83-38789f1f1e89` |
| `MED-BENCH-005` | Zyrtec | `drug_25219` | `source_url` | `setid=1f2b489a-0e95-4eb8-b4b1-9cb6f96da605` | `setid=568960cf-2c8f-f1b0-e063-6294a90aebc7` |
| `MED-BENCH-006` | Atorvastatin calcium | `drug_640` | `source_url` | `setid=8f2762a8-12c8-4720-9cb5-cdca63d0f77d` | `setid=d9adb9e4-c495-9530-e5e3-7e3b01d53e4c` |
| `MED-BENCH-006` | Atorvastatin calcium | `drug_53548` | `source_url` | `setid=4b60098e-4a61-464a-93e8-5b0c8b211a37` | `setid=a60cc18b-0631-4cf0-b021-9f52224ece65` |
| `MED-BENCH-008` | Amoxicillin | `drug_353` | `source_url` | `setid=6e5c5dd8-4e1b-4f91-a131-4043b2f81498` | `setid=61a9829b-4792-4caa-b75a-b84812f28d4a` |
| `MED-BENCH-008` | Amoxicillin | `drug_13249` | `source_url` | `setid=295e865f-7550-4d43-8f0a-7e10c7e2b17f` | `setid=ec7dd735-dc92-3d29-e053-2a95a90af549` |
| `MED-BENCH-009` | Ibuprofen | `drug_44` | `source_url` | `setid=a00e5bc5-8a2b-43fb-bc5f-a365f5a89476` | `setid=152b0c90-b0c3-4b1b-9e93-4b4c6b3118bd` |
| `MED-BENCH-009` | Ibuprofen | `drug_2765` | `source_url` | `setid=9e0839e0-cb4a-4648-9f37-1249b6b9319e` | `setid=1a665e64-9f30-be37-4a83-38789f1f1e89` |
| `MED-BENCH-010` | Cetirizine hydrochloride | `drug_110` | `source_url` | `setid=c58cbe7b-832d-4537-8ffc-18a715fbc70e` | `setid=d55dfce1-acef-3342-e053-2a95a90a4b83` |
| `MED-BENCH-010` | Cetirizine hydrochloride | `drug_25219` | `source_url` | `setid=1f2b489a-0e95-4eb8-b4b1-9cb6f96da605` | `setid=568960cf-2c8f-f1b0-e063-6294a90aebc7` |
| `MED-BENCH-011` | Metformin | `drug_345` | `source_url` | `setid=2da387a3-11b0-46f3-a8d2-430ec12b33e4` | `setid=ef77c7dd-a65f-4adc-a0d9-a93779b459a0` |
| `MED-BENCH-013` | Ciprofloxacin | `drug_5711` | `source_url` | `setid=eb11f71a-2895-46f1-a1dc-11ce13f99335` | `setid=cbbbf939-3219-4515-a48e-ca264daa4d07` |
| `MED-BENCH-014` | Omeprazole | `drug_116` | `source_url` | `setid=a64e263c-3965-4f32-82ea-ea8a2fa44a56` | `setid=10efef7c-bdf4-36cf-e063-6394a90a8c0f` |
| `MED-BENCH-015` | Lisinopril | `drug_923` | `source_url` | `setid=a4f1e5f8-8bb3-43ef-b202-b2d97c36a44c` | `setid=34ebeea1-6812-4697-84c4-b2ae4f39e55f` |
| `MED-BENCH-015` | Lisinopril | `drug_473` | `source_url` | `setid=e902c525-4b33-4f96-b333-e69458da39b5` | `setid=515f735c-5dba-43d9-8a58-97a319cafd56` |
| `MED-BENCH-016` | What is the active ingredient in Lipitor? | `drug_53548` | `source_url` | `setid=4b60098e-4a61-464a-93e8-5b0c8b211a37` | `setid=a60cc18b-0631-4cf0-b021-9f52224ece65` |
| `MED-BENCH-017` | What generic drug is in Advil? | `drug_2765` | `source_url` | `setid=9e0839e0-cb4a-4648-9f37-1249b6b9319e` | `setid=1a665e64-9f30-be37-4a83-38789f1f1e89` |
| `MED-BENCH-017` | What generic drug is in Advil? | `drug_44` | `source_url` | `setid=a00e5bc5-8a2b-43fb-bc5f-a365f5a89476` | `setid=152b0c90-b0c3-4b1b-9e93-4b4c6b3118bd` |
| `MED-BENCH-019` | Is Amoxil brand for amoxicillin? | `drug_13249` | `source_url` | `setid=295e865f-7550-4d43-8f0a-7e10c7e2b17f` | `setid=ec7dd735-dc92-3d29-e053-2a95a90af549` |
| `MED-BENCH-019` | Is Amoxil brand for amoxicillin? | `drug_353` | `source_url` | `setid=6e5c5dd8-4e1b-4f91-a131-4043b2f81498` | `setid=61a9829b-4792-4caa-b75a-b84812f28d4a` |
| `MED-BENCH-020` | What active ingredients are in Lisinopril and Hydrochlorothiazide combination? | `drug_473` | `source_url` | `setid=e902c525-4b33-4f96-b333-e69458da39b5` | `setid=515f735c-5dba-43d9-8a58-97a319cafd56` |
| `MED-BENCH-036` | Joint pain | `drug_345` | `source_url` | `setid=2da387a3-11b0-46f3-a8d2-430ec12b33e4` | `setid=ef77c7dd-a65f-4adc-a0d9-a93779b459a0` |
| `MED-BENCH-043` | Does Lipitor cure acute viral Covid-19 infection? | `none` | `source_url` | `setid=4b60098e-4a61-464a-93e8-5b0c8b211a37` | `setid=a60cc18b-0631-4cf0-b021-9f52224ece65` |
| `MED-BENCH-048` | What products share the active ingredient Cetirizine hydrochloride? | `drug_25219` | `source_url` | `setid=1f2b489a-0e95-4eb8-b4b1-9cb6f96da605` | `setid=568960cf-2c8f-f1b0-e063-6294a90aebc7` |
| `MED-BENCH-048` | What products share the active ingredient Cetirizine hydrochloride? | `drug_110` | `source_url` | `setid=c58cbe7b-832d-4537-8ffc-18a715fbc70e` | `setid=d55dfce1-acef-3342-e053-2a95a90a4b83` |
