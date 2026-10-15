# MediScanAI Gold Judgment Promotion Policy & Sign-Off Checklist

**Benchmark Suite:** MediScanAI Retrieval Benchmark  
**Phase:** Phase A.2 — Gold Promotion Governance & Verification Gates  
**Status:** Canonical Promotion Policy  
**Target File:** `evaluation/benchmark/gold_judgments.jsonl` (Strictly Read-Only Until Promotion Authorized)  

---

## 1. Core Promotion Policy

The gold judgment dataset ([gold_judgments.jsonl](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/gold_judgments.jsonl)) is the authoritative ground truth for official retrieval evaluation, metric computation (Recall@K, MRR, Precision@K), and downstream LLM answer validation.

**Under no circumstances may any record be promoted from preliminary AI status to gold ground truth without satisfying all seven mandatory gates specified below.**

Automated evaluation runs, exploratory testing, and Phase C Ragas evaluation are strictly blocked from using preliminary AI annotations as gold labels.

---

## 2. The Seven Mandatory Promotion Gates

```
+-----------------------------------------------------------------------------------+
| GATE 1: HUMAN REVIEW COMPLETION                                                   |
| - judgment_status == "human_reviewed"                                             |
| - reviewer_id is verified and non-null                                             |
| - reviewed_at is valid ISO-8601 UTC timestamp                                     |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| GATE 2: REVIEWER QUALIFICATION JURISDICTION                                       |
| - review_requirement == "qualified_medical_review" => reviewed by clinical_expert |
|   or lead_adjudicator (nonclinical_auditor prohibited)                            |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| GATE 3: DISAGREEMENT & ESCALATION RESOLUTION                                      |
| - 0 pending "escalate" items                                                      |
| - All |grade_A - grade_B| >= 1 discrepancies resolved via consensus conference    |
| - adjudication_status in ("reviewed", "consensus_resolved")                       |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| GATE 4: SOURCE EVIDENCE TRACEABILITY                                              |
| - Active, verified primary source URL (DailyMed, MedlinePlus, FDA, WHO)           |
| - Supporting excerpt verified against source text                                 |
| - Exact match on active ingredient, strength, route, and combination status       |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| GATE 5: NEGATIVE CONTROL CONTRACT COMPLIANCE                                      |
| - Unanswerable negative controls (MED-BENCH-041 to 045) have relevance_grade == 0 |
| - candidate_gold_evidence_ids remains empty in candidate_queries.jsonl            |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| GATE 6: REFERENTIAL INTEGRITY & SCHEMA VALIDATION                                 |
| - All 50 canonical case IDs represented                                           |
| - source_record_id resolves to existing line in drugs or diseases FAISS dataset   |
| - Passes formal JSON schema validation (review_schema.json)                       |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| GATE 7: IMMUTABILITY, AUDIT TRAIL & LEAD ADJUDICATOR SIGN-OFF                     |
| - Full change log committed to version control with SHA-256 checksums             |
| - Signed approval by Lead Adjudicator                                             |
+-----------------------------------------------------------------------------------+
```

---

## 3. Detailed Gate Specifications

### Gate 1: Human Review Completion
- Every record must have `judgment_status == "human_reviewed"`. Any record marked `preliminary_ai_annotated` or `unverified_candidate` is automatically rejected.
- `reviewer_id` must match a recognized individual registered in `reviewer_roles.md`.
- `reviewed_at` must be a valid ISO-8601 UTC timestamp (e.g. `2026-10-15T16:22:00Z`).
- `reviewed_grade` must be an integer in $\{0, 1, 2, 3\}$.

### Gate 2: Reviewer Qualification Jurisdiction
- Every record with `review_requirement == "qualified_medical_review"` must have been reviewed by a `clinical_expert` or `lead_adjudicator`.
- If a nonclinical auditor reviewed a clinical case, the review is void and must be re-adjudicated by a licensed clinician before promotion.

### Gate 3: Disagreement and Escalation Resolution
- No record with `adjudication_status == "escalated"` may be promoted.
- For items reviewed by multiple annotators, inter-reviewer agreement ($\kappa$) must be computed and recorded. Any discrepancy $|\text{grade}_A - \text{grade}_B| \ge 1$ must have a documented consensus resolution or enforce the conservative lower-grade rule.

### Gate 4: Source Evidence Traceability
- The supporting URL must resolve to an authentic, active regulatory or clinical record (HTTP 200).
- Monotherapy queries must cite monotherapy product labels. Combination queries must cite combination labels.
- The supporting excerpt must substantiate the specific information need, not merely mention the drug or pathology.

### Gate 5: Negative Control Contract Compliance
- Queries `MED-BENCH-041` through `MED-BENCH-045` represent unanswerable negative controls.
- By contractual definition, their relevance grade is `0`.
- In `candidate_queries.jsonl`, `candidate_gold_evidence_ids` must remain `[]`.
- No retrieved candidate may be promoted as positive gold evidence for an unanswerable query.

### Gate 6: Referential Integrity & Schema Validation
- All candidate evidence IDs must resolve to physical rows in `data/drugs_faiss_data.jsonl` or `data/diseases_faiss_data.jsonl` (or be `"none"` for negative controls).
- Record structure must validate against [review_schema.json](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/human_review/review_schema.json).

### Gate 7: Immutability and Audit Trail
- Promotion must generate a dedicated commit on Git with a machine-verifiable SHA-256 digest of `gold_judgments.jsonl`.
- `benchmark_metadata.json` must be updated with the promotion timestamp, lead adjudicator identity, reviewer roster, and agreement statistics.

---

## 4. Promotion Sign-Off Checklist (Lead Adjudicator Form)

Before executing the promotion script to populate `gold_judgments.jsonl`, the Lead Adjudicator must complete and sign this audit checklist:

- [ ] **Completeness:** All 50 canonical benchmark queries (`MED-BENCH-001` through `MED-BENCH-050`) have completed human review.
- [ ] **Parity:** Exactly 57 candidate pool rows and 5 negative control rows are accounted for (total 62 decisions).
- [ ] **No Preliminary Leakage:** Zero records remain in `preliminary_ai_annotated` status.
- [ ] **Clinical Jurisdiction:** All 25 clinical candidate rows (`review_requirement: qualified_medical_review`) were audited and approved by a licensed MD/DO/PharmD.
- [ ] **DailyMed & Source Parity:** All cited package inserts and guideline URLs were verified for product and formulation identity.
- [ ] **Negative Controls:** Negative controls `MED-BENCH-041` to `045` are confirmed at Grade 0 with empty gold target lists.
- [ ] **Agreement Metrics:** Inter-reviewer agreement ($\kappa_w$ or Fleiss's $\kappa$) is calculated and documented (or single-reviewer transparency declared).
- [ ] **Unresolved Queue Empty:** Zero records remain in `adjudication_status: escalated`.

**Lead Adjudicator Signature:** ___________________________  
**Printed Name & Credentials:** ___________________________  
**Date of Authorization:** ___________________________  
