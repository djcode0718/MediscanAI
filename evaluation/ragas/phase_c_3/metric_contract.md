# Phase C.3 — Ragas Metric Contract & Eligibility Specification

**Document Version:** 1.0.0  
**Phase:** C.3 (Ragas Infrastructure Setup)  
**Target Ragas Version:** `0.2.15`  
**Dataset Format:** HuggingFace `Dataset` / Ragas `EvaluationDataset`  
**Date:** 2026-10-15  

---

## 1. Overview & Principles

This metric contract formally defines the input schemas, computational dependencies, reference requirements, and validity boundaries for all candidate Ragas metrics targeted for MediScanAI's upcoming paired RAG evaluation (Phase C.4).

### Cardinal Scientific Principles:
1. **Traceable Grounding:** Reference answers are source-backed AI-assisted research references (`human_reviewed=False`, `clinical_reviewed=False`). No metric output shall be claimed as clinical ground truth.
2. **Explicit Input Contracts:** Metrics are enabled only if their required dataset columns are fully satisfied by MediScanAI's data pipeline.
3. **Deterministic Separation:** Evaluated answers from baseline hybrid search (`track="baseline"`) and Neo4j graph search (`track="graph"`) are evaluated independently.
4. **Empty Gold Integrity:** `evaluation/benchmark/gold_judgments.jsonl` remains 0 bytes; human gold labels are never simulated or assumed.

---

## 2. Metric Eligibility Matrix

| Metric Name | Ragas Class / Import | Required Columns | LLM Judge? | Embeddings? | Reference Required? | Eligibility Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Faithfulness** | `ragas.metrics.faithfulness` | `user_input`, `retrieved_contexts`, `response` | Yes | No | No | **ENABLED** |
| **Answer Relevancy** | `ragas.metrics.answer_relevancy` | `user_input`, `response` | Yes | Yes | No | **ENABLED** |
| **Context Precision** | `ragas.metrics.context_precision` | `user_input`, `reference`, `retrieved_contexts` | Yes | No | Yes (Reference answer) | **ENABLED (Reference-Guided)** |
| **Context Recall** | `ragas.metrics.context_recall` | `user_input`, `reference`, `retrieved_contexts` | Yes | No | Yes (Reference answer) | **ENABLED (Research Track)** |
| **Answer Correctness** | `ragas.metrics.answer_correctness` | `user_input`, `response`, `reference` | Yes | Yes | Yes (Reference answer) | **ENABLED (Research Track)** |
| **Context Entity Recall** | `ragas.metrics.context_entity_recall` | `retrieved_contexts`, `reference_contexts` | Yes | No | Yes (`reference_contexts`) | **BLOCKED** (Lacks formal reference chunk text) |
| **Harmfulness / Toxicity** | `ragas.metrics.critique.harmfulness` | `user_input`, `response` | Yes | No | No | **EXPLORATORY** (Clinical safety rubric preferred) |

---

## 3. Detailed Specification per Enabled Metric

### A. Faithfulness (`ragas.metrics.faithfulness`)
- **API Call:** `from ragas.metrics import faithfulness`
- **Definition:** Evaluates the degree to which claims in the generated response can be directly inferred from the provided `retrieved_contexts`.
- **Operational Mechanism:**
  1. Breaks the generated `response` into discrete factual statements via LLM prompt.
  2. Evaluates each statement against the concatenated `retrieved_contexts` to assign binary verdicts ($1 = \text{supported}, 0 = \text{unsupported}$).
  3. Score = $\frac{\sum \text{supported statements}}{\text{total statements}}$.
- **Required Inputs:** `user_input` (str), `retrieved_contexts` (list[str]), `response` (str).
- **Backend Dependencies:** LLM Judge (`llama3.1:8b`). Embeddings not required.
- **Validity Limitations:**
  - Evaluates context consistency, not objective medical truth. If retrieved context contains a medical error, a faithful response reproducing that error receives a high score.
  - Requires judge to output strict integer verdicts ($0$ or $1$); models outputting float verdicts cause Pydantic validation failures.
- **Status:** **ENABLED (Core Primary Metric)**.

---

### B. Answer Relevancy (`ragas.metrics.answer_relevancy`)
- **API Call:** `from ragas.metrics import answer_relevancy`
- **Definition:** Measures how pertinent the generated response is to the query, penalizing incomplete, evasive, or repetitive answers.
- **Operational Mechanism:**
  1. Prompts LLM judge to generate $N$ synthetic questions that the generated `response` would answer.
  2. Embeds the synthetic questions and the original `user_input` using the embedding model (`all-MiniLM-L6-v2`).
  3. Computes the mean cosine similarity between the embeddings of the synthetic questions and the original query.
- **Required Inputs:** `user_input` (str), `response` (str).
- **Backend Dependencies:** LLM Judge (`llama3.1:8b`) AND Embedding Model (`all-MiniLM-L6-v2`).
- **Validity Limitations:**
  - Highly dependent on embedding model quality. Relevancy does not measure factual correctness; a beautifully relevant answer that is completely ungrounded can score $1.0$.
- **Status:** **ENABLED (Core Primary Metric)**.

---

### C. Context Precision (`ragas.metrics.context_precision`)
- **API Call:** `from ragas.metrics import context_precision`
- **Definition:** Evaluates whether relevant information in the `retrieved_contexts` is ranked higher than irrelevant information, using the reference answer as the guide for relevance.
- **Operational Mechanism:**
  - For each retrieved chunk in `retrieved_contexts`, prompts LLM judge to determine whether it is useful in arriving at the `reference` answer.
  - Computes Mean Average Precision (MAP) over the ranked chunks.
- **Required Inputs:** `user_input` (str), `reference` (str), `retrieved_contexts` (list[str]).
- **Backend Dependencies:** LLM Judge (`llama3.1:8b`). Embeddings not required.
- **Validity Limitations:**
  - This is an LLM-based reference-guided precision metric. It is distinct from Phase B deterministic source-ID `Precision@K`. It measures whether the LLM judge perceives the text chunk as helpful to the reference.
- **Status:** **ENABLED (Reference-Guided Track)**.

---

### D. Context Recall (`ragas.metrics.context_recall`)
- **API Call:** `from ragas.metrics import context_recall`
- **Definition:** Evaluates whether the retrieved context contains all the necessary factual claims required to construct the `reference` answer.
- **Operational Mechanism:**
  1. Deconstructs the `reference` answer into discrete key factual claims.
  2. Checks each reference claim against `retrieved_contexts` ($1 = \text{found in context}, 0 = \text{missing}$).
  3. Score = $\frac{\sum \text{supported reference claims}}{\text{total reference claims}}$.
- **Required Inputs:** `user_input` (str), `reference` (str), `retrieved_contexts` (list[str]).
- **Backend Dependencies:** LLM Judge (`llama3.1:8b`). Embeddings not required.
- **Validity Limitations:**
  - Evaluated against AI-assisted research reference answers (`reference_answers.jsonl`). Does not represent human clinical gold coverage.
  - Negative controls (`MED-BENCH-041` through `MED-BENCH-045`) have empty reference evidence expectations; Context Recall must be interpreted conditionally for unanswerable queries.
- **Status:** **ENABLED (Research Track)**.

---

### E. Answer Correctness (`ragas.metrics.answer_correctness`)
- **API Call:** `from ragas.metrics import answer_correctness`
- **Definition:** Evaluates the factual and semantic accuracy of the generated `response` in comparison to the `reference` answer.
- **Operational Mechanism:**
  - Combines factual correctness (F1 score of supported claims via LLM classification into TP, FP, FN) and semantic similarity (cosine similarity between response and reference embeddings).
  - Default weighting: $0.75 \times \text{factual F1} + 0.25 \times \text{semantic similarity}$.
- **Required Inputs:** `user_input` (str), `response` (str), `reference` (str).
- **Backend Dependencies:** LLM Judge (`llama3.1:8b`) AND Embedding Model (`all-MiniLM-L6-v2`).
- **Validity Limitations:**
  - Measures alignment with the research reference answers. Reference-based correctness is a research metric, not clinical verification.
- **Status:** **ENABLED (Research Track)**.

---

## 4. Blocked & Excluded Metrics

1. **Context Entity Recall (`ragas.metrics.context_entity_recall`):**
   - *Status:* **BLOCKED**.
   - *Rationale:* Requires fine-grained reference entity sets or chunked reference contexts (`reference_contexts`), which are not part of the active benchmark reference schema.
2. **Gold Label Retrieval Metrics (Recall@K, MRR, nDCG via Ragas):**
   - *Status:* **BLOCKED in Ragas**.
   - *Rationale:* Deterministic retrieval evaluation is already executed with mathematical precision via Phase B's verified metric engine (`evaluation/retrieval/metrics.py`). LLM-based estimation of retrieval metrics is redundant and mathematically inferior to source-ID matching.
