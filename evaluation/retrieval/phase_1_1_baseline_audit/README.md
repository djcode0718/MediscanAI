# MediScanAI Phase 1.1 — Evaluation Baseline, Metric Reconciliation, and Failure Audit

This directory contains the complete, isolated audit deliverables for **Phase 1.1**, establishing a trustworthy, reproducible baseline for the MediScanAI architecture prior to optimization.

---

## 1. Executive Summary & Authorizing Verdict

**Final Transition Gate Decision:**

$$\mathbf{BASELINE\_ESTABLISHED\_WITH\_WARNINGS}$$

| Audit Dimension | Core Question | Verified Finding / Outcome | Status |
| :--- | :--- | :--- | :---: |
| **Step A: Provenance** | Is Phase D.2.c in production code? | No. Production [`app/retriever.py`](file:///Users/sj/Documents/mediscanai/app/retriever.py) is legacy uncalibrated; D.2.c remains an isolated experiment in `phase_d_2_c/`. | `VERIFIED` |
| **Step B: Reconciliation** | Why did Phase C.5 and C.5.1 metrics differ? | Original C.5 numbers are mathematically correct. The C.5.1 Markdown text table had an unreproduced clerical error, contradicted by its own JSON. | `RECONCILED` |
| **Step C: Retrieval Baseline** | What are the baseline retrieval metrics? | Strict Record Recall@5: 0.4444 (dev) / 0.4444 (val) / 0.5556 (held-out). Canonical-Entity Recall@5: 0.6296 (dev) / 0.6667 (val) / 0.7778 (held-out). | `ESTABLISHED` |
| **Step D: Generation Baseline** | What is the generation baseline on D.2.c? | Zero generation runs have been performed using D.2.c retrieval evidence. Formally recorded as `BASELINE_NOT_ESTABLISHED`. | `NOT_ESTABLISHED` |
| **Step E: Latency Baseline** | What is the latency profile? | Retrieval p50 = 1,407 ms (dominated by cross-encoder). Generation p50 = 17,708 ms (Ollama `llama3.1:8b` at ~8.9 tok/s). End-to-end median = ~19.1s. | `ESTABLISHED` |
| **Step F: Contract Proposal** | What rules govern future evaluation? | Drafted formal evaluation contract covering Faithfulness, Context Precision, Context Recall, safety invariants, and offline cloud-judge governance. | `PROPOSED` |

---

## 2. Directory Index & Deliverables Manifest

| Filename | Format | Description |
| :--- | :---: | :--- |
| [`repository_configuration_audit.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/repository_configuration_audit.md) | Markdown | Complete code provenance, commit hash, model tags, runtime configurations, and production vs. experimental retrieval analysis. |
| [`c5_c5_1_metric_reconciliation.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/c5_c5_1_metric_reconciliation.md) | Markdown | Independent recalculation proving original C.5 numbers are true baseline; resolves C.5.1 markdown clerical error and timeout handling. |
| [`retrieval_baseline.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/retrieval_baseline.md) | Markdown | Definitive retrieval baseline for `CFG-04-D2C-ADAPTIVE-FINAL` across Dev, Val, and Held-Out splits, intent breakdown, and failure analysis. |
| [`retrieval_failure_inventory.csv`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/retrieval_failure_inventory.csv) | CSV | Granular inventory of all 24 retrieval misses across development, validation, and held-out test splits. |
| [`generation_baseline.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/generation_baseline.md) | Markdown | Audit establishing `BASELINE_NOT_ESTABLISHED` for current retrieval configuration, analyzing historical C.4/C.5 generation capabilities. |
| [`generation_failure_inventory.csv`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/generation_failure_inventory.csv) | CSV | Categorized failure inventory of historical generation anomalies (emergency guidance dilution, context confusion, timeouts). |
| [`latency_baseline.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/latency_baseline.md) | Markdown | Component-by-component timing breakdown (embed, FAISS, BM25, RRF, cross-encoder, prompt processing, generation) and bottlenecks. |
| [`proposed_evaluation_contract.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/proposed_evaluation_contract.md) | Markdown | Comprehensive metric contract defining Faithfulness, Context Precision/Recall, record vs canonical matching, safety invariants, and judge governance. |
| [`baseline_manifest.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/baseline_manifest.json) | JSON | Machine-readable manifest capturing all verified metrics, hashes, model specs, data paths, and split denominators. |
| [`integrity_report.json`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/integrity_report.json) | JSON | Audit compliance certificate verifying all strict restrictions and system invariants. |
| [`final_phase_1_1_report.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/final_phase_1_1_report.md) | Markdown | Master synthesis report: what is working, what is failing, what remains unknown, impact analysis, and ranked Phase 1.2 proposal. |
| [`README.md`](file:///Users/sj/Documents/mediscanai/evaluation/retrieval/phase_1_1_baseline_audit/README.md) | Markdown | This navigation index and executive guide. |

---

## 3. Strict Integrity Invariants Certification

Throughout Phase 1.1:
- `entity_resolution/` was **never inspected, read, searched, listed, or referenced**.
- `evaluation/benchmark/gold_judgments.jsonl` remains **strictly 0 bytes**.
- Zero production files under [`app/`](file:///Users/sj/Documents/mediscanai/app/) or [`backend/`](file:///Users/sj/Documents/mediscanai/backend/) were modified.
- Zero source JSONL datasets or FAISS indexes were modified.
- Prior phase artifacts (A, B, C, D.0, D.1, D.2.a-c, D.2.c-Final) were preserved without modification.
- Zero cloud API calls or paid external judges were utilized.
- Zero packages or runtime dependencies were installed or upgraded.
- Zero unauthorized held-out evaluations or held-out tuning runs occurred.
