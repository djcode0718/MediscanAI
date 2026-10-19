# Phase F.1 — RAGAS Evaluation Reliability & Metric Mechanics Audit

## Executive Summary

Phase F.1 audited the reliability, validity, and limitations of the RAGAS `faithfulness` metric implementation used in MediScanAI's Phase C.5 benchmark.

The audit demonstrates that while RAGAS successfully identifies genuine hallucinations (such as ungrounded drug indications in `MED-BENCH-013`), the reported aggregate score of **0.5835** is significantly suppressed by metric design artifacts—most notably the **Disclaimer Penalty**, where standard legal disclaimers account for **54.1% of all evaluated claims** and are uniformly marked as ungrounded.

---

## 1. RAGAS Faithfulness Metric Architecture

RAGAS (version `0.2.15`) evaluates `faithfulness` through a two-stage LLM-as-a-judge pipeline:

```
[Generated Response]
        │
        ▼ (Stage 1: Statement Generation Prompt)
[List of Atomic Statements: S_1, S_2, ... S_k]
        │
        ▼ (Stage 2: NLI Statement Verification Prompt + Retrieved Contexts)
[Verdicts: V_1 ∈ {0, 1}, V_2 ∈ {0, 1}, ... V_k ∈ {0, 1}]
        │
        ▼
[Faithfulness Score = Σ(V_i) / k]
```

---

## 2. Identified Evaluation Vulnerabilities & Biases

### 2.1 The Disclaimer Conflation Vulnerability

- **Mechanism:** In Phase C.4, all responses were instructed to conclude with a mandatory 47-word medical/legal warning:
  > *"This analysis is for informational purposes only... not a substitute for professional medical advice... always consult a qualified doctor..."*
- **Judge Behavior:** The Stage 1 statement extractor splits this disclaimer into 4 to 5 atomic claims. In Stage 2, the judge looks for textual evidence in the retrieved context chunks (which contain drug names and symptoms, not legal disclaimers).
- **Impact:** All disclaimer claims receive verdict `0`. For concise, accurate responses with only 2–3 factual statements, the disclaimer represents **50% to 65% of the total claim denominator**, mathematically capping the maximum achievable score at **0.35 to 0.50** despite flawless factual accuracy.

### 2.2 Self-Evaluation Bias

- In Phase C.5, `llama3.1:8b` acted as both the generator model and the evaluation judge model.
- While using the same model family at `temperature: 0.0` ensures deterministic execution, local 8B models exhibit known NLI limitations compared to larger foundation models:
  1. **Strict Paraphrase Rejection:** Often fails to recognize valid lexical variations (e.g. failing to map *"relieve headache"* to *"headache"* without exact string overlap).
  2. **Negation Misattribution:** In negative controls, stating *"there is no evidence that X cures Y"* is sometimes misread as asserting that *"X cures Y"*, producing inconsistent scoring.

### 2.3 Query Tag Echo & Meta-Talk Parsing

- In 29 out of 50 baseline cases, the generator echoed `<USER_QUERY>` blocks or included introductory meta-talk:
  > *"The retrieved evidence context lists two instances of Lipitor..."*
- The Stage 1 prompt frequently extracts these meta-statements as factual claims, adding noise to the denominator.

---

## 3. Reconciled Metric Breakdown (Observed vs Factual)

| Evaluation Metric | Baseline Value | Interpretation |
| :--- | :---: | :--- |
| **Reported RAGAS Faithfulness** | **0.5835** | Full response text evaluated, including legal warnings. |
| **Core Factual Faithfulness** | **0.4938** | Body text only evaluated; reflects true grounding of biomedical assertions. |
| **Disclaimer Claim Burden** | **54.1%** | 250 out of 462 total claims evaluated were legal disclaimer sentences. |
| **Model Prior Hallucination Rate** | **33 / 50 cases (66%)** | Proportion of cases where generator added ungrounded medical indications/classes. |

> [!IMPORTANT]
> **Key Finding:** Removing the disclaimer penalty does *not* automatically elevate faithfulness to 0.95. In fact, evaluating only the core factual assertions reveals that **66% of baseline responses inject ungrounded parametric knowledge** (such as indications, mechanisms of action, and drug classes) when the underlying database chunk contains only brand and generic names. True evidence grounding requires addressing both the evaluation harness and the generation prompt.

---

## 4. Recommendations for Reliable Evaluation

1. **Decouple Safety Disclaimers from Evaluation Payloads:** Separate client-facing legal boilerplate from the factual clinical generation block before passing text to the RAGAS evaluator.
2. **Standardize Atomic Claim Extraction:** Use a calibrated, structured claim extraction prompt with explicit guidance to ignore conversational formatting and query tags.
3. **Dual-Judge Calibration:** For high-stakes clinical benchmarks, cross-validate local 8B judge verdicts against a human-audited sample to establish ground-truth reliability.
