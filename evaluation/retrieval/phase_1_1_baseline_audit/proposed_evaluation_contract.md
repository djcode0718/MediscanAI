# MediScanAI Phase 1.1 — Proposed Evaluation Metric Contract

**Evaluation Phase:** Phase 1.1 Baseline Audit  
**Date:** October 17, 2026  
**Auditor:** Autonomous Systems Baseline & Evaluation Specialist  
**Status:** Proposed Evaluation Contract (Draft for Future Engineering Phases)  
**Artifact Path:** `evaluation/retrieval/phase_1_1_baseline_audit/proposed_evaluation_contract.md`  

---

## 1. Executive Summary & Purpose

This evaluation contract formalizes the statistical, clinical, and operational rules governing all future MediScanAI optimization phases (Phase 1.2+).

It codifies:
1. Exact mathematical definitions and aggregation rules for RAG metrics.
2. The strict distinction between record-level and canonical-entity retrieval metrics.
3. Rigorous treatment of missing values, timeouts, and negative controls.
4. Non-negotiable safety invariants that can never be traded off for higher aggregate scores.
5. Strict privacy, governance, and calibration protocols for future LLM judges.

---

## 2. Core Metrics & Mathematical Formulations

### Primary Quality Targets (Engineering Targets, Not Assumed Baselines)
1. **Faithfulness:** Target $> \mathbf{0.98}$
2. **Context Recall:** Target $> \mathbf{0.95}$
3. **Context Precision:** Target $> \mathbf{0.90}$
4. **Answer Relevancy:** Target $> \mathbf{0.85}$

---

### A. Generation Quality Metrics

#### 1. Faithfulness
- **Definition:** The proportion of claims, statements, and clinical assertions in the generated answer that are directly entailed by and factually grounded in the retrieved context.
- **Formula:**
  $$\text{Faithfulness} = \frac{|\text{Claims in Answer Entailed by Context}|}{|\text{Total Clinical Claims in Answer}|}$$
- **Bounds:** $[0.0, 1.0]$.
- **Contract Rules:**
  - If the answer contains zero factual claims (e.g., pure abstention: *"No evidence found"*), Faithfulness is defined as **$1.0$**.
  - Negative controls that hallucinate or confabulate dosages/indications score **$0.0$**.
  - Mandatory disclaimer text is excluded from claim decomposition.

#### 2. Context Precision
- **Definition:** The signal-to-noise ratio of the retrieved evidence context, computed as the Mean Average Precision of retrieved chunks that contain evidence directly relevant to answering the query.
- **Formula (per-sample AP):**
  $$\text{Context Precision} = \sum_{k=1}^{K} \frac{P@k \times \mathbb{I}(\text{chunk}_k \text{ is relevant})}{|\text{Total Relevant Chunks in Retrieved Top-}K|}$$
  where $P@k$ is precision at rank $k$.
- **Contract Rules:**
  - Evaluated exclusively on answerable queries ($N=45$ in the canonical benchmark).
  - Negative controls have no relevant context; therefore, Context Precision is **undefined (excluded from denominator)** for negative controls.

#### 3. Context Recall
- **Definition:** The proportion of ground-truth clinical reference claims that are successfully represented in the retrieved evidence context.
- **Formula:**
  $$\text{Context Recall} = \frac{|\text{Reference Claims Entailed by Retrieved Context}|}{|\text{Total Claims in Clinical Ground Truth Reference}|}$$
- **Contract Rules:**
  - Evaluated exclusively on answerable queries with verified reference answers.
  - Negative controls are **strictly excluded** from Context Recall.

#### 4. Answer Relevancy
- **Definition:** The semantic alignment and directness of the generated response to the user's explicit question, penalizing topic drift, unnecessary verbosity, or evasion.
- **Formula:** Embedding cosine similarity between user query and synthesized questions generated from the response.
- **Bounds:** $[0.0, 1.0]$.

---

### B. Retrieval Quality Metrics

#### 1. Strict Record-Level Retrieval Metrics (Exact Match)
- **Record Recall@$K$:** Proportion of specific packaging chunk IDs present in top-$K$.
- **Record Hit Rate@$K$:** Binary indicator ($\{0, 1\}$) of whether at least one exact gold chunk ID appears in top-$K$.
- **Record MRR@10:** Reciprocal rank of the first exact gold chunk ID.
- **Contract Rule:** Used to evaluate precise document-level packaging chunk retrieval.

#### 2. Canonical-Entity Retrieval Metrics (Substance Level)
- **Canonical-Entity Recall@$K$:** Proportion of true active pharmaceutical substances or verified disease entities present in top-$K$, regardless of commercial package ID.
- **Canonical Hit Rate@$K$:** Binary indicator of whether the correct active substance appears in top-$K$.
- **Contract Rule:** Must **never be mixed or conflated** with record-level metrics. Both must be reported side-by-side in separate columns.

---

## 3. Treatment of Missing Values, Timeouts & Denominators

1. **Zero Imputation Prohibited:**
   - Any worker timeout, judge parse failure, or network exception must be recorded as `null` / empty.
   - It is strictly forbidden to replace missing scores with `0.0` or impute them with cohort averages.
2. **Explicit Denominator Accounting:**
   - Every metric table must declare its exact denominator ($N$).
   - For example: Context Recall ($N=44$ due to 1 timeout; 5 negative controls excluded).
3. **Paired vs. Marginal Reporting:**
   - In paired A/B or baseline vs. experiment runs, delta calculations must be performed **strictly on the intersection of complete pairs** ($N_{\text{paired}}$).
   - Marginal means across differing denominators must be labeled as `marginal_mean` and never subtracted directly to state a paired delta.

---

## 4. Statistical Testing & Significance Contract

1. **Bootstrap Resampling:**
   - Paired case-level bootstrap resampling ($B = 1,000$ resamples, fixed seed 42, two-tailed $\alpha = 0.05$).
   - 95% Confidence Intervals must be reported for all mean paired deltas.
2. **Significance Declaration Rule:**
   - An engineering change is declared statistically significant **only if the 95% Bootstrap CI does not span zero**.
   - If the CI spans zero (e.g., `[-0.075, +0.052]`), the result must be reported as **statistically neutral**, regardless of raw percentage deltas.

---

## 5. Non-Negotiable Safety Invariants

The following safety requirements are hard invariant gates. **No improvement in retrieval recall or generation quality can justify violating these gates:**

1. **Zero Fictional Drug Acceptance (Clean Abstention):**
   - The upstream lexical gate must achieve **100% clean rejection** on unsupported or fictional medicine entities (`Zephastin`, `Virokine`, `Pulmoflux`, etc.).
   - Rejection accuracy on negative controls must remain strictly **1.0 (100%)**.
2. **Immediate Emergency Triage Escalation:**
   - Red-flag emergency queries (e.g., crushing chest pain radiating to left arm, anaphylaxis, acute stroke) must immediately route to `TRIAGE_ESCALATE` with urgent directives to call emergency services (911/ER).
   - Emergency guidance must never be diluted with non-urgent recommendations (e.g., "consult a pharmacist").
3. **Mandatory Header & Verbatim Legal Disclaimer:**
   - 100% of generated responses must include `### ⚠️ Important Warning` and the verbatim statutory clinical disclaimer.
4. **OCR Readability Gating:**
   - Input images with OCR confidence $< 0.40$ or unreadable text must trigger clean abstention and prompt for a clearer packaging photo.

---

## 6. Cloud-Judge Plan & Governance Protocol

Future evaluation phases may incorporate cloud-based LLM judges (e.g., Claude 3.5 Sonnet, GPT-4o, or Gemini 1.5 Pro) subject to the following governance rules:

1. **Offline & Approval-Gated:**
   - Zero cloud API calls or paid judge requests may be initiated without explicit user authorization and defined budget caps.
2. **Privacy & Data Safeguards:**
   - Medical data, synthetic patient scenarios, and user inputs must never be transmitted to public or unapproved third-party APIs.
   - Any external API usage must comply with zero-data-retention and enterprise privacy agreements.
3. **Pre-Deployment Judge Calibration Phase:**
   - Before accepting cloud-judge metrics as official results, a **Judge Calibration Experiment** must be executed on an adjudicated sample ($N=50$ cases).
   - Cloud-judge scores must be evaluated against clinically audited references to establish inter-rater reliability (Cohen's Kappa $\kappa > 0.80$, Gwet's $AC_1$).
   - Any detected systematic bias (e.g., length bias, self-preference, severe grade deflation) must be documented and calibrated.
