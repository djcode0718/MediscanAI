# MediScanAI Phase C.5 — Paired Ragas Evaluation of Baseline vs Graph-Assisted Responses

**Phase:** C.5  
**Framework:** Ragas `0.2.15` with LangChain `1.4.6`  
**Judge Model:** `llama3.1:8b` via local Ollama (`http://localhost:11434`, greedy `temperature=0.0`)  
**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (`local_files_only=True`)  
**Generator Model:** `llama3.1:8b` (Phase C.4 frozen answers)  
**Date:** 2026-10-15  

---

## 1. Overview & Objective

Phase C.5 executes a paired, evidence-based evaluation comparing MediScanAI's **Baseline Hybrid Retrieval** (dense FAISS + BM25 + RRF + cross-encoder reranking) against **Graph-Assisted Retrieval** (identical baseline evidence supplemented with Neo4j graph triples where available) across the 50 canonical benchmark queries.

The evaluation evaluates whether supplementary graph relations improve answer faithfulness, relevance, context precision, and context recall, or whether they introduce distractor content and unsupported claims.

### Absolute Ground Rules:
1. `entity_resolution/` is strictly off-limits.
2. `evaluation/benchmark/gold_judgments.jsonl` remains strictly 0 bytes.
3. All 100 Phase C.4 responses and contexts are frozen experimental inputs; no answers are regenerated.
4. Reference answers from Phase C.1.2 are AI-assisted research summaries (`human_reviewed=False`, `clinical_reviewed=False`, `official_human_gold=False`), NOT clinical gold standards.
5. All operations are strictly local (local Ollama and offline cached embeddings); zero external API calls.

---

## 2. Directory Structure

```
evaluation/ragas/phase_c_5/
├── README.md                      # Reproduction instructions, methodology, caveats
├── preflight_report.md            # Input validation, cryptographic verification, Go/No-Go
├── run_manifest.json              # Provenance manifest with model configs, hashes, and settings
├── metric_contract.md             # Formal metric definitions and eligibility specification
├── run_evaluation.py              # Reproducible evaluation runner script
├── case_level_scores.csv          # Granular case-level scores across all 100 runs
├── paired_metric_deltas.csv       # Paired graph minus baseline differences per case
├── aggregate_metrics.json         # Aggregate means, medians, 95% bootstrap CIs, outcome counts
├── metric_failures.jsonl          # Log of any judge errors, retries, or malformed responses
├── progress.json                  # Live execution progress and ETA tracking
├── negative_control_analysis.md   # Safety analysis for 5 negative controls and chest pain
├── judge_bias_and_limitations.md  # Detailed documentation of same-model bias and caveats
├── evaluation_report.md           # Comprehensive evaluation narrative, findings, and analysis
└── integrity_report.json          # Automated post-run integrity audit
```

---

## 3. Metrics & Eligibility Specification

| Metric Name | Implementation | Eligible Sample Size | Denominator Policy |
| :--- | :--- | :---: | :--- |
| **Faithfulness** | `ragas.metrics.faithfulness` | **50 / 50 pairs** (100 runs) | Evaluated across all 50 cases. |
| **Answer Relevancy** | `ragas.metrics.answer_relevancy` | **50 / 50 pairs** (100 runs) | Evaluated across all 50 cases. |
| **Context Precision** | `ragas.metrics.context_precision` | **45 / 50 pairs** (90 runs) | 5 negative controls marked `ineligible_unanswerable_negative_control` (null score with explicit reason). |
| **Context Recall** | `ragas.metrics.context_recall` | **45 / 50 pairs** (90 runs) | 5 negative controls marked `ineligible_unanswerable_negative_control` (null score with explicit reason). |

---

## 4. How to Reproduce

### 4.1 Prerequisites
- Conda environment `med-env`:
  ```bash
  conda activate med-env
  ```
- Local Ollama running with `llama3.1:8b`:
  ```bash
  ollama list | grep llama3.1:8b
  ```

### 4.2 Executing Evaluation
To execute or resume the evaluation run:
```bash
/Users/sj/miniforge3/envs/med-env/bin/python -u evaluation/ragas/phase_c_5/run_evaluation.py
```
- Evaluation runs strictly sequentially (`max_workers=1`) to prevent unified memory pressure.
- Checkpoints are written atomically to `case_level_scores.csv` after every run; interrupted runs resume automatically without re-evaluating completed cases.

### 4.3 Recomputing Deltas and Aggregates
To recompute deltas, bootstrap confidence intervals, and aggregate summaries from an existing `case_level_scores.csv`:
```bash
/Users/sj/miniforge3/envs/med-env/bin/python evaluation/ragas/phase_c_5/run_evaluation.py --post-process-only
```

---

## 5. Methodological Limitations & Safety Warnings

1. **Same-Model Self-Evaluation Bias:** `llama3.1:8b` serves as both generator and judge. Scores reflect relative consistency rather than independent clinical validation.
2. **AI-Assisted Reference Provenance:** Reference answers are source-backed research syntheses from Phase C.1.2, not human-approved gold.
3. **Exploratory Status:** This experiment is a technical evaluation of retrieval augmentation. It does **NOT** constitute clinical validation, regulatory clearance, or proof of diagnostic safety.
