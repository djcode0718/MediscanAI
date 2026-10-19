# Phase F.1 — Controlled Experiment Priority Matrix

## Executive Summary

To achieve the engineering objective of improving RAGAS Faithfulness from **0.5835** to **> 0.9500** through genuine evidence grounding, candidate interventions were evaluated and prioritized across four dimensions: Expected Impact, Safety & Clinical Risk, Implementation Complexity, and Computational Cost.

---

## 1. Candidate Interventions Ranking Matrix

| Rank | Candidate Intervention | Expected Impact on Faithfulness | Clinical & Safety Risk | Complexity | Cost | Recommendation |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | **EXP-F2-A: Decouple Disclaimer from Evaluation Payload** | **+0.15 to +0.25** | Zero (Preserves client warning in UI) | Low | Zero | **Immediate Priority (Step 1)** |
| **2** | **EXP-F2-B: Strict Evidence-Only Grounding Prompt** | **+0.20 to +0.35** | Very Low (Eliminates parametric leaks) | Low | Low | **Immediate Priority (Step 2)** |
| **3** | **EXP-F2-C: Structured Claim-Level Evidence Citations** | **+0.10 to +0.15** | Low | Medium | Low | **Secondary Follow-Up** |
| **4** | **EXP-F2-D: Calibrated Abstention Contract on Low Score** | **+0.05 to +0.10** | Low (Improves negative control precision) | Medium | Low | **Secondary Follow-Up** |
| **5** | **EXP-F2-E: Context Deduplication & Noise Filtering** | **+0.03 to +0.06** | Low | Medium | Medium | **Tertiary Phase** |
| **6** | **EXP-F2-F: Independent Judge Calibration & Re-weighting** | N/A (Measurement only) | Zero | High | High | **Verification Phase** |

---

## 2. Detailed Experiment Profiles & Acceptance Gates

### Priority 1: EXP-F2-A — Disclaimer Decoupling from Evaluated Payload
- **Hypothesis:** Separating client-facing legal boilerplate from the factual medical response block before passing text to the RAGAS evaluation harness eliminates the artificial disclaimer penalty without suppressing legal disclaimers in the UI.
- **Implementation:**
  - Update evaluation adapter to evaluate `response_body` rather than `response_body + mandatory_warning`.
  - Maintain verbatim legal disclaimers in client outputs.
- **Success Criterion:**
  - Mean Faithfulness increases from `0.5835` to `≥ 0.7000`.
  - Negative control faithfulness on `MED-BENCH-041` increases from `0.1667` to `≥ 0.8000`.
- **Regression Criterion:**
  - Answer Relevancy must not drop by more than `0.0200`.

---

### Priority 2: EXP-F2-B — Strict Evidence-Only Grounding Prompt
- **Hypothesis:** 66% of baseline responses add ungrounded parametric knowledge (e.g. reciting that Paracetamol is an analgesic or Advil is an NSAID when the database records only active ingredients). A strict negative-constraint prompt instructing the model to *state only facts explicitly documented in the evidence chunks* will prevent external prior leakage.
- **System Prompt Rules:**
  1. *"Do not describe drug indications, mechanisms of action, or therapeutic classes unless explicitly written in the evidence context."*
  2. *"If a user asks what a drug treats, and the retrieved context lists only active ingredients, explicitly state: 'The database records ingredients and brand names, but does not specify indications.'"*
  3. *"Do not echo `<USER_QUERY>` blocks or format tags."*
- **Success Criterion:**
  - Core Factual Faithfulness increases from `0.4938` to `≥ 0.9000`.
  - Total Faithfulness reaches `> 0.9500` when combined with EXP-F2-A.
  - Zero ungrounded drug class or indication hallucinations across all 50 cases.
- **Regression Criterion:**
  - Answer Relevancy remains `≥ 0.7500`.
  - Negative control abstention preserved at 5/5.
  - Emergency fast-path and critical triage signals remain uncompromised.

---

### Priority 3: EXP-F2-C — Explicit Claim-Level Inline Citations
- **Hypothesis:** Requiring the generator to append bracketed citations (e.g. `[drug_58277]`) directly after every factual clause forces the attention mechanism to attend directly to source chunks and enables automated token-level verification.
- **Success Criterion:**
  - Uncited claim count drops to 0.
  - Faithfulness increases by `≥ 0.0500`.

---

## 3. Recommended Next Action: The Single Highest-Value Experiment

### Target Phase: **Phase F.2 — Grounded Prompting & Evaluation Decoupling**

Combine **EXP-F2-A** (Evaluation Harness Decoupling) and **EXP-F2-B** (Strict Grounded Prompting) into a single controlled two-arm evaluation:

| Benchmark Target | Historical Baseline (C.5) | Projected Target (F.2) | Gate Threshold for Success |
| :--- | :---: | :---: | :---: |
| **RAGAS Faithfulness** | **0.5835** | **0.9550** | **≥ 0.9200** |
| **Answer Relevancy** | `0.7532` | `0.7600` | `≥ 0.7300` |
| **Context Recall** | `0.6186` | `0.6186` | No regression |
| **Negative Control Safety** | 5/5 Abstention | 5/5 Abstention | Strictly 5/5 (100%) |
| **Emergency Triage Recall** | 100% | 100% | Strictly 100% |
