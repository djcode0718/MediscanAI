# Phase F.2 — Grounded Generation and Faithfulness Evaluation Decoupling: Experiment Design

## 1. Executive Objective

Phase F.2 executes a controlled, non-production experiment to resolve the two primary root causes of low RAGAS Faithfulness identified in Phase F.1:
1. **The Evaluation Artifact (Disclaimer Penalty):** The mandatory 47-word legal warning (*"This analysis is for informational purposes only... not a substitute for professional medical advice..."*) was historically evaluated as part of the factual response payload, causing Ragas to extract 250 disclaimer claims across 50 cases and mark 100% of them as unsupported by biomedical retrieval chunks.
2. **Genuine Factual Grounding Failures:** The generator model (`llama3.1:8b`) frequently injected ungrounded parametric knowledge (such as drug indications, therapeutic classes, mechanisms of action, and disease etiologies) when the underlying database chunk contained only brand, generic, and active substance names. In addition, 58% of responses contained `<USER_QUERY>` prompt tag echoes and meta-commentary.

The goal is to improve genuine body-level evidence grounding to reach the engineering target of **> 0.9500** on body-only evaluation while preserving the verbatim legal disclaimer in all user-facing responses, retaining high answer relevancy (≥ 0.7300), and maintaining 100% emergency safety and negative control abstention.

---

## 2. The 4-Arm Experimental Matrix

To isolate the separate effects of evaluation-only decoupling versus strict-grounding generation improvements, Phase F.2 evaluates four distinct experimental conditions on the exact same canonical retrieval contexts:

| Condition Code | Generation Prompt | Evaluated Text Segment | Description & Purpose |
| :--- | :--- | :--- | :--- |
| **`EXP-F2-0`** | Baseline Prompt (Phase C.4) | `response_full` (with disclaimer) | **Historical Baseline:** Replicates Phase C.5 full-response benchmark (`0.5835`). |
| **`EXP-F2-A`** | Baseline Prompt (Phase C.4) | `response_body` (disclaimer excluded) | **Evaluation Decoupling Only:** Measures the exact metric gain of removing the disclaimer penalty without regenerating any answers. |
| **`EXP-F2-B`** | Strict-Grounding Prompt (Phase F.2) | `response_full` (with disclaimer) | **Strict Grounding Full:** Measures prompt improvements while still subjected to the disclaimer evaluation penalty. |
| **`EXP-F2-C`** | Strict-Grounding Prompt (Phase F.2) | `response_body` (disclaimer excluded) | **Primary Candidate:** Combines strict evidence-only generation with decoupled evaluation. Target: **> 0.9500**. |

---

## 3. Strict-Grounding Prompt Engineering

The experimental generation prompt enforces strict negative constraints to prevent parametric knowledge leaks:

```markdown
Core Generation Constraints:
1. Strict Grounding: Base your factual answer ONLY on the provided Retrieved Evidence Context.
2. Negative Constraint on Parametric Knowledge: Never introduce drug indications, therapeutic uses, mechanisms of action, drug classes (e.g. do NOT say 'NSAID', 'statin', 'analgesic', 'antibiotic'), contraindications, or disease causes unless they are explicitly written in the evidence context above. If the context contains only brand and generic names, state ONLY those names.
3. Preserving Exact Details: Preserve exact salt forms, qualifiers, and spelling from the context. Do not assume two differently named products are identical.
4. Clean Abstention on Insufficient Evidence: If the context contains no records matching the queried entity, or if the evidence does not answer the question, state: "The retrieved database records contain no information to answer this query." Do NOT summarize or list unrelated records from the context.
5. Emergency Clinical Guidance: For any acute symptom presentation (such as chest pain, severe breathing difficulty, sudden weakness, or stroke symptoms), ALWAYS state explicitly at the top of your answer: "Immediate Medical Attention: Acute symptoms like chest pain require immediate professional emergency medical evaluation (call 911/112 or local emergency services)."
6. Formatting Rules:
   - Do NOT echo `<USER_QUERY>` tags, delimiter blocks, or prompt instructions.
   - Do NOT use meta-phrases like "Based on the retrieved evidence context..." or "The context lists...". State the facts directly.
   - Conclude your entire response with the exact mandatory warning section below verbatim.
```

---

## 4. Benchmark Cohort & Split Isolation

To prevent overfitting and preserve scientific validity, the canonical 50-case benchmark is strictly partitioned according to frozen Phase D.2.c split assignments:
- **Development Split (`dev`, $N=30$):** Used for candidate evaluation, parameter freezing, and iterative diagnosis.
- **Validation Split (`val`, $N=10$):** Out-of-development confirmation evaluated under configuration freeze.
- **Held-Out Test Split (`held_out_test`, $N=10$):** Sealed evaluation split. Evaluated strictly once without prompt or threshold tuning.

---

## 5. Execution Protocol & Hardware Constraints

- **Hardware Environment:** Apple MacBook Air M4 (16 GB Unified Memory).
- **Inference Runtime:** Local Ollama (`llama3.1:8b`, Q4_K_M, temperature: 0.0, context: 131,072).
- **Concurrency Policy:** Strictly sequential (`max_workers=1`). No parallel execution to prevent memory pressure or thermal throttling.
- **Atomic Persistence:** Each response pair and evaluation row is checkpointed to disk immediately upon completion to guarantee full recovery in case of interruption.
- **Offline Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` executed locally with `local_files_only=True`. Zero external cloud calls.
