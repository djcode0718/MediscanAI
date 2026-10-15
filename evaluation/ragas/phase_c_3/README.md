# Phase C.3 — Ragas Infrastructure Setup

**Directory:** `evaluation/ragas/phase_c_3/`  
**Purpose:** Validated environment, model configuration, dataset adapter, metric contracts, and smoke tests for MediScanAI's upcoming Phase C.4 paired RAG evaluation.

---

## 1. Directory Manifest

- `setup_report.md`: Complete environment audit, package resolution analysis, and model role specifications.
- `metric_contract.md`: Formal eligibility matrix, computational formulas, and input schemas for Ragas metrics.
- `model_configuration.json`: Generator, judge, and embedding configurations (strictly excluding API secrets).
- `requirements-evaluation.txt`: Pin-stabilized evaluation dependency manifest.
- `dataset_adapter.py`: Standalone adapter translating benchmark records to Ragas HuggingFace Datasets and EvaluationDatasets.
- `smoke_test.py`: Reproducible 5-stage verification script.
- `smoke_test_results.json`: Empirical smoke-test execution results.
- `integrity_report.json`: Verification manifest with SHA-256 hashes and compliance attestations.
- `README.md`: This file.

---

## 2. Environment Setup

All evaluation dependencies are installed and verified in Conda environment `med-env`:

```bash
# Activate target environment
conda activate med-env

# Verify pin-stabilized packages
pip install -r evaluation/ragas/phase_c_3/requirements-evaluation.txt
```

### Core Dependency Versions
- `ragas`: `0.2.15`
- `datasets`: `3.6.0`
- `langchain`: `1.4.6`
- `langchain-core`: `1.6.10`
- `langchain-community`: `0.3.31`
- `sentence-transformers`: `5.1.0`
- `transformers`: `4.56.1`
- `huggingface-hub`: `0.36.2`
- `pydantic`: `2.11.9`
- `torch`: `2.8.0`

---

## 3. How to Run the Smoke Test

Execute the standalone smoke test from the repository root:

```bash
conda run -n med-env python evaluation/ragas/phase_c_3/smoke_test.py
```

The script runs 5 automated checks:
1. Adapter validation and error handling on malformed records.
2. Local offline loading of `all-MiniLM-L6-v2` embeddings.
3. Local connectivity to `llama3.1:8b` via Ollama (`http://localhost:11434`).
4. End-to-end evaluation of `faithfulness` and `answer_relevancy` on a synthetic non-clinical fixture.
5. Structural schema validation on 2 benchmark reference records without generating benchmark responses.

---

## 4. Key Architectural Decisions

1. **Generator:** `llama3.1:8b` via local Ollama (`temperature=0`). Selected in Phase C.2 due to strict context grounding and zero parametric hallucination.
2. **Judge:** `llama3.1:8b` via `ChatOllama` / `LangchainLLMWrapper`. Validated to strictly adhere to integer verdicts required by Ragas Pydantic schemas (unlike `mistral:latest` which outputted float verdicts).
3. **Embeddings:** `all-MiniLM-L6-v2` via `HuggingFaceEmbeddings` / `LangchainEmbeddingsWrapper`. Runs 100% locally from disk cache.
4. **Reference Answers:** AI-assisted research references from `evaluation/benchmark/narrative_references/reference_answers.jsonl` (`human_reviewed=False`, `clinical_reviewed=False`).

---

## 5. Absolute Restrictions Observed

- `entity_resolution/` was strictly off-limits and was never touched.
- `evaluation/benchmark/gold_judgments.jsonl` remains exactly 0 bytes.
- Zero benchmark responses were generated in this phase.
- No production code was modified.
