# MediScanAI Human Adjudication Workflow

**Directory:** `evaluation/benchmark/human_review/`  
**Purpose:** Operational human review suite for validating and establishing verified clinical and nonclinical ground truth for the MediScanAI retrieval benchmark.  
**Phase:** Phase A.2 — Human Adjudication Workflow Preparation  
**Benchmark Target:** 50 canonical queries (`MED-BENCH-001` to `MED-BENCH-050`), 62 total candidate rows.

---

## 1. Overview and Operational Philosophy

MediScanAI employs a **staged, research-assisted adjudication paradigm**. Preliminary retrieval outputs and candidate pools were empirically gathered and researched against official medical registries (DailyMed, MedlinePlus, FDA, WHO). All AI-proposed annotations are explicitly classified as `preliminary_ai_annotated` and do **not** constitute ground truth.

The primary objective of the human review workflow is to transition these preliminary hypotheses into verified human ground truth through independent, qualified, and auditable human review.

### Core Principles
1. **Separation of Preliminary Hypotheses from Ground Truth:**  
   AI-proposed relevance grades (`proposed_grade`, `proposed_rationale`) serve purely as research references. Human reviewers must record their decisions independently in distinct fields (`human_decision`, `reviewed_grade`, `reviewer_rationale`).
2. **Strict Competency Boundaries:**  
   Cases are partitioned by domain complexity. Factual product and identity lookups may be validated by technical data auditors, while all clinical disease-symptom relationships, multi-symptom presentations, and diagnostic differentials are strictly reserved for licensed medical professionals (`clinical_expert` or `lead_adjudicator`).
3. **Immutability of the Gold Dataset:**  
   No human review tool or reviewer may directly edit [gold_judgments.jsonl](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/gold_judgments.jsonl). Promotion to gold is governed by a strict, multi-gate automated policy ([gold_promotion_policy.md](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/human_review/gold_promotion_policy.md)).

---

## 2. Directory Layout and File Inventory

```
evaluation/benchmark/human_review/
├── README.md                  # This operational overview and reviewer guide
├── review_template.csv        # Blank 62-row tabular review sheet for human annotators
├── review_schema.json         # Formal Draft-07 JSON schema validating human review records
├── review_protocol.md         # Detailed adjudication guidelines and disagreement procedures
├── reviewer_roles.md          # Qualification matrix, permissions, and jurisdictional boundaries
└── gold_promotion_policy.md   # Explicit promotion gates, validation checks, and sign-off checklist
```

---

## 3. Step-by-Step Reviewer Guide

### Step 1: Claim Assigned Cases According to Qualification
Before opening [review_template.csv](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/human_review/review_template.csv), identify your assigned cases based on your declared qualification role ([reviewer_roles.md](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/human_review/reviewer_roles.md)):
- **Nonclinical Auditors (`nonclinical_auditor`):** Restricted to rows where `review_requirement == "none"` (29 unique cases, 37 rows).
- **Clinical Experts (`clinical_expert`):** Responsible for rows where `review_requirement == "qualified_medical_review"` (21 unique cases, 25 rows), as well as any escalated product cases.
- **Lead Adjudicators (`lead_adjudicator`):** Adjudicates consensus conferences, inter-reviewer disagreements, and final promotion sign-offs.

### Step 2: Independent Assessment & Blinding Guardrail
- **Cognitive Bias Warning:** Do **not** begin by inspecting `proposed_grade`. Read the verbatim `query` and the `evidence_id` / `evidence_excerpt` first.
- Formulate your independent judgment: Does this retrieved record satisfy the specific information need of the user query?

### Step 3: Source Verification
- Click the provided `supporting_source_url` (or query the official registry).
- For drug products: Verify that the DailyMed Structured Product Labeling (SPL) matches the exact active substance, strength, formulation, and monotherapy vs. combination status.
- For disease chunks: Verify that the clinical symptom profile in MedlinePlus, CDC, or clinical guidelines directly supports the relationship.
- For negative controls (`MED-BENCH-041` to `045`): Verify that the entity is nonexistent in regulatory registries or that the medical claim is factually false.

### Step 4: Record the Review Decision
In [review_template.csv](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/human_review/review_template.csv), complete the following blank fields:

| Field Name | Allowed Values | Description / Requirement |
|---|---|---|
| `human_decision` | `agree`, `disagree`, `insufficient_evidence`, `escalate` | Action taken relative to the preliminary AI hypothesis. |
| `reviewed_grade` | `0`, `1`, `2`, `3` | Your independent integer relevance grade (see rubric below). |
| `reviewer_id` | e.g. `dr_chen_md`, `pharm_d_patel` | Your verified, non-null reviewer identifier. |
| `reviewer_role` | `nonclinical_auditor`, `clinical_expert`, `lead_adjudicator` | Your certified role tier. |
| `reviewed_at` | ISO-8601 string, e.g. `2026-10-15T14:30:00Z` | Precise UTC timestamp when review was completed. |
| `reviewer_rationale` | Free text | Concrete explanation tied to clinical/regulatory evidence. |
| `reviewer_confidence` | `high`, `moderate`, `low` | Degree of certainty in the judgment. |
| `supporting_source_url` | Valid URL | Authoritative URL confirming the clinical/factual ground truth. |
| `adjudication_status` | `reviewed` or `escalated` | Set to `reviewed` if conclusive, or `escalated` if referral is required. |
| `adjudication_notes` | Free text | Optional consensus notes or escalation justification. |

---

## 4. Relevance Grading Scale (0 to 3)

The benchmark utilizes the official 4-level relevance grading scale documented in [judgment_guidelines.md](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/judgment_guidelines.md):

- **Grade 3 (Definitive / Direct Answer):**  
  The candidate directly, fully, and accurately resolves the query.
  - *Drugs:* Exact brand-to-generic identity match, exact unbranded monotherapy active substance match, or exact active ingredient verification.
  - *Diseases:* Direct pathognomonic symptom profile matching the query pathology.
- **Grade 2 (Highly Relevant Supporting Evidence):**  
  The candidate contains essential, highly related clinical/pharmacological context, but is not a single direct answer.
  - *Drugs:* Fixed-dose combination product containing the requested active ingredient; brand counterpart retrieved on generic query.
  - *Diseases:* Legitimate secondary etiology or valid differential diagnosis matching non-specific symptoms (e.g. Type 2 Diabetes for "fatigue and dizziness").
- **Grade 1 (Marginally Relevant Evidence):**  
  The candidate mentions a related medical entity or peripheral association, but does not provide actionable clinical guidance or direct answers.
  - *Example:* Advanced renal failure mentioning uremic pleuritic chest pain on a broad "Chest pain" query (`MED-BENCH-038`).
- **Grade 0 (Irrelevant / False / Negative Control):**  
  The candidate is completely uninformative, medically erroneous, or represents an unanswerable negative control query (`MED-BENCH-041` to `045`).

---

## 5. Review Outcomes & Decision Tree

```
                      [Reviewer Inspects Case & Source Evidence]
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
         [Factual Drug/ID Case]                        [Clinical Relevance Case]
        (review_requirement: none)               (review_requirement: qualified_medical)
                  │                                               │
        Permitted: Nonclinical Auditor                  Permitted: Clinical Expert
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                         [Does evidence support claim?]
                                          │
         ┌───────────────────┬────────────┴────────────┬───────────────────┐
         ▼                   ▼                         ▼                   ▼
     [AGREE]             [DISAGREE]              [INSUFFICIENT]       [ESCALATE]
  Matches AI grade.   Assign true grade.       Source lacks proof.   Borderline case.
  reviewed_grade =    reviewed_grade =         reviewed_grade = 0.   reviewed_grade = blank.
  proposed_grade      new integer [0-3]        adjudication_status = adjudication_status =
  adjudication_status adjudication_status      "reviewed"            "escalated"
  = "reviewed"        = "reviewed"
```

---

## 6. Safety and Audit Restrictions

- **Do Not Edit Production Files:** Reviewers work strictly within `evaluation/benchmark/human_review/`. Never modify files in `app/`, `data/`, or `evaluation/results/`.
- **Do Not Touch Gold Judgments:** [gold_judgments.jsonl](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/gold_judgments.jsonl) is strictly read-only and maintained by automated promotion scripts.
- **Never Synthesize or Fabricate Timestamps:** Every timestamp must reflect actual human review completion.
- **Entity Resolution Off-Limits:** `entity_resolution/` is strictly off-limits.
