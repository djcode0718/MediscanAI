# MediScanAI Phase D.1 — Faithfulness-First Hybrid Retrieval Engineering

## 1. Overview & Objectives

Phase D.1 executes foundational hybrid retrieval engineering for MediScanAI, focusing on:
1. **Experiment D1-1:** Replacing destructive generic SymSpell text normalization with a medical-aware tokenizer that preserves brand names, active substances, salt forms, and dosage units.
2. **Experiment D1-2:** Activating the 58,332-record `drug_dict` index as an active text-query retrieval channel.
3. **Experiment D1-3:** Section-aware passage reranking and calibrated relevance thresholding ($\tau$) to eliminate forced nearest-neighbor hallucinations.
4. **OCR-Only Use Case:** Establishing first-class support for medicine image uploads without user-provided text, including readability scoring and uncertainty communication.
5. **Deterministic Retrieval Benchmarking:** Measuring Recall@5/10, Hit Rate@5/10, MRR@10, and nDCG@10 across stratified Development (30), Validation (10), and Held-Out Test (10) splits.
6. **Safety Regression Suite:** 12-case regression battery covering negative controls, chest pain emergency triage (`MED-BENCH-038`), stroke warning signs, and pediatric poisoning.

---

## 2. Artifacts & Deliverables Index

| Artifact | Format | Description |
| :--- | :--- | :--- |
| [`implementation_report.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/implementation_report.md) | Markdown | Initial audit verifying Phase D.0 defect claims directly against code. |
| [`experiment_manifest.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/experiment_manifest.json) | JSON | Experiment metadata, Git commit SHA, model configs, and splits. |
| [`baseline_metrics.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/baseline_metrics.json) | JSON | Reproducible metrics for the legacy baseline (`MultiRetriever`) on Dev and Val splits. |
| [`experiment_metrics.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/experiment_metrics.json) | JSON | Empirical metrics for D1-1, D1-2, threshold calibration grid, and D1-Combined splits. |
| [`case_level_retrieval_results.jsonl`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/case_level_retrieval_results.jsonl) | JSONL | Detailed per-case retrieval logs, latencies, ranks, and grades across all 50 cases. |
| [`ocr_only_test_results.jsonl`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/ocr_only_test_results.jsonl) | JSONL | Evaluation of 5 realistic OCR scenarios (strips, blister packs, blurry labels, multi-agents). |
| [`safety_regression_results.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/safety_regression_results.json) | JSON | Results of 12-case safety regression suite (Pass: 9, Fail: 3). |
| [`failure_analysis.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/failure_analysis.md) | Markdown | Technical post-mortem on negative control framing word leakage and held-out gap. |
| [`integrity_report.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/integrity_report.json) | JSON | Formal gate evaluations and Phase D.1 compliance verdict. |
| [`medical_tokenizer.py`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/medical_tokenizer.py) | Python | Non-destructive medical tokenizer and regex normalizer. |
| [`experimental_retriever.py`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/experimental_retriever.py) | Python | Experimental hybrid retriever supporting baseline and D.1 feature flags. |
| [`ocr_evaluator.py`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/ocr_evaluator.py) | Python | OCR entity extraction, readability scoring, and query generator. |
| [`safety_suite.py`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/safety_suite.py) | Python | Safety regression test case definitions and evaluation logic. |
| [`run_experiments.py`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_d_1/run_experiments.py) | Python | Master experiment execution harness. |

---

## 3. How to Reproduce

Execute the master evaluation harness within the project root:

```bash
/Users/sj/miniforge3/envs/med-env/bin/python evaluation/retrieval/phase_d_1/run_experiments.py
```

### Invariant Checks:
- `evaluation/benchmark/gold_judgments.jsonl` remains strictly **0 bytes**.
- Zero modifications made to original source JSONL files or FAISS indexes.
- `entity_resolution/` was never accessed or referenced.
