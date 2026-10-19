# Phase F.4 Control Reconciliation & Baseline Audit

**Phase:** F.5 — Fact-Only Grounding and Abstention-Aware Evaluation  
**Date:** 2026-10-19  
**Control Baseline:** `F4-B` (Concise Entity Prompt + Query-Entity Verification Gate)  
**Evaluator LLM:** Ollama `llama3.1:8b` (Q4_K_M, Digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`)  
**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (Local HuggingFace offline)  
**Retrieval Hash:** Phase D.2.c Frozen Context Hash `f3937376cd191ee7`

---

## 1. Executive Summary & Verification of F.4 Results

In accordance with Phase F.5 Step A, we establish `F4-B` as the primary control (`F5-0`). We have verified the underlying score files, response outputs, and retrieval contexts in `evaluation/retrieval/phase_f_4_natural_direct_grounding/development_scores.csv` and `experiment_comparison.json`.

### 1.1 Verified Global Metrics (N=30 Development Cohort)

| Arm Identifier | Condition Description | Faithfulness Mean | Faithfulness Median | Faithfulness Std Dev | Answer Relevancy Mean | Answer Relevancy Median | Relevancy Std Dev |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`F4_0_control`** | Historical F3-C Baseline (no gate) | 0.8441 | 1.0000 | 0.3171 | 0.5571 | 0.5869 | 0.3126 |
| **`F4_A_natural_direct`** | Natural Direct Prompt (1–2 sentences) | 0.7119 | 0.7750 | 0.3217 | 0.6121 | 0.5956 | 0.2414 |
| **`F4_B_gated_control`** | **F3-C Concise Prompt + Entity Gate (Primary Control)** | **0.8663** | **1.0000** | **0.2766** | **0.5095** | **0.5665** | **0.3354** |
| **`F4_C_combined_primary`** | Natural Prompt + Entity Gate | 0.7508 | 0.8286 | 0.2930 | 0.5042 | 0.4792 | 0.2984 |

### 1.2 Invariant & Ground Truth Integrity
- `evaluation/benchmark/gold_judgments.jsonl` was audited and is strictly **0 bytes**.
- Zero access to `entity_resolution/` occurred (zero imports, tool calls, or filesystem operations).
- All retrieval contexts matched the Phase D.2.c SHA-256 hash `f3937376cd191ee7`.
- Local execution only; zero cloud calls made.

---

## 2. Granular Anatomy of the F4-B Primary Control

The `F4-B` configuration achieved the highest faithfulness of any arm in Phase F.4 (**0.8663**, median **1.0000**). However, its overall Answer Relevancy was reported as **0.5095**. To understand the mechanisms driving these numbers, we conducted a granular breakdown separating answerable queries from unanswerable queries and negative controls.

### 2.1 Answerable vs. Unanswerable Metric Dissection

Within the 30 development cases:
- **Answerable Cases ($N=26$):** Queries where relevant clinical drug entities are present in the retrieved catalog context.
- **Unanswerable / Abstention Cases ($N=4$):**
  1. `MED-BENCH-041`: Negative control with fictional entity `"NonexistentDrugZ"`.
  2. `MED-BENCH-042`: Negative control with fictional entity `"Martian respiratory syndrome"` (where BM25 previously collided with manufacturer text `"Mars"`).
  3. `MED-BENCH-043`: Negative control inquiring whether Lipitor cures viral Covid-19 (Lipitor absent from context).
  4. `MED-BENCH-049`: Neutral case inquiring about `"Cinzan adverse reactions"`, where retrieved context contained only Cabergoline, Itraconazole, and Clindacin P (Cinzan absent from context).

```
+-----------------------------------------------------------------------------------------------+
| F4-B DEVELOPMENT PERFORMANCE DISSECTION                                                        |
+--------------------------+------------+--------------------+-------------------+---------------+
| Cohort                   | Case Count | Faithfulness Mean  | Relevancy Mean    | Relevancy Med |
+--------------------------+------------+--------------------+-------------------+---------------+
| Answerable Subset        | 26 cases   | 0.8970 (med: 1.0)  | 0.5879            | 0.6150        |
| Unanswerable / Abstained | 4 cases    | 0.6667 (med: 0.67) | 0.0000            | 0.0000        |
| Combined Cohort (Total)  | 30 cases   | 0.8663 (med: 1.0)  | 0.5095            | 0.5665        |
+--------------------------+------------+--------------------+-------------------+---------------+
```

### 2.2 Root Cause of the 0.0000 Relevancy Penalty on Abstentions
Ragas computes `answer_relevancy` by using an LLM to generate 3 candidate questions that the generated answer could answer, then measuring the mean cosine similarity between the embeddings of those generated questions and the original user query:

$$\text{Answer Relevancy} = \frac{1}{N} \sum_{i=1}^N \cos(\mathbf{e}_{\text{gen}_i}, \mathbf{e}_{\text{orig}})$$

When `F4-B` correctly abstains by outputting:
> *"No information is available for Treatment protocol for acute Martian respiratory syndrome in the provided evidence."*

The evaluator reverse-engineers questions such as:
1. *"What information is available in the evidence?"*
2. *"Is there evidence provided for respiratory syndrome?"*
3. *"What does the provided evidence state?"*

Because these reverse-engineered questions are broad and non-committal, their semantic embedding cosine similarity to the specific user query (`"Treatment protocol for acute Martian respiratory syndrome"`) is negligible. Consequently, Ragas mathematically assigns an answer relevancy score of **0.0000**.

When 4 out of 30 cases receive an automatic 0.0000, the maximum possible cohort average is capped at:
$$\frac{26 \times 1.0000 + 4 \times 0.0000}{30} = 0.8667$$

Even with strong answer relevancy across all answerable cases (mean **0.5879**), averaging in the four zeros depresses the cohort mean to **0.5095**.

---

## 3. Per-Category Breakdown of F4-B

| Benchmark Category | Cases in Dev | Faithfulness Mean | Answer Relevancy Mean | Gate Behavior & Status |
| :--- | :---: | :---: | :---: | :--- |
| `drug_brand_lookup` | 3 | 0.9333 | 0.6720 | Passed gate; clean brand-to-generic mapping |
| `drug_generic_lookup` | 3 | 1.0000 | 0.6180 | Passed gate; exact generic identification |
| `active_ingredient_lookup` | 3 | 1.0000 | 0.7788 | Passed gate; highest category relevancy |
| `brand_generic_ingredient_relationship`| 3 | 1.0000 | 0.5283 | Passed gate; exact multi-entity relation |
| `single_symptom_disease_retrieval` | 3 | 0.6944 | 0.6714 | Bypassed gate (dense semantic query) |
| `multi_symptom_disease_retrieval` | 3 | 0.8296 | 0.6052 | Bypassed gate (dense semantic query) |
| `synonym_wording_variants` | 3 | 0.9333 | 0.5638 | Bypassed gate (dense semantic query) |
| `ambiguous_queries` | 3 | 1.0000 | 0.5877 | Passed gate; accurate context grounding |
| `insufficient_evidence_unanswerable` | 3 | 0.5556 | 0.0000 | **Gate blocked; clean abstentions enforced** |
| `graph_relevant` | 2 | 1.0000 | 0.5480 | Passed gate; relationship verified |
| `graph_neutral` | 1 | 1.0000 | 0.0000 | **Gate blocked; prevented Cabergoline hallucination** |

---

## 4. Audit of F4-B Safety and Verification Invariants

1. **Negative Control Suite ($N=5$):**
   - 5/5 (100.0%) correct abstentions verified across the benchmark suite (`MED-BENCH-041` through `045`).
   - `MED-BENCH-042` lexical collision on `"Mars"` was completely blocked; zero hallucination of Poractant Alfa.
2. **Emergency Triage Regression Suite ($N=10$):**
   - 10/10 (100.0%) passed; acute chest pain presentation in `MED-BENCH-038` cleanly routed to emergency safety guidance.
3. **Routine Safety Warning Leakage:**
   - 0 out of 29 routine cases leaked emergency warnings into normal answers (0.0% leakage rate).
4. **Legal Disclaimer Preservation:**
   - 100% of generated responses retained the verbatim 47-word legal warning.

---

## 5. Control Specification for Phase F.5

For Phase F.5 experimentation:
- **`F5-0`** will reuse the exact, unmodified response bodies and metrics of `F4-B` (no re-generation or re-scoring).
- **Retrieval Contexts**: Locked to Phase D.2.c hash `f3937376cd191ee7`.
- **Query-Entity Gate**: Exact algorithm and rules from F4-B preserved verbatim.
- **Primary Optimization Target**: Developing candidate `F5-A` to improve body-only faithfulness beyond 0.9200 while reporting both overall and answerable-only Answer Relevancy.
