# MediScanAI Reviewer Roles and Qualification Matrix

**Benchmark Suite:** MediScanAI Retrieval Benchmark  
**Phase:** Phase A.2 — Reviewer Qualification & Boundary Matrix  
**Status:** Canonical Role Governance  

---

## 1. Principles of Reviewer Qualification

To guarantee clinical safety and scientific validity, benchmark evaluation data must never conflate technical identity matching with clinical relevance assessment. The review suite enforces a strict, credential-governed jurisdictional boundary across three distinct roles:

1. **Nonclinical Auditor (`nonclinical_auditor`)**
2. **Clinical Expert (`clinical_expert`)**
3. **Lead Adjudicator (`lead_adjudicator`)**

---

## 2. Reviewer Role Matrix

| Attribute / Requirement | Nonclinical Auditor (`nonclinical_auditor`) | Clinical Expert (`clinical_expert`) | Lead Adjudicator (`lead_adjudicator`) |
|---|---|---|---|
| **Minimum Required Credentials** | BS/MS in Computer Science, Data Science, Bioinformatics, or Health Informatics; completion of MediScanAI benchmark adjudication calibration. | Licensed Medical Doctor (MD/DO), Doctor of Pharmacy (PharmD), or MBBS with active clinical or hospital experience. | Board-Certified Physician (MD/DO) or Senior Clinical Pharmacologist with $\ge 5$ years post-graduate clinical practice and informatics experience. |
| **Permitted Review Scope** | **Factual & Identity Queries Only** (`review_requirement == "none"`):<br>- `drug_brand_lookup`<br>- `drug_generic_lookup`<br>- `active_ingredient_lookup`<br>- `brand_generic_ingredient_relationship`<br>- `insufficient_evidence_unanswerable` | **All Clinical & Diagnostic Queries** (`review_requirement == "qualified_medical_review"`):<br>- `single_symptom_disease_retrieval`<br>- `multi_symptom_disease_retrieval`<br>- `synonym_wording_variants`<br>- `ambiguous_queries`<br>- Clinical knowledge lookups | **Full Benchmark Jurisdiction**:<br>- All clinical and nonclinical cases<br>- Escalated and borderline items<br>- Consensus conference adjudication<br>- Gold dataset promotion sign-off |
| **Permitted Case Jurisdiction** | 29 Unique Cases (37 Candidate Rows) | 21 Unique Cases (25 Candidate Rows) *(and optional secondary audit on nonclinical cases)* | All 50 Unique Cases (62 Candidate Rows) |
| **Key Decision Authorities** | Can select `agree`, `disagree`, `insufficient_evidence`, or `escalate` on factual drug identity and regulatory registry presence. | Can select `agree`, `disagree`, `insufficient_evidence`, or `escalate` on clinical presentations, pathognomonic symptoms, and differentials. | Final binding ruling on escalated cases, inter-reviewer disagreements, and promotion gates. |
| **Prohibited Actions** | **STRICTLY PROHIBITED** from grading symptom-disease relevance, evaluating clinical presentations, or interpreting medical necessity. | Prohibited from unilateral promotion to gold without lead adjudicator sign-off. | Cannot override unanimous clinical consensus without written medical justification. |

---

## 3. Jurisdictional Boundary Rules and Enforcements

### Rule 1: The Nonclinical Barrier
Nonclinical auditors are strictly restricted to questions of factual record matching, packaging verification, and regulatory presence:
- *Permitted:* Verifying whether DailyMed SPL `a60cc18b-0631-4cf0-b021-9f52224ece65` lists "Atorvastatin Calcium" as active ingredient for Lipitor.
- *Prohibited:* Judging whether chest pain worsening on deep inspiration in a patient with asthma represents pleuritic vs. bronchospastic etiology (`MED-BENCH-038`).
- **Enforcement:** Any record with `review_requirement == "qualified_medical_review"` submitted with `reviewer_role == "nonclinical_auditor"` will be **automatically invalidated** by the pre-promotion validation gate.

### Rule 2: Clinical Expert Responsibility
Clinical experts must ground all decisions in clinical evidence:
- Must differentiate between primary defining/pathognomonic symptoms (Grade 3) and non-specific associative symptoms (Grade 2 or 1).
- Must enforce Rule 4.5 by ignoring self-referential disease titles in raw symptom arrays and evaluating underlying pathology.
- Must document clinical rationale with reference to established guidelines (e.g., ACOG for obstetric cholestasis, ICHD-3 for headaches, KDIGO for renal failure).

### Rule 3: Lead Adjudicator Sign-Off Authority
- Only a verified `lead_adjudicator` may sign the final promotion authorization checklist.
- The lead adjudicator must personally review every case flagged as `disagree`, `insufficient_evidence`, or `escalate`, as well as any candidate where inter-reviewer grade divergence $|\text{grade}_A - \text{grade}_B| \ge 1$.

---

## 4. Reviewer Identification and Confidentiality

- Every reviewer must be registered in `benchmark_metadata.json` with:
  - Unique Reviewer ID (e.g. `dr_chen_md`, `pharm_d_patel`, `auditor_turner_01`).
  - Professional Credentials (e.g. `MD (Internal Medicine)`, `PharmD, BCPS`, `MS Computer Science`).
  - Institutional Affiliation and Conflict of Interest declaration.
- Pseudonymized identifiers may be used in public benchmark distributions, but a secure, auditable mapping must be maintained internally for clinical data governance.
