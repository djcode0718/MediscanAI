# Phase F.3 — Evaluation Reliability and Metric Sensitivity Audit

## Executive Summary

This audit assesses the measurement reliability, failure modes, and sensitivity profiles of the automated evaluation stack used in MediScanAI's Phase F experiments. It specifically evaluates the behavior of RAGAS `faithfulness` and `answer_relevancy` when executed against local models (`llama3.1:8b` via Ollama and `all-MiniLM-L6-v2` embeddings), analyzes evaluator timeouts, and explains the mathematical mechanics of metric distortion on concise and negative-control responses.

---

## 1. Automated Judge Stack Specifications

| Layer | Implementation Component | Version / Runtime | Configuration | Execution Constraints |
| :--- | :--- | :--- | :--- | :--- |
| **Judge LLM** | `llama3.1:8b` | Ollama (Local) | `temperature: 0.0`, `num_predict: 512` | Offline, zero cloud API calls |
| **Embedding Engine** | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace (Local) | 384-dimensional cosine similarity | Local files only |
| **Framework** | RAGAS | `0.2.15` | `faithfulness`, `answer_relevancy` | Sequential execution (`max_workers=1`) |
| **Gold Evidence Standard** | `evaluation/benchmark/gold_judgments.jsonl` | **0 bytes** | Frozen invariant | Zero unverified human gold labels |

---

## 2. Metric Sensitivity Profiles & Known Artifacts

### 2.1 The "Conciseness & Disclaimer Penalty" on Full-Response Faithfulness
In Phase F.1 and Phase F.2, we established the mathematical formula governing full-response evaluation:
$$\text{Faithfulness} = \frac{C_{\text{supported}}}{C_{\text{supported}} + C_{\text{unsupported}}}$$
- The mandatory 47-word legal disclaimer (`### ⚠️ Important Warning...`) reliably yields $C_{\text{disclaimer}} = 5$ atomic legal claims.
- Because biomedical retrieval contexts contain only FDA label and disease monograph text, all 5 disclaimer claims are judged **unsupported**.
- In a concise, highly faithful response with $C_{\text{body}} = 2$ supported factual claims:
  $$\text{Faithfulness}_{\text{full}} = \frac{2}{2 + 5} = \frac{2}{7} \approx 0.2857$$
- Across `full_response_scores.csv`, every concise drug answer (`MED-BENCH-005`, `008`, `011`, `012`, `014`) scored exactly **0.285714**.
- **Audit Conclusion:** Full-response faithfulness severely penalizes concise, well-grounded answers. Decoupling the disclaimer to evaluate `response_body` is essential for valid grounding measurement.

---

### 2.2 The "Abstention & Conciseness Distortion" on Answer Relevancy
RAGAS `answer_relevancy` operates by prompting the judge LLM to generate 3 hypothetical user questions that the candidate answer addresses, embedding those 3 questions, and computing mean cosine similarity with the actual user query:
$$\text{Answer Relevancy} = \frac{1}{3} \sum_{i=1}^3 \cos\left(E(q_i^{\text{synth}}), E(q^{\text{actual}})\right)$$

#### Failure on Clean Abstentions:
- Query: `"Treatment protocol for acute Martian respiratory syndrome"` (`MED-BENCH-042`)
- Candidate Answer: `"No information is available for Treatment protocol for acute Martian respiratory syndrome."`
- The LLM judge extracts what the answer addresses and generates synthetic questions such as:
  1. `"What does the database have information on?"`
  2. `"Is there information available for this condition?"`
  3. `"What records are missing?"`
- When embedded, these generic meta-questions have low cosine similarity ($\sim 0.15 - 0.35$) to the clinical query `"Treatment protocol for acute Martian respiratory syndrome"`.
- As a result, a clinically perfect abstention receives an Answer Relevancy score of **0.0000 - 0.2500**!

#### Failure on Direct, Concise Answers:
- For `MED-BENCH-010` (Query: `"Ibuprofen"`):
  - Direct answer: `"Ibuprofen is available under brand names Advil, Motrin, Nuprin."`
  - Synthetic questions generated: `"What brand names contain ibuprofen?"`
  - Cosine similarity between `"Ibuprofen"` (single token) and `"What brand names contain ibuprofen?"` drops to **0.3090**, even though the clinical intent was 100% satisfied.

**Audit Conclusion:** RAGAS answer relevancy is fundamentally biased toward verbose answers that restate the question and provide explanatory framing. Concise factual listings and abstentions incur an artificial relevancy penalty.

---

### 2.3 Judge Timeout Failures on Local Runtime
When evaluating multi-claim answers sequentially on a local 16GB Apple Silicon runtime, Ragas's internal asynchronous event loop occasionally exceeds default task timeouts:
- In Phase F.2, `MED-BENCH-013` and `MED-BENCH-047` suffered `TimeoutError()` in async worker threads, defaulting to `F=0.0`.
- Each timeout artificially suppresses cohort mean faithfulness by $0.0200$ (2 full percentage points).
- In Phase F.3, we remediated this by raising `RunConfig(max_workers=1, timeout=180, max_wait=180)` and implementing sequential processing.

---

## 3. Human Audit vs AI-Assisted Assessment Labeling

Per clinical AI safety standards:
- All scores, claim relationships, and classifications in Phase F are **AI-assisted automated experimental assessments** produced by local evaluation models.
- They are **not** clinician-validated gold truths.
- `evaluation/benchmark/gold_judgments.jsonl` remains strictly **0 bytes** to prevent unverified model outputs from being falsely labeled as human clinical gold.
