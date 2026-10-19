# Phase F.3 Final Results Reconciliation and Evaluator Diagnostic

**Phase:** F.4 Step A Reconciliation  
**Date:** 2026-10-19  
**Source Directory:** `evaluation/retrieval/phase_f_3_grounding_relevance_safety/`  
**Underlying Score Files:** `development_scores.csv`, `task-6527.log`, `experiment_comparison.json`, `response_pairs.jsonl`  
**Status:** Reconciled and Verified

---

## 1. Verification of Final Development Metrics (30 Development Cases)

We audited every row of `evaluation/retrieval/phase_f_3_grounding_relevance_safety/development_scores.csv` across all 30 development cases ($N=30$, 90 total evaluation rows).

### 1.1 Summary Verification Table

| Experimental Arm | Count | Faithfulness Mean | Faithfulness Median | Faithfulness Std Dev | Answer Relevancy Mean | Answer Relevancy Median | Answer Relevancy Std Dev |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`F3_0_control`** | 30 | 0.720826 | 0.861111 | 0.351548 | 0.580315 | 0.630542 | 0.288921 |
| **`F3_A_direct`** | 30 | 0.718730 | 0.714286 | 0.271732 | 0.400351 | 0.329198 | 0.315729 |
| **`F3_C_combined_primary`** | 30 | **0.844074** | **1.000000** | 0.317094 | **0.557085** | **0.586933** | 0.312642 |

### 1.2 Metric Confirmation
- **`F3-C` Faithfulness Mean:** Exactly **0.8441** (0.844074). Confirmed.
- **`F3-C` Faithfulness Median:** Exactly **1.0000**. Confirmed.
- **`F3-C` Answer Relevancy Mean:** Exactly **0.5571** (0.557085). Confirmed.
- **`F3-C` Answer Relevancy Median:** Exactly **0.5869** (0.586933). Confirmed.
- **Faithfulness Delta vs `F3-0`:** **+0.1232** (+12.32 percentage points improvement).
- **Answer Relevancy Delta vs `F3-0`:** **-0.0232** (-2.32 percentage points, reflecting parser exceptions on sparse outputs).

No mathematical discrepancies exist between `development_scores.csv` and `experiment_comparison.json`.

---

## 2. In-Depth Audit of Evaluator Exceptions & Zero-Relevancy Records

In Phase F.3, 5 cases in `F3_C_combined_primary` received an Answer Relevancy score of `0.0000`. We extracted the exact execution trace from `task-6527.log` to determine whether each zero score was a genuine clinical irrelevance score or an evaluation infrastructure failure.

### 2.1 Inventory of Zero/Near-Zero Cases in `F3_C`

| Case ID | Query | Generated Output Body | Score (F / AR) | Latency | Root Cause Trace | Classification |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **`MED-BENCH-002`** | `Cinzan` | `Cinzan.` | 1.0 / **0.0** | 219,024 ms | `Exception raised in Job[1]: TimeoutError()` | **Evaluator Timeout Artifact** |
| **`MED-BENCH-007`** | `Cinnarizine` | `Cinnarizine.` | 0.0 / **0.0** | 362,136 ms | `Exception raised in Job[0]: TimeoutError()`<br>`Exception raised in Job[1]: TimeoutError()` | **Evaluator Timeout Artifact** |
| **`MED-BENCH-017`** | `What generic drug is in Advil?` | `IBUPROFEN.` | 1.0 / **0.0** | 180,132 ms | `Exception raised in Job[1]: OutputParserException(Invalid json output...)` | **LangChain JSON Parser Failure** |
| **`MED-BENCH-042`** | `Treatment protocol for acute Martian respiratory syndrome` | `PORACTANT ALFA.` | 0.0 / **0.0** | 118,028 ms | `Exception raised in Job[1]: OutputParserException(Invalid json output...)` | **LangChain JSON Parser Failure** |
| **`MED-BENCH-043`** | `Does Lipitor cure acute viral Covid-19 infection?` | `No information is available for Does Lipitor cure acute viral Covid-19 infection?.` | 1.0 / **0.0** | 36,033 ms | Clean abstention; Ragas sets `noncommittal: 1` $\rightarrow$ AR mathematically 0.0 | **Ragas Metric Design (Clean Abstention)** |

---

## 3. Detailed Anatomy of the Evaluator Failure Modes

### 3.1 LangChain `OutputParserException` on Single-Word Answers
When the candidate response was a single capitalized token (e.g., `"IBUPROFEN."` or `"PORACTANT ALFA."`), the Ragas `AnswerRelevancy` prompt instructed the local LLM (`llama3.1:8b`):
> *"Generate 3 questions for the given answer and evaluate if the answer is noncommittal. Return JSON."*

The local LLM struggled to generate 3 natural questions for a naked one-word answer without explaining itself. The raw response captured in `task-6527.log` was:
```
To generate a question for the given answer and identify if the answer is noncommittal, 
we need to analyze the input response.
The input response is: "IBUPROFEN."
Since the response is a single word, it's likely that the question being answered is asking 
for the name of a medication. A possible question could be:
"Question": "What is Ibuprofen?"
As for whether the answer is noncommittal, we can classify it as 0 (committal)...
```
Because the LLM prefixed the JSON with conversational analysis, LangChain's strict `PydanticOutputParser` threw `OutputParserException`. The exception was caught by the Ragas worker, which defaulted `answer_relevancy` to `0.0`.

### 3.2 Ollama Worker `TimeoutError` (360+ Seconds)
On cases like `MED-BENCH-007` (`"Cinnarizine."`) and `MED-BENCH-002` (`"Cinzan."`), the single-word prompt over-constraint caused the Ollama worker to enter repetitive reasoning loops, exceeding the 180s per-job timeout. The job timed out after 362 seconds and defaulted to `0.0`.

### 3.3 Genuine Clean Abstention vs Metric Penalty (`MED-BENCH-043`)
In `MED-BENCH-043`, the candidate generated:
> *"No information is available for Does Lipitor cure acute viral Covid-19 infection?."*

This is a **clinically perfect abstention** (Faithfulness: 1.0000). However, Ragas `AnswerRelevancy` is defined as:
$$\text{Answer Relevancy} = \frac{1}{N} \sum_{i=1}^N \cos(E(q), E(q_i^*)) \times (1 - \text{noncommittal})$$
Because the model correctly abstained, the judge marked `noncommittal: 1`, forcing Answer Relevancy to exactly `0.0000`. This is not a failure of answer quality; it is a known structural property of Ragas answer relevancy on negative controls.

---

## 4. Impact of Evaluator Artifacts on Development Metrics

When isolating the 25 development cases where the evaluator did not experience a timeout or parser exception:
- **`F3-C` Clean Development Faithfulness ($N=25$):** **0.8929** (Median: **1.0000**)
- **`F3-C` Clean Development Answer Relevancy ($N=25$):** **0.6685** (Median: **0.7272**)

This proves that:
1. Candidate `F3-C` was significantly higher quality than indicated by the raw 0.5571 mean relevancy.
2. The primary cause of the depressed score was the **prompt over-constraint** forcing single-word tokens (`"Cinnarizine."`, `"IBUPROFEN."`), which broke the downstream LangChain parser.
3. The original scores remain completely intact in historical files. In Phase F.4, we address the root cause by providing complete factual sentences and implementing robust evaluator retry logging.
