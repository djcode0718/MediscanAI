# Phase C.5 — Ragas Metric Contract & Eligibility Specification

**Phase:** C.5 (Paired Ragas Evaluation of Baseline vs Graph-Assisted Responses)  
**Evaluator Framework:** Ragas `0.2.15`  
**Judge Model:** `llama3.1:8b` via local Ollama (`http://localhost:11434`, greedy `temperature=0.0`)  
**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (`local_files_only=True`)  
**Reference Dataset:** `evaluation/benchmark/narrative_references/reference_answers.jsonl` (Phase C.1.2)  
**Date:** 2026-10-15  

---

## 1. Experimental Objective & Governance

This contract governs the comparative Ragas evaluation between frozen baseline hybrid retrieval and frozen graph-assisted retrieval generated in Phase C.4 across MediScanAI's 50 canonical benchmark queries.

### Fundamental Scientific Ground Rules:
1. **Frozen Experimental Inputs:** Evaluates the 100 immutable Phase C.4 generation runs and their corresponding retrieved contexts. No regeneration or prompt alteration is permitted.
2. **Explicit Reference Provenance:** Reference answers are AI-assisted research summaries verified against external medical literature in Phase C.1.1 (`human_reviewed=False`, `clinical_reviewed=False`, `official_human_gold=False`). They are NOT clinical gold standards.
3. **Strict Gold Isolation:** `evaluation/benchmark/gold_judgments.jsonl` remains 0 bytes; no gold labels are fabricated or assumed.
4. **Self-Evaluation Bias Disclosure:** Because `llama3.1:8b` generated the responses and also judges them, scores reflect internal model consistency rather than independent clinical truth.
5. **Deterministic Denominators:** Denominators for each metric are formally fixed by eligibility rules. Ineligible cases receive explicit null values with documented reasons—no cases are silently dropped.

---

## 2. Implemented Metric Specifications

### 2.1 Track A — Core Metric Matrix

| Metric Name | Ragas Class | Required Schema Fields | Judge | Embeddings | Reference Required? | Eligible Sample Size (Paired) | Ineligible Policy |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Faithfulness** | `ragas.metrics.faithfulness` | `user_input`, `response`, `retrieved_contexts` | `llama3.1:8b` | None | No | **50 / 50 pairs** (100 runs) | None (All cases eligible) |
| **Answer Relevancy** | `ragas.metrics.answer_relevancy` | `user_input`, `response` | `llama3.1:8b` | `all-MiniLM-L6-v2` | No | **50 / 50 pairs** (100 runs) | None (All cases eligible) |
| **Context Precision** | `ragas.metrics.context_precision` | `user_input`, `reference`, `retrieved_contexts` | `llama3.1:8b` | None | Yes | **45 / 50 pairs** (90 runs) | 5 negative controls marked `ineligible_unanswerable_negative_control` |
| **Context Recall** | `ragas.metrics.context_recall` | `user_input`, `reference`, `retrieved_contexts` | `llama3.1:8b` | None | Yes | **45 / 50 pairs** (90 runs) | 5 negative controls marked `ineligible_unanswerable_negative_control` |

---

## 3. Operational Metric Definitions & Eligibility Rules

### 3.1 Faithfulness (`faithfulness`)
- **Definition:** Quantifies whether the factual assertions made in the generated answer are strictly grounded in the retrieved context provided for that generation.
- **Operational Process:**
  1. The LLM judge extracts discrete factual propositions from the generated `response`.
  2. Each proposition is verified against the concatenated `retrieved_contexts` to yield binary support decisions ($1 = \text{grounded}, 0 = \text{ungrounded}$).
  3. $\text{Score} = \frac{\sum \text{supported statements}}{\text{total statements}}$.
- **Eligibility:** 100% of benchmark cases (50/50 pairs).
- **Caveat:** Evaluates evidence fidelity, not clinical validity. If retrieved text contains an error, reproducing that error scores high on faithfulness.

### 3.2 Answer Relevancy (`answer_relevancy`)
- **Definition:** Measures how directly and specifically the answer addresses the user's clinical or pharmacological question, penalizing evasion, repetition, or irrelevant digression.
- **Operational Process:**
  1. The LLM judge synthesizes $N$ reverse questions that the generated `response` answers.
  2. The synthetic questions and the original `user_input` are encoded using `all-MiniLM-L6-v2`.
  3. Score is the mean cosine similarity between the embeddings of the synthetic queries and the user query.
- **Eligibility:** 100% of benchmark cases (50/50 pairs).
- **Caveat:** Independent of factual correctness. A fluent, highly relevant hallucination can achieve a score of 1.0.

### 3.3 Context Precision (`context_precision`)
- **Definition:** Evaluates whether retrieved evidence chunks relevant to arriving at the reference answer are ranked preferentially at the top of the context list.
- **Operational Process:**
  - For each ranked chunk in `retrieved_contexts`, the LLM judge determines if the chunk is useful for constructing the `reference` answer.
  - Mean Average Precision (MAP) is computed over the ranked chunks.
- **Eligibility:** 45/50 cases.
  - **Eligible:** `answerable` (20), `answerable_with_caveat` (21), `ambiguous` (4).
  - **Ineligible (5 cases):** `unanswerable` negative controls (`MED-BENCH-041` through `MED-BENCH-045`). These cases query fictional or unsupported clinical assertions; measuring retrieval precision against an unanswerable prompt without valid target chunks is methodologically invalid. Ineligible cases are recorded as `null` with reason `ineligible_unanswerable_negative_control`.

### 3.4 Context Recall (`context_recall`)
- **Definition:** Evaluates whether the retrieved context contains all key factual elements documented in the reference answer.
- **Operational Process:**
  1. The LLM judge segments the `reference` answer into essential factual claims.
  2. Each claim is checked against the retrieved evidence ($1 = \text{present}, 0 = \text{absent}$).
  3. $\text{Score} = \frac{\sum \text{supported reference claims}}{\text{total reference claims}}$.
- **Eligibility:** 45/50 cases (identical to Context Precision).
  - Ineligible cases (`MED-BENCH-041` through `MED-BENCH-045`) are recorded as `null` with reason `ineligible_unanswerable_negative_control`.

---

## 4. Paired Delta & Uncertainty Methodology

For each metric $m$ on eligible case $i$:
$$\Delta_i = \text{Score}_{i, \text{graph\_assisted}} - \text{Score}_{i, \text{baseline}}$$

- **Aggregate Metrics:**
  - Mean baseline score ($\bar{X}_{\text{base}}$) and mean graph score ($\bar{X}_{\text{graph}}$).
  - Mean paired difference ($\bar{\Delta} = \frac{1}{N}\sum \Delta_i$).
  - Median paired difference ($\text{median}(\Delta_i)$).
  - Categorical outcomes:
    - **Improved:** $\Delta_i > +0.01$
    - **Unchanged:** $|\Delta_i| \le 0.01$
    - **Regressed:** $\Delta_i < -0.01$
- **Uncertainty Estimation:**
  - 95% Bootstrap Confidence Interval for $\bar{\Delta}$ computed using 1,000 paired case-level resamples (`random_seed=42`).
  - Wilcoxon signed-rank test for paired non-parametric difference with exact p-value reporting.
  - No claim of statistical superiority will be made without confidence bounds excluding zero and appropriate caveat on sample size ($N=50$).

---

## 5. Judge Failure & Retry Policy

1. **Deterministic Parameters:** Judge runs with `temperature=0.0`.
2. **Bounded Retry:** If Ollama returns a transient error or malformed JSON, the runner retries up to 2 times with a 5-second backoff.
3. **Explicit Failure Accounting:** If all retries fail, a `null` score is stored, the error is recorded in `metric_failures.jsonl`, and the failure count is tallied in the aggregate report. No scores are replaced with arbitrary defaults (e.g., 0.0 or 1.0).
