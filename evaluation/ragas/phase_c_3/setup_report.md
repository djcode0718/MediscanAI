# Phase C.3 — Ragas Evaluation Infrastructure Setup Report

**Phase:** C.3 (Ragas Infrastructure Setup)  
**Date:** 2026-10-15  
**Evaluator:** MediScanAI Evaluation Engineering  
**Target Environment:** Conda environment `med-env` on Apple Silicon (macOS arm64)  
**Status:** Complete & Fully Validated (`PASSED`)

---

## 1. Executive Summary

Phase C.3 establishes the validated evaluation infrastructure for the upcoming Phase C.4 paired RAG evaluation (comparing 50 baseline hybrid responses against 50 Neo4j graph-assisted responses).

This phase resolved all library compatibility hurdles, selected a pin-stabilized Ragas release (`ragas==0.2.15`), established local embedding and judge integrations, validated the promoted 50 narrative reference answers, constructed a dedicated dataset adapter, and executed a 5-step smoke test with 100% pass rate.

No full benchmark responses were generated, and `evaluation/benchmark/gold_judgments.jsonl` remains strictly 0 bytes.

---

## 2. Environment Audit & Dependency Resolution Findings

### Host & Environment Audit
- **Host OS:** macOS 15.7.9 (Darwin 24.6.0, Apple Silicon Mac16,12)
- **Host Memory & Compute:** 16 GB Unified Memory, 10 CPU cores
- **Target Python Environment:** Conda `med-env` (`/Users/sj/miniforge3/envs/med-env`)
- **Python Version:** `3.10.18` (packaged by conda-forge)
- **Local Inference Server:** Ollama v0.30.5 (`http://localhost:11434`)

### Dependency Conflict Discovery & Resolution
1. **Initial Conflict with Unpinned `ragas` (v0.4.3):**
   - Installing unconstrained `ragas` pulled `datasets 5.1.0` and `huggingface-hub 2.2.0`.
   - This broke MediScanAI's production embedding stack (`transformers 4.56.1` and `tokenizers 0.22.0`), which enforce `huggingface-hub<1.0,>=0.34.0`.
2. **Resolution Strategy:**
   - Identified that `ragas==0.2.15` and `datasets==3.6.0` support `huggingface-hub<1.0`.
   - Pinned `huggingface-hub==0.36.2`, preserving 100% compatibility with existing `transformers 4.56.1` and `sentence-transformers 5.1.0`.
   - Pinned `langchain-community==0.3.31` to satisfy internal Ragas module references.
3. **Validated Package Manifest:**
   - `ragas==0.2.15`
   - `datasets==3.6.0`
   - `langchain==1.4.6`
   - `langchain-core==1.6.10`
   - `langchain-community==0.3.31`
   - `sentence-transformers==5.1.0`
   - `transformers==4.56.1`
   - `huggingface-hub==0.36.2`
   - `pydantic==2.11.9`
   - `torch==2.8.0`

Existing project dependencies, offline FAISS indices, and embedding models were completely preserved and confirmed functional.

---

## 3. Model Roles: Generator, Judge, and Embeddings

### A. Generator Model
- **Model Identifier:** `llama3.1:8b` (Ollama digest `46e0c10c039e...`)
- **Role:** Generates candidate clinical answers for both baseline hybrid retrieval and Neo4j graph-assisted retrieval.
- **Runtime:** Local Ollama REST API with deterministic settings (`temperature=0`, `num_predict=512`).

### B. Judge Model
- **Local Primary Judge:** `llama3.1:8b` via `ChatOllama` wrapped in `LangchainLLMWrapper`.
  - *Empirical Validation:* Correctly generated statements and integer verdicts (`verdict: 1`), passing Pydantic schema validation without output parser exceptions.
- **Local Alternative Judge Limitation (`mistral:latest`):**
  - In our empirical tests, `mistral:latest` generated float verdicts (`verdict: 0.5`) on NLI classification, causing Pydantic validation errors in Ragas's output parser. Mistral is therefore **disqualified** as an automated Ragas judge without custom prompt post-processing.
- **Memory & Resource Budget:**
  - Running a single 8B model locally (`llama3.1:8b`, ~5.8 GB VRAM footprint) operates well within the 16 GB unified-memory envelope. Sequential execution ensures zero GPU/VRAM thrashing.
- **Hosted Judge Option (Proposal for Phase C.4):**
  - MediScanAI has Gemini (`gemini-2.0-flash` / `gemini-1.5-flash`) and Groq (`llama-3.3-70b-versatile`) keys in `.env`.
  - If a strictly independent external judge is preferred to eliminate self-evaluation bias, Gemini or Groq can be configured via `ChatOpenAI` / `ChatGoogleGenerativeAI` subject to explicit approval. No external API calls were made in this phase.

### C. Embedding Model
- **Model Identifier:** `all-MiniLM-L6-v2` (384-dimensional dense vectors)
- **Role:** Computes semantic similarity for `answer_relevancy` and semantic correctness.
- **Runtime:** Local `HuggingFaceEmbeddings` with `local_files_only=True` (zero network dependency; loads in 0.33s from local disk cache).

---

## 4. Retrieval Context Interfaces for Ragas

Ragas requires paired query, retrieved context chunks, generated response, and reference answer. In MediScanAI, context chunks are sourced directly from:
1. **Phase B Verified Evaluation Records:** `evaluation/results/eval_evidence_verified_both_20261015_102208/per_case_results.jsonl`.
   - Contains all 50 benchmark cases with exact baseline hybrid retrieval items (`channel == "baseline"`) and graph retrieval items (`channel == "graph"`).
   - Preserves composite evidence IDs (`drug_<id>`, `disease_chunk_<id>`), ranks, cross-encoder scores, and evidence excerpts.
2. **MultiRetriever & GraphRetriever APIs:** `app/retriever.py` and `app/graph/retriever.py` remain accessible as fallback live query interfaces.

---

## 5. Summary of Smoke Test Results

All 5 automated smoke-test components passed cleanly:
1. **Adapter Validation:** Verified that malformed records (missing query, empty contexts, blank response) are rejected with descriptive exceptions.
2. **Embedding Model:** `all-MiniLM-L6-v2` loaded locally and embedded test text into 384-dim vectors in 6.2s (including initial disk read).
3. **Judge LLM Connectivity:** `llama3.1:8b` via Ollama responded to probe prompt in 460ms.
4. **Metric Execution on Synthetic Fixture:** Evaluated synthetic non-clinical sample (`SYNTHETIC-FIXTURE-001`, Eiffel Tower query):
   - `faithfulness`: **1.0000**
   - `answer_relevancy`: **1.0000**
5. **Benchmark Structural Check:** Successfully mapped 2 benchmark reference records (`MED-BENCH-001` and `MED-BENCH-017`) through the adapter into compliant Ragas HuggingFace dataset objects without generating or scoring benchmark responses.

Overall status: **`PASSED`**.
