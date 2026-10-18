# MediScanAI Phase 1.1 — Repository & Configuration Provenance Audit

**Evaluation Phase:** Phase 1.1 Baseline Audit  
**Date:** October 17, 2026  
**Auditor:** Autonomous Systems Baseline & Evaluation Specialist  
**Artifact Path:** `evaluation/retrieval/phase_1_1_baseline_audit/repository_configuration_audit.md`  

---

## 1. Executive Summary & Purpose

Before initiating pipeline optimizations or clinical evaluation campaigns, this audit establishes the exact provenance of code, configuration, runtime environments, models, and data artifacts currently present in the repository.

### Key Audit Finding
> [!IMPORTANT]
> **Production vs. Experimental Pipeline Disconnection:**  
> The production retrieval implementation in [`app/retriever.py`](file:///Users/sj/Documents/mediscanai/app/retriever.py) is the **legacy uncalibrated baseline** (BM25 + FAISS Dense + RRF + CrossEncoder `ms-marco-MiniLM-L-6-v2`). It contains **none** of the Phase D innovations (`IntentRouter`, `SectionAwareReranker`, formulation token stripping, upstream lexical gating, or calibrated score thresholding $\tau = -0.5$).  
> All Phase D.2.c improvements (`CFG-04-D2C-ADAPTIVE-FINAL`, config hash `f3937376cd191ee7`) remain **isolated experiments** inside [`evaluation/retrieval/phase_d_2_c/`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_2_c/).

---

## 2. Repository State & Working Tree Provenance

- **Current Git Branch:** `feat/retrieval-evaluation`
- **Current HEAD Commit Hash:** `40ba53b24b8afefe8ea45188f2f2eaa921d2d548`
- **Author / Date:** `djcode0718 <rickey.chikki@gmail.com>`, Fri Oct 16 18:09:43 2026 +0530
- **Working-Tree Status:**
  - Before Audit: Clean working tree; `.gitignore` updated to exclude large case-level evaluation JSONL run dumps (`evaluation/retrieval/**/*.jsonl`).
  - Production code status: Zero changes to [`app/`](file:///Users/sj/Documents/mediscanai/app/) or [`backend/`](file:///Users/sj/Documents/mediscanai/backend/).
  - Absolute Boundary Integrity: Directory `entity_resolution/` was never inspected, listed, or referenced.
  - Benchmark Invariant: [`evaluation/benchmark/gold_judgments.jsonl`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/gold_judgments.jsonl) verified at exactly **0 bytes**.

---

## 3. Retrieval Architecture & Configuration Audit

### Production Configuration (`app/retriever.py`)
- **Code Path:** [`app/retriever.py`](file:///Users/sj/Documents/mediscanai/app/retriever.py)
- **Pipeline Structure:**
  1. Input normalization: `normalize_text()`
  2. Embedding: `all-MiniLM-L6-v2` via `app.embeddings.embed_texts` (384-dimensional dense vectors)
  3. Dense Search: FAISS IndexFlatIP (cosine similarity) with candidate pool size `max(15, top_k * 3)`
  4. Sparse Search: Self-contained pure-Python BM25 Index ($k_1=1.5, b=0.75$)
  5. Rank Fusion: Reciprocal Rank Fusion ($k=60$)
  6. Reranking: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Missing Safeguards in Production:**
  - No `IntentRouter`: No emergency red-flag interception, no fictional negative control blocking, no symptom channel isolation.
  - No Score Thresholding: Raw candidates are returned regardless of cross-encoder confidence, creating false positive exposure on unanswerable queries.
  - No Formulation Normalizer: Exact string mismatch on queries like `"Metformin 500mg tablets"`.

### Selected Experimental Configuration (`CFG-04-D2C-ADAPTIVE-FINAL`)
- **Code Path:** [`evaluation/retrieval/phase_d_2_c/`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_2_c/)
- **Configuration Hash:** `f3937376cd191ee7`
- **Pipeline Components:**
  1. `IntentRouter`: Upstream Lexical Verification Gate + Emergency Red-Flag Triage + OCR Readability Gating
  2. Formulation Token Normalizer: Strips trailing dosage/formulation tokens (`500mg`, `tablets`) prior to catalog lookup
  3. Experimental Retriever: Hybrid BM25 + FAISS Dense + RRF with channel isolation
  4. `SectionAwareReranker`: Section-biased cross-encoder scoring prioritizing indications, contraindications, and boxed warnings
  5. Calibrated Thresholding: Text threshold $\tau = -0.5$ for clean negative control abstention (100% rejection accuracy)

---

## 4. Generator & Runtime Model Configuration

### Model Availability Audit
- **Local LLM Runtime:** Ollama (version 0.30.5 / local REST daemon on `http://localhost:11434`)
- **Active Installed Models (`ollama list`):**
  - `llama3.1:8b` (46e0c10c039e, 4.9 GB) — Installed & verified.
  - `llama3.2:3b` (a80c4f17acd5, 2.0 GB) — Installed.
  - `qwen3:8b` (500a1f067a9f, 5.2 GB) — Installed.
  - `mistral:latest` (6577803aa9a0, 4.4 GB) — Installed.
  - `nomic-embed-text:latest` (0a109f422b47, 274 MB) — Installed.
- **Model Tag Discrepancy:**
  - Intended model in user specifications: `llama3:8b` (original Meta Llama 3 8B).
  - Actual installed model: `llama3.1:8b` (Meta Llama 3.1 8B).
  - Production default setting in [`backend/core/config.py`](file:///Users/sj/Documents/mediscanai/backend/core/config.py): `OLLAMA_MODEL = "mistral"`.
  - Phase C.4 generation run model: `llama3.1:8b` (digest `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`).
- **Cloud LLM Providers:**
  - Offline mode enforced: `LLM_MODE = "offline"`.
  - Zero external API calls, paid judges, or cloud requests were executed during this audit.

---

## 5. Benchmark & Ground-Truth Artifacts Audit

- **Canonical Benchmark:** Phase A.3 Canonical 50-Case Benchmark ([`evaluation/benchmark/benchmark_cases.jsonl`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/benchmark_cases.jsonl)).
  - Split Allocation: 30 Development (`dev`), 10 Validation (`val`), 10 Held-out Test (`held_out_test`).
  - Answerability: 45 answerable cases, 5 negative controls / unanswerable distractors (`MED-BENCH-041` to `045`).
- **Narrative References:** [`evaluation/benchmark/narrative_references/reference_answers.jsonl`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/narrative_references/reference_answers.jsonl)
  - Provenance: Curated references with AI-assisted drafting followed by clinical adjudication audit.
  - **Clinical Gold Status:** *Provisional / research-grade*. Never represent these as human-reviewed board-certified gold judgments.
- **Gold Judgments File:** [`evaluation/benchmark/gold_judgments.jsonl`](file:///Users/sj/Documents/mediscanai/evaluation/benchmark/gold_judgments.jsonl) verified at **exactly 0 bytes** (sealed).

---

## 6. Synthesis & Findings Summary

1. `CFG-04-D2C-ADAPTIVE-FINAL` is an established, reproducible experimental configuration with verified hash `f3937376cd191ee7`, but it is **not yet in production code**.
2. Production code in `app/retriever.py` lacks intent routing and score calibration, making it vulnerable to negative control hallucinations.
3. Ollama model runtime contains `llama3.1:8b`, which served as the actual generator in Phase C.4.
4. All benchmark datasets and sealed gold files remain uncorrupted and intact.
