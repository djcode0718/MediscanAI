# Phase C.2 — MediScanAI Generator Model Comparison Pilot

**Location:** `evaluation/model_pilot/phase_c_2/`  
**Purpose:** Reproducible 10-case controlled comparison of `llama3.1:8b` vs `mistral:latest` under identical frozen retrieval contexts, identical generation instructions, and deterministic temperature (0).

---

## 1. Directory Contents

- `pilot_plan.md`: Experimental design, selection rationale, and scientific limitations.
- `selected_cases.jsonl`: Metadata and rationale for the 10 selected representative benchmark cases.
- `evidence_contexts.jsonl`: Frozen baseline hybrid retrieval contexts and SHA-256 integrity hashes.
- `generation_runs.jsonl`: Raw model outputs, Ollama execution metadata, token counts, and latencies.
- `scoring_rubric.md`: Standardized 7-dimension evaluation rubric (1–5 scale).
- `case_level_scores.csv`: Itemized case-by-case scoring across all 7 dimensions with detailed evaluator evidence.
- `model_comparison.csv`: Aggregate quantitative comparison (mean scores, latency percentiles, compliance rates).
- `failure_analysis.md`: Detailed failure mode catalog (groundedness deviations, warning omissions, abstention behavior).
- `recommendation.md`: Formal model selection decision, trade-off analysis, and Phase C.3 roadmap.
- `integrity_report.json`: Verification manifest (hashes, counts, parameter parity, file immutability).
- `run_pilot.py`: Standalone, reproducible runner script with dynamic progress bar and ETA.
- `README.md`: This file.

---

## 2. Prerequisites & Model Availability

1. **Ollama:** Version `0.30.5` or later running on `http://localhost:11434`.
2. **Local Models:**
   - `llama3.1:8b` (SHA-256: `46e0c10c039e...`)
   - `mistral:latest` (SHA-256: `6577803aa9a0...`)
   Verify via:
   ```bash
   ollama list
   ```

---

## 3. How to Reproduce

Execute the standalone pilot runner from the repository root:

```bash
python3 evaluation/model_pilot/phase_c_2/run_pilot.py
```

The runner:
1. Loads the 10 frozen evidence contexts from `evidence_contexts.jsonl`.
2. Warms up `llama3.1:8b` and runs 10 sequential queries with real-time progress, elapsed time, and ETA.
3. Warms up `mistral:latest` and runs the identical 10 queries.
4. Records raw responses, token counts, and Ollama timing metrics into `generation_runs.jsonl`.

---

## 4. Integrity Commitments

- `entity_resolution/` is strictly off-limits and was never touched.
- `evaluation/benchmark/gold_judgments.jsonl` remains strictly 0 bytes.
- All candidate queries, candidate judgments, and narrative references remain unmodified.
- No production code or prompt files were altered.
