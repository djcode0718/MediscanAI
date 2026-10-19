# Phase F.3 — Focused Grounding, Relevance, and Safety Separation Experiment Design

## 1. Experimental Overview & Objectives

Phase F.3 extends the empirical findings of Phase F.2 to address the remaining bottlenecks preventing MediScanAI from achieving high body-only faithfulness and high answer relevancy.

### Historical Progression & Motivation:
- **Phase C.5 (Historical):** Baseline full-response Faithfulness = **0.5835**, Answer Relevancy = **0.7532**.
- **Phase F.1 (Diagnosis):** Identified that the mandatory 47-word legal disclaimer contaminated Ragas claim verification, while the generator introduced parametric indications, drug classes, and query tag echoes.
- **Phase F.2 (Decoupling & Strict Grounding):** Decoupling the disclaimer alone elevated baseline body faithfulness to **0.8207**. However, the strict-grounding prompt achieved only **0.7384** faithfulness and experienced an answer relevancy drop to **0.5840**.
- **Root Causes Identified in F.2 Audit:**
  1. **Introductory Meta-Talk (18/31 claims):** Sentences like `"The retrieved database records contain..."` were marked unfaithful.
  2. **Emergency Guidance Bleed (7/31 claims):** Instructing the generator to provide chest pain warnings caused it to prepend emergency alerts to routine drug queries like "Amoxicillin".
  3. **MED-BENCH-042 Negative Control Failure:** Lexical BM25 match on "Mars" caused the model to answer with Mars Wellness products instead of abstaining.

### Phase F.3 Objectives:
1. Eliminate introductory meta-talk by introducing **Direct-Answer Generation** (`F3-A`).
2. Eliminate safety warning bleed by implementing **Safety Separation** (`F3-B`), isolating emergency triage into the pre-generation `EmergencyGuardrail` classifier.
3. Solve `MED-BENCH-042` with an **Exact Entity Verification Rule**.
4. Test the **Combined Candidate** (`F3-C`) on the development split ($N=30$) to determine whether it passes the development gate (Faithfulness $\ge 0.9200$, Relevancy $\ge 0.7300$, Negative Controls 5/5).

---

## 2. Experimental Arms and Comparisons

| Condition ID | Strategy | Prompt Configuration | Safety Escalation Architecture | Primary Evaluation Payload |
| :--- | :--- | :--- | :--- | :--- |
| **`F3-0`** | Strict Control (F.2) | F.2 Strict Grounding | Embedded inside generator prompt | `response_body` (includes safety bleed & meta-talk) |
| **`F3-A`** | Direct-Answer Gen | Direct-Answer Prompt (Zero meta-talk) | Embedded inside generator prompt | `response_body` (zero meta-talk; safety bleed remains) |
| **`F3-B`** | Safety Separation | F.2 Strict Grounding | Isolated `EmergencyGuardrail` classifier | `response_body` (zero safety bleed; meta-talk remains) |
| **`F3-C`** | Combined Primary | Direct-Answer Prompt | Isolated `EmergencyGuardrail` classifier | `response_body` (zero meta-talk, zero safety bleed) |

---

## 3. Split Isolation and Experimental Discipline

- **Development Set ($N=30$, `dev`):** The primary experimental arena. All candidate tuning and gate validation take place exclusively on this split.
- **Validation Set ($N=10$, `val`):** Evaluated strictly after development freezing.
- **Held-Out Test Set ($N=10$, `held_out_test`):** Strictly held out; zero prompt adjustments or threshold tuning.
- **Retrieval Invariant:** Retrieval contexts, FAISS indexes, BM25 indices, and rank fusion outputs are frozen and identical across all conditions.

---

## 4. Evaluation Contract & Metrics

All conditions are evaluated against:
1. **Ragas Faithfulness (`response_body`):** Evaluates factual body claims against retrieved chunks. (Primary target: >0.9500; Development gate: $\ge 0.9200$).
2. **Ragas Faithfulness (`response_full`):** Historical full-response protocol including the 47-word legal disclaimer.
3. **Ragas Answer Relevancy:** Measures embedding similarity of synthetic questions generated from the answer body against the user query. (Target: $\ge 0.7300$, regression $\le 0.02$).
4. **Negative Control Abstention Rate:** Target: **5 / 5 (100.0%)** across `MED-BENCH-041` through `MED-BENCH-045`.
5. **Emergency Triage Recall:** Target: **100.0%** on acute emergency queries (`MED-BENCH-038`).
6. **Disclaimer Preservation:** Target: **100.0% (50/50)** verbatim in user-facing full responses.
7. **Claim Grounding Audit:** 6-way classification of atomic factual claims.

---

## 5. Absolute Invariant Checks

- `entity_resolution/`: Strictly unaccessed (0 reads, 0 imports, 0 modifications).
- `evaluation/benchmark/gold_judgments.jsonl`: Exactly **0 bytes**.
- Frozen Phase D.2.c hash: `f3937376cd191ee7`.
- Cloud API calls: **0** (Local Ollama `llama3.1:8b` and local HuggingFace embeddings only).
- Production code: Zero modifications (`git status` clean).
