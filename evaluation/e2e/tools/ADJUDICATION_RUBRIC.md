# MediScanAI Human Adjudication Rubric (Phase 3B)

**Target Document:** [`evaluation/e2e/results/B0/adjudication_sheet_blind.csv`](file:///Users/sj/Documents/mediscanai/evaluation/e2e/results/B0/adjudication_sheet_blind.csv)  
**Authoritative Judge Model:** `llama3.1:8b`  
**Purpose:** Blinded clinical adjudication of extracted statements to establish the reference baseline B0.

---

## 1. Blinding & Anchoring Prevention

To prevent human cognitive anchoring to the AI judge's opinion:
- Use **`adjudication_sheet_blind.csv`** for primary human review.
- The AI judge's verdict (`judge_verdict`) and rationale (`judge_reason`) are deliberately omitted during initial labeling.
- The human reviewer must evaluate the statement purely against the supplied clinical evidence context blocks (`relevant_evidence_blocks`) and the generated model response (`judged_answer`).

---

## 2. Labeling Definitions (`human_label` column)

Every statement row must be annotated with one of three lowercase labels:

### A. `supported`
- **Definition:** The statement is clinically and factually substantiated by the provided reference evidence blocks (`[E1]`, `[E2]`, etc.).
- **Criteria:**
  - The disease-symptom relationship, indication, dosage, active ingredient, or medical contraindication is explicitly stated or directly entailed by the evidence.
  - Conservative clinical paraphrasing or standard synonymy (e.g. "high blood pressure" for "hypertension") that does not distort meaning is considered supported.

### B. `unsupported`
- **Definition:** The statement is not substantiated by the provided evidence blocks.
- **Criteria:**
  - **Hallucination:** An active ingredient, drug indication, or diagnostic claim not present in any evidence block.
  - **Misattribution:** Assigning symptoms or indications of Drug A to Drug B.
  - **Overreach:** Claiming a definitive diagnosis when the evidence only lists possible symptom overlap.
  - **Irrelevant / Prompt Contamination:** Few-shot examples (e.g. statements regarding Albert Einstein in case `E2E-080`) that appear in the output must be marked `unsupported` as they have zero clinical connection to the medical evidence.

### C. `unclear`
- **Definition:** The statement is grammatically ambiguous, truncated, or lacks sufficient context boundaries to make a decisive supported/unsupported determination.
- **Criteria:**
  - Sentence fragments that cannot be evaluated standalone.
  - Ambiguous pronoun references that cannot be resolved from the judged answer.

---

## 3. Contaminated Case Handling (`E2E-080`)

Case `E2E-080` contains known prompt contamination where the judge reproduced RAGAS few-shot examples (Einstein relativity statements). 
- In the adjudication sheet, these statements are retained for transparency.
- The reviewer should label them according to clinical evidence grounding (which will be `unsupported`).
- The adjudication statistics computer (`adjudication_stats.py`) isolates contaminated cases into a separate audit block so they do not artificially distort ordinary clinical agreement rates.

---

## 4. Acceptance Criteria for "ESTABLISHED" Status

Once all rows are labeled, executing:
```bash
PYTHONPATH=. python evaluation/e2e/tools/adjudication_stats.py
```
computes the agreement metrics. Baseline B0 can only advance from `provisional` to `established` if:
1. **Overall Judge-Human Agreement:** $\ge 85.0\%$
2. **Judge-Negative Precision:** $\ge 80.0\%$ (at least 80% of judge-negative verdicts are human-confirmed `unsupported`)
3. **Contaminated Cases:** Contaminated statements are explicitly flagged and resolved.
