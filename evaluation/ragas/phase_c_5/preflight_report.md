# MediScanAI Phase C.5 — Preflight & Provenance Validation Report

**Phase:** C.5 (Paired Ragas Evaluation of Baseline vs Graph-Assisted Responses)  
**Timestamp:** 2026-10-15T22:35:00+05:30  
**Evaluator Environment:** `med-env` (Conda, Python 3.10.18)  
**Git Commit:** `20b679c` (`feat/retrieval-evaluation`)  
**Git Working Tree Status:** Clean (no modified tracked files; gold judgments file 0 bytes)  
**Preflight Decision:** **GO FOR EVALUATION**

---

## 1. Executive Summary

This preflight validation confirms that all input artifacts, dependency environments, cryptographic hashes, model configurations, and repository invariants meet the mandatory experimental requirements for executing Phase C.5.

All 10 preflight gates have passed with zero discrepancies. No production code, prompts, retrieval indexes, or reference answers were altered. `evaluation/benchmark/gold_judgments.jsonl` remains strictly 0 bytes.

---

## 2. Preflight Gate Verification Matrix

| Gate # | Verification Requirement | Expected Condition | Observed State | Gate Status |
| :--- | :--- | :--- | :--- | :---: |
| **Gate 1** | Canonical Case IDs | Exactly 50 unique cases | 50 unique case IDs (`MED-BENCH-001` .. `MED-BENCH-050`) | **PASS** |
| **Gate 2** | Frozen Generation Records | 100 total records (50 baseline, 50 graph-assisted) | Exactly 50 baseline and 50 graph-assisted records | **PASS** |
| **Gate 3** | Record Completeness | Valid query, answer, context, provenance | 100/100 records contain all required schema fields | **PASS** |
| **Gate 4** | Cryptographic Hashes | `raw_output_hash` and `context_hash` match raw text | 100/100 match `sha256(raw_output)` and `sha256(context_text)` | **PASS** |
| **Gate 5** | Reference Dataset Completeness | 50 unique cases, valid answerability labels | 50 cases (20 answerable, 21 caveat, 4 ambiguous, 5 unanswerable) | **PASS** |
| **Gate 6** | Reference Provenance Integrity | Non-gold attribution | 50/50 records marked `human_reviewed=False`, `clinical_reviewed=False`, `official_human_gold=False` | **PASS** |
| **Gate 7** | Gold Judgment Isolation | `gold_judgments.jsonl` untouched | File size = 0 bytes | **PASS** |
| **Gate 8** | Local Model Digest | Deterministic local LLM judge | `llama3.1:8b` (digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`) | **PASS** |
| **Gate 9** | Dependency Compatibility | Installed Ragas / LangChain stack | Ragas 0.2.15, LangChain 1.4.6, SentenceTransformers 5.1.0, Datasets 3.6.0 | **PASS** |
| **Gate 10** | Laptop & Runtime Safeguards | Sequential Ollama execution, offline embeddings | `max_workers=1`, `local_files_only=True`, atomic checkpointing | **PASS** |

---

## 3. Detailed Input Artifact Audit

### 3.1 Frozen Generation Artifacts (`evaluation/ragas/phase_c_4/`)
- `paired_responses.jsonl`: 50 paired records, each linking canonical baseline and graph-assisted outputs.
- `generation_runs.jsonl`: 100 individual generation records (50 baseline, 50 graph-assisted).
- `retrieval_contexts.jsonl`: 100 context records (50 baseline, 50 graph-assisted).
- All 100 `raw_output_hash` values match `hashlib.sha256(raw_output.encode("utf-8")).hexdigest()`.
- All 100 `context_hash` values match `hashlib.sha256(context_text.encode("utf-8")).hexdigest()`.

### 3.2 Narrative Reference Dataset (`evaluation/benchmark/narrative_references/reference_answers.jsonl`)
- 50 records corresponding to canonical benchmark query IDs.
- Answerability distribution:
  - `answerable`: 20 cases
  - `answerable_with_caveat`: 21 cases
  - `ambiguous`: 4 cases (`MED-BENCH-036`, `MED-BENCH-037`, `MED-BENCH-039`, `MED-BENCH-040`)
  - `unanswerable`: 5 cases (`MED-BENCH-041` through `MED-BENCH-045`, negative controls)
- Provenance verification: Every record explicitly contains:
  ```json
  "verification_provenance": {
    "adjudicator_type": "assistant_authored_source_backed_research",
    "human_reviewed": false,
    "clinical_reviewed": false,
    "official_human_gold": false
  }
  ```

### 3.3 Gold Isolation
- `evaluation/benchmark/gold_judgments.jsonl`: 0 bytes. Human gold labels are strictly isolated and unsimulated.

---

## 4. Evaluator Configuration & Self-Evaluation Disclosure

### 4.1 Model Specifications
- **LLM Judge:** `llama3.1:8b` via Ollama (`http://localhost:11434`)
  - **Digest:** `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`
  - **Parameters:** 8.0B parameters, `Q4_K_M` quantization, context length 131,072.
  - **Inference Parameters:** `temperature=0.0` (greedy deterministic decoding).
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
  - **Local Cache:** Enforced via `model_kwargs={"local_files_only": True}`. Zero network requests permitted.
- **Ragas Execution Configuration:**
  - `RunConfig(max_workers=1, timeout=180, max_wait=60)`
  - Strictly sequential evaluation to protect host memory and prevent Ollama socket timeouts.

### 4.2 Explicit Methodological Disclosure: Same-Model Self-Evaluation Bias
Because `llama3.1:8b` served as both the generator model in Phase C.4 and the evaluation judge model in Phase C.5:
1. **Self-Preference & Correlated Errors:** The judge may systematically prefer stylistic, structural, and syntactic patterns characteristic of Llama 3.1 8B.
2. **Shared Failure Modes:** Factual omissions or subtle hallucinations plausible to the 8B generator may be equally invisible to the 8B judge.
3. **Exploratory Status:** All Ragas scores represent relative, model-perceived comparisons and must NOT be interpreted as independent clinical certification.

---

## 5. Stop/Go Final Decision

**DECISION: GO FOR EVALUATION**  
Preflight verification is complete and fully satisfies all mandatory constraints.
