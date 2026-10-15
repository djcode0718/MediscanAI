# DailyMed Source Remediation Report (Phase A.1.2)

**Benchmark Artifact:** MediScanAI Evaluation Suite  
**Phase:** Phase A.1.2 — Evidence Provenance Remediation  
**Status:** Remediated & Verified via Official DailyMed REST API  
**Date:** October 14, 2026  
**Auditor:** Medical Evidence Research Engineer & Benchmark Data Integrity Auditor  

---

## 1. Executive Summary

During the Phase A.1.1 integrity audit, all 14 cited DailyMed product label references were identified as containing synthetic/invalid `setid` UUIDs that returned zero elements (`total_elements: 0`) from the official DailyMed REST API.

Under Phase A.1.2, all 14 references were comprehensively researched and remediated against the live National Library of Medicine (NLM) DailyMed database and REST API. Each product was matched to an authentic FDA Structured Product Labeling (SPL) package insert verifying:
1. Exact brand name and/or unbranded generic active substance.
2. Formulation, route, and dosage form (e.g. oral film-coated tablet, oral suspension, extended-release tablet, injection solution).
3. Manufacturer/distributor alignment with raw corpus records.
4. HTTP 200 live page resolution and API element return.

**Resolution Total:** **14 / 14 (100.0%) references successfully remediated and verified.**  
**Unresolved References Remaining:** **0**.

---

## 2. Item-by-Item Source Remediation Table

| Source Key | Product Name / Entity | Former Synthetic SetID | Remediated Live SetID | Live SPL Title & Publisher | Available Revision Date | API & HTTP Status |
|---|---|---|---|---|:---:|:---:|
| `drug_53548` | Lipitor (Atorvastatin Calcium) | `4b60098e-4a61-464a-93e8-5b0c8b211a37` | `a60cc18b-0631-4cf0-b021-9f52224ece65` | `LIPITOR (ATORVASTATIN CALCIUM) TABLET, FILM COATED [VIATRIS SPECIALTY LLC]` | 2026-07-15 | **VERIFIED 200** |
| `NC-043` | Lipitor COVID-19 Negative Control | `4b60098e-4a61-464a-93e8-5b0c8b211a37` | `a60cc18b-0631-4cf0-b021-9f52224ece65` | `LIPITOR (ATORVASTATIN CALCIUM) TABLET, FILM COATED [VIATRIS SPECIALTY LLC]` | 2026-07-15 | **VERIFIED 200** |
| `drug_2765` | Advil (Ibuprofen 200 mg) | `9e0839e0-cb4a-4648-9f37-1249b6b9319e` | `1a665e64-9f30-be37-4a83-38789f1f1e89` | `ADVIL (IBUPROFEN) TABLET, COATED [HALEON US HOLDINGS LLC]` | 2026-03-16 | **VERIFIED 200** |
| `drug_25219` | Zyrtec (Cetirizine HCl) | `1f2b489a-0e95-4eb8-b4b1-9cb6f96da605` | `568960cf-2c8f-f1b0-e063-6294a90aebc7` | `ZYRTEC ALLERGY (CETIRIZINE HYDROCHLORIDE) TABLET, FILM COATED [SELECT CONSUMER GROUP]` | 2026-07-15 | **VERIFIED 200** |
| `drug_13249` | Amoxil (Amoxicillin oral susp) | `295e865f-7550-4d43-8f0a-7e10c7e2b17f` | `ec7dd735-dc92-3d29-e053-2a95a90af549` | `AMOXIL (AMOXICILLIN ORAL SUSP) POWDER, FOR SUSPENSION [DIRECTRX]` | 2025-01-23 | **VERIFIED 200** |
| `drug_640` | Atorvastatin Calcium generic | `8f2762a8-12c8-4720-9cb5-cdca63d0f77d` | `d9adb9e4-c495-9530-e5e3-7e3b01d53e4c` | `ATORVASTATIN CALCIUM TABLET, FILM COATED [APOTEX CORP.]` | 2026-09-10 | **VERIFIED 200** |
| `drug_353` | Amoxicillin generic capsule | `6e5c5dd8-4e1b-4f91-a131-4043b2f81498` | `61a9829b-4792-4caa-b75a-b84812f28d4a` | `AMOXICILLIN CAPSULE [CHARTWELL GOVERNMENTAL & SPECIALTY RX, LLC]` | 2026-10-12 | **VERIFIED 200** |
| `drug_44` | Ibuprofen 200 mg generic | `a00e5bc5-8a2b-43fb-bc5f-a365f5a89476` | `152b0c90-b0c3-4b1b-9e93-4b4c6b3118bd` | `IBUPROFEN TABLET, FILM COATED [A-S MEDICATION SOLUTIONS]` | 2026-10-12 | **VERIFIED 200** |
| `drug_110` | Cetirizine HCl generic tablet | `c58cbe7b-832d-4537-8ffc-18a715fbc70e` | `d55dfce1-acef-3342-e053-2a95a90a4b83` | `CETIRIZINE HYDROCHLORIDE TABLET, COATED [GRANULES PHARMACEUTICALS INC.]` | 2026-10-12 | **VERIFIED 200** |
| `drug_345` | Metformin HCl extended release | `2da387a3-11b0-46f3-a8d2-430ec12b33e4` | `ef77c7dd-a65f-4adc-a0d9-a93779b459a0` | `METFORMIN HYDROCHLORIDE TABLET, EXTENDED RELEASE [AUROBINDO PHARMA LIMITED]` | 2026-10-12 | **VERIFIED 200** |
| `drug_116` | Amazon Basic Care Omeprazole | `a64e263c-3965-4f32-82ea-ea8a2fa44a56` | `10efef7c-bdf4-36cf-e063-6394a90a8c0f` | `AMAZON BASIC CARE OMEPRAZOLE (OMEPRAZOLE) TABLET, DELAYED RELEASE [AMAZON.COM SERVICES LLC]` | 2026-08-31 | **VERIFIED 200** |
| `drug_923` | Lisinopril generic monotherapy | `a4f1e5f8-8bb3-43ef-b202-b2d97c36a44c` | `34ebeea1-6812-4697-84c4-b2ae4f39e55f` | `LISINOPRIL TABLET [BLUEPOINT LABORATORIES]` | 2026-10-09 | **VERIFIED 200** |
| `drug_473` | Lisinopril + HCTZ combination | `e902c525-4b33-4f96-b333-e69458da39b5` | `515f735c-5dba-43d9-8a58-97a319cafd56` | `LISINOPRIL AND HYDROCHLOROTHIAZIDE TABLET [LUPIN PHARMACEUTICALS, INC.]` | 2025-11-26 | **VERIFIED 200** |
| `drug_5711` | Ciprofloxacin in Dextrose 5% | `eb11f71a-2895-46f1-a1dc-11ce13f99335` | `cbbbf939-3219-4515-a48e-ca264daa4d07` | `CIPROFLOXACIN IN DEXTROSE (CIPROFLOXACIN) INJECTION, SOLUTION [HOSPIRA, INC.]` | 2025-12-02 | **VERIFIED 200** |

---

## 3. Verification Details & API Checks

Verification was performed using an automated two-stage validation harness:
1. **DailyMed REST API Check (`/services/v2/spls.json?setid=<setid>`):**
   - Verified that the endpoint returns `total_elements: 1`.
   - Verified that the product title and published date match the SPL metadata.
2. **DailyMed Web Portal Check (`/drugInfo.cfm?setid=<setid>`):**
   - Verified that the URL resolves with HTTP status 200.
   - Extracted and verified HTML `<title>` tags and `<h1>` drug label headers.
   - Confirmed that active ingredients, dosage forms, and product indications correspond directly to the query and evidence contracts.

---

## 4. Impact on Machine-Readable Datasets

- **`proposed_judgments.jsonl`:** Exactly 27 rows referencing these 14 entities were updated with authentic URLs, titles, publishers, and publication dates.
- **`source_evidence.jsonl`:** Exactly 14 primary source registry records were updated with authentic setids, live excerpts, and verified dates.
- **`reviewer_packet.csv`:** Exactly 27 rows updated to match `proposed_judgments.jsonl` with 100% field parity.
- **Relevance Grades:** 0 grades were modified, as the verified official product labeling fully confirms the clinical assessments made in Phase A.1.
