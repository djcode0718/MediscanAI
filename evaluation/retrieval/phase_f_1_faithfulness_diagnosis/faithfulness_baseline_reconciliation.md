# Phase F.1 — Faithfulness Baseline Reconciliation & Provenance Verification

## Executive Summary

Phase F.1 establishes the empirical diagnostic baseline for MediScanAI's RAGAS Faithfulness evaluation. Our engineering objective is to transition from the historical Phase C.5 baseline of **0.5835** to greater than **0.9500** through genuine evidence grounding, without artificial metric manipulation or indiscriminate abstention.

This document verifies the underlying Phase C.4 and Phase C.5 evaluation outputs, audits model and judge configurations, confirms exact input/output hashes, and reconciles reported aggregate statistics with underlying case-level generation and context records.

---

## 1. Verified Benchmark & Environment Provenance

### 1.1 Dataset and Execution Scope

- **Benchmark Dataset:** Canonical Medical Benchmark Phase A.3
- **Unique Test Cases:** Exactly 50 unique queries (`MED-BENCH-001` through `MED-BENCH-050`)
- **Evaluated Cohorts:**
  - `baseline`: 50 runs (dense FAISS + BM25 + RRF + cross-encoder)
  - `graph_assisted`: 50 runs (hybrid + Neo4j knowledge graph context)
- **Total Generations Evaluated:** Exactly 100 frozen responses from Phase C.4

### 1.2 Runtime Environment & Dependencies

| Component | Verified Version | Source / Path |
| :--- | :--- | :--- |
| **Python** | `3.10.18` | `med-env` Conda environment |
| **Ragas** | `0.2.15` | `pip show ragas` |
| **LangChain** | `1.4.6` | `pip show langchain` |
| **Datasets** | `3.6.0` | `pip show datasets` |
| **Sentence-Transformers** | `5.1.0` | `pip show sentence_transformers` |
| **Ollama Runtime** | `0.30.5` | `http://localhost:11434` |

### 1.3 Generator, Judge, and Embedding Configurations

- **Generator Model:** `llama3.1:8b`
  - Digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`
  - Parameters: `temperature: 0.0`, `num_predict: 512`, `top_p: 1.0`
- **Judge Model:** `llama3.1:8b` (Self-evaluation / Identical Model Family)
  - Digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`
  - Execution Policy: Strictly sequential (`max_workers: 1`, timeout: 180s)
  - Judge Consistency: The identical judge instance and prompt evaluated all 100 responses across both tracks.
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (Offline local execution enforced).

---

## 2. Reconciled Baseline Faithfulness Metrics

### 2.1 Direct Verification of Historical Reported Numbers

From `evaluation/ragas/phase_c_5/aggregate_metrics.json` and `case_level_scores.csv`:

| Track | Metric Name | Reported in C.5 | Recomputed in F.1 | Exact Match |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline Track** | Faithfulness Mean | **0.583470** (~0.5835) | **0.583470** | **YES (Identical)** |
| | Faithfulness Median | **0.500000** | **0.500000** | **YES (Identical)** |
| | Standard Deviation | `0.252557` | `0.252557` | **YES (Identical)** |
| | Min / Max | `0.166667` / `1.000000` | `0.166667` / `1.000000` | **YES (Identical)** |
| **Graph-Assisted Track** | Faithfulness Mean | **0.570257** (~0.5703) | **0.570257** | **YES (Identical)** |
| | Faithfulness Median | **0.500000** | **0.500000** | **YES (Identical)** |
| | Paired Mean Delta | **-0.013213** | **-0.013213** | **YES (Identical)** |
| | Bootstrap 95% CI | `[-0.075905, 0.052703]` | `[-0.075905, 0.052703]` | **YES (Identical)** |

### 2.2 Completeness and Missing Data Audit

- **Faithfulness Denominator:** Exactly **50 / 50** baseline cases and **50 / 50** graph-assisted cases yielded valid numerical faithfulness scores.
- **Missing or Excluded Cases:** Zero missing cases for Faithfulness (`N=50` pairs). *(Note: `MED-BENCH-029` suffered an internal timeout during Context Recall evaluation in Phase C.5, but its Faithfulness score was successfully recorded as `1.000000`)*.
- **Negative Controls:** All 5 unanswerable negative control queries (`MED-BENCH-041` through `MED-BENCH-045`) were evaluated for faithfulness.

---

## 3. Context & Input Alignment Verification

A critical verification requirement is ensuring that the retrieval contexts supplied to the RAGAS evaluator exactly match the retrieval contexts provided to the generator during response generation:

1. **Context Text Identity:** In `run_evaluation.py`, `contexts[(cid, track_name)]["context_text"]` was loaded directly from `evaluation/ragas/phase_c_4/retrieval_contexts.jsonl`.
2. **Chunking Strategy:** `extract_context_chunks(context_text)` split the context string by linebreaks (`\n`), stripping empty lines and headers.
3. **Prompt Integrity:** The prompt string fed to the generator in Phase C.4 incorporated `{context}` verbatim.
4. **Context Hash Verification:** The SHA-256 hash of the context string stored in `generation_runs.jsonl` matches `retrieval_contexts.jsonl` across all 50 baseline cases.

---

## 4. Master Artifact Hashes

| Artifact Path | Record Count | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `evaluation/ragas/phase_c_4/paired_responses.jsonl` | 50 records | 238,708 B | `1639cb0612f24dae8ccf6af920aeee97ddd3bf4c5ce9820adc4deed53b847352` |
| `evaluation/ragas/phase_c_4/retrieval_contexts.jsonl` | 100 records | 452,830 B | `c8802f0492eaf9ac25866cd5106468208a5f846d8ef4498564229b2b41cbcefb` |
| `evaluation/ragas/phase_c_4/generation_runs.jsonl` | 100 records | 226,313 B | `ea58800623608d953b37545558e1c17f327502b2a8088a65d676700b8cafcfc4` |
| `evaluation/ragas/phase_c_5/case_level_scores.csv` | 100 rows | 39,910 B | `07f5945c55dcbf5f6a93e5066db6509f63200ffcc5da29e37da09f984a92a543` |
| `evaluation/ragas/phase_c_5/aggregate_metrics.json` | JSON object | 8,472 B | `1c899c36209ad7bfa9c3be7ae07f2a4e98f029c323f4c6530635e982fafe750c` |
| `evaluation/benchmark/gold_judgments.jsonl` | **0 lines** | **0 Bytes** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `evaluation/retrieval/phase_d_2_c/intent_router.py` | Python source | 17,992 B | Frozen hash: `f3937376cd191ee7` (exact match) |

---

## 5. Conclusion: Baseline Established

The reported historical baseline of **0.5835** is mathematically verified, fully reproducible from frozen artifacts, and established as the reference benchmark for Phase F engineering optimizations.
