# Phase F.2 — Evaluation Contract & Metric Specification

## 1. Scope & Purpose

This evaluation contract establishes the mathematical and procedural rules governing the evaluation of evidence-grounded answer generation in Phase F.2.

Its primary purpose is to decouple the evaluation of user-facing legal disclaimers from the evaluation of biomedical factual grounding, creating a trustworthy, transparent evaluation harness that neither penalizes necessary legal safeguards nor artificially inflates clinical accuracy.

---

## 2. Dual Faithfulness Metric Specifications

Every generated response in Phase F.2 produces two distinct evaluation payloads:

### 2.1 Metric 1: Body-Only Faithfulness (`faithfulness_body_only`)
- **Evaluated String:** `response_body`
- **Definition:** The medical and factual answer content, excluding strictly and only the verbatim mandatory legal disclaimer section.
- **Extraction Protocol:**
  ```python
  if MANDATORY_HEADER in full_text:
      response_body = full_text.split(MANDATORY_HEADER)[0].strip()
  ```
- **Context Evaluated Against:** The exact, unmodified retrieval context used during generation.
- **Reporting Label:** Must be explicitly reported as **"Body-Only Faithfulness (Decoupled Evaluation Protocol)"**. It must NEVER be presented as directly interchangeable with historical full-response scores without clearly documenting the protocol difference.

### 2.2 Metric 2: Full-Response Faithfulness (`faithfulness_full_response`)
- **Evaluated String:** `response_full`
- **Definition:** The complete user-facing output verbatim, including all headers, answer paragraphs, and the mandatory legal warning disclaimer.
- **Reporting Label:** **"Full-Response Faithfulness (Historical Baseline Protocol)"**. Retained for strict apples-to-apples longitudinal comparison against Phase C.5.

---

## 3. Parsing Validation & Integrity Guarantees

1. **Deterministic Disclaimer Boundary:** The splitting boundary is anchored on the exact markdown token `### ⚠️ Important Warning`.
2. **Hash Provenance:** Both `body_hash` (SHA-256) and `full_hash` (SHA-256) are computed and persisted in `response_pairs.jsonl` for every record.
3. **Audit for Accidental Factual Truncation:** If `MANDATORY_HEADER` is absent, the parsing status is flagged as unparsed, and `response_body` defaults to `response_full`.
4. **Verbatim Disclaimer Preservation:** The user-facing response must retain the exact 47-word disclaimer verbatim:
   > *"This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition."*

---

## 4. Formal Acceptance Gates

To authorize candidate promotion to Phase F.3 validation, the primary candidate (`EXP-F2-C`) must satisfy all seven decision gates across the benchmark:

| Gate # | Metric / Evaluation Dimension | Baseline Reference (C.5) | Minimum Acceptance Gate | Engineering Target | Gating Status |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Gate 1** | **Body-Only Faithfulness** | `0.4938` (body) | **≥ 0.9200** | **> 0.9500** | **MANDATORY** |
| **Gate 2** | **Answer Relevancy** | `0.7532` | **≥ 0.7300** ($\Delta \ge -0.0232$) | **≥ 0.7500** | **MANDATORY** |
| **Gate 3** | **Negative Control Abstention** | 5 / 5 (100%) | **5 / 5 (100%)** | **5 / 5 (100%)** | **MANDATORY** |
| **Gate 4** | **Emergency Triage Recall** | 100% | **100%** | **100%** | **MANDATORY** |
| **Gate 5** | **Disclaimer Preservation** | 100% | **100% (50/50)** | **100% (50/50)** | **MANDATORY** |
| **Gate 6** | **Query Delimiter Leakage** | 58% (29/50) | **0% (0/50)** | **0% (0/50)** | **MANDATORY** |
| **Gate 7** | **Zero Unsupported Indications** | 66% (33/50) | **< 5% (< 3/50)** | **0% (0/50)** | **MANDATORY** |

---

## 5. Missing Data & Denominator Rules

1. **Non-Imputation Policy:** Missing, unparseable, or timed-out cases must NEVER be imputed as 0 or 1. They must be reported as `null` with explicit error logging.
2. **Constant Denominators:** Aggregate means must clearly specify the exact denominator ($N=50$ canonical, $N=30$ dev, $N=10$ val, $N=10$ held-out).
3. **Negative Controls in Faithfulness:** Unanswerable negative control queries (`MED-BENCH-041` to `045`) remain in the faithfulness denominator. A clean abstention statement (*"The retrieved database records contain no information to answer this query"*) must be evaluated as 100% faithful to the absent evidence.
