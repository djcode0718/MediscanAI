# MediScanAI Candidate A6.1 — Resource Usage & Cost Instrumentation Report

**Date:** 2026-10-24 14:37:17
**Run Identifier:** `A6_1_dev40`
**Generator Model:** `ollama/llama3.1:8b` (num_ctx=8192, temp=0.0, seed=42)
**Judge Model:** `ollama/llama3.1:8b` (num_ctx=12288, temp=0, seed=42)
**Total Cases:** 40 cases (`dev_subset_40.json`)

## 1. Aggregate Usage Summary

| Stage | Provider & Model | Calls | Input Tokens | Output Tokens | Total Tokens | Avg Latency (ms) |
|---|---|---:|---:|---:|---:|---:|
| **Generator** | `ollama/llama3.1:8b` | 40 | 55,383 | 3,589 | 58,972 | 17,600.1 |
| **Judge (Live Calls)** | `ollama/llama3.1:8b` | 46 | 47,616 | 14,273 | 61,889 | — |
| **Combined** | — | 86 | 102,999 | 17,862 | 120,861 | — |

## 2. Cost Analysis & Future Cloud Comparison Schema

- **Current Local Ollama Run:** API cost is **$0.00** as all inference executed locally on Apple Silicon (M-series GPU). Local hardware and power consumption are unmonetized.
- **Projected Cloud Pricing Reference (as of Oct 2026):**
  * **Gemini 1.5 Flash:** $0.075 / 1M prompt tokens, $0.30 / 1M completion tokens.
  * **Groq Llama 3.1 8B:** $0.05 / 1M input tokens, $0.08 / 1M output tokens.
  * Projected cost for 40 dev cases on Groq: ~$0.003 (less than half a cent).

## 3. Measurement Coverage and Quality

- **Generator Metadata:** 100% provider-reported directly from Ollama runtime (`prompt_eval_count`, `eval_count`). No estimated values.
- **Judge Metadata:** Captured directly via LangChain `ChatOpenAI` callback listener from Ollama's OpenAI-compatible `/v1/chat/completions` endpoint.
- **Deterministic Cache Usage:** Invariant test cases utilize cached judgments to ensure exact replication and prevent judge jitter, while updated candidate answers trigger live evaluations.

## 4. Per-Case Resource Breakdown (First 15 Cases)

| Case ID | Category | Gen Tokens (In/Out) | Gen Latency | Judge Calls | Judge Tokens | Status |
|---|---|---:|---:|---:|---:|---|
| `E2E-035` | `medicine_only_clean_ocr` | 1398 / 92 | 17985ms | 0 | 0/0 | success |
| `E2E-042` | `medicine_only_noisy_ocr` | 1028 / 104 | 14305ms | 0 | 0/0 | success |
| `E2E-008` | `symptom_only` | 1009 / 93 | 8637ms | 0 | 0/0 | success |
| `E2E-069` | `symptom_plus_medicine_match` | 1819 / 82 | 21940ms | 2 | 2205/500 | success |
| `E2E-088` | `symptom_plus_medicine_mismatch` | 1497 / 136 | 25682ms | 2 | 1978/603 | success |
| `E2E-093` | `unanswerable` | 1285 / 33 | 13000ms | 0 | 0/0 | success |
| `E2E-032` | `medicine_only_clean_ocr` | 1241 / 133 | 18103ms | 0 | 0/0 | success |
| `E2E-044` | `medicine_only_noisy_ocr` | 1585 / 114 | 20524ms | 0 | 0/0 | success |
| `E2E-009` | `symptom_only` | 1369 / 75 | 11417ms | 2 | 1977/487 | success |
| `E2E-073` | `symptom_plus_medicine_match` | 1693 / 82 | 21268ms | 2 | 2108/560 | success |
| `E2E-082` | `symptom_plus_medicine_mismatch` | 1679 / 76 | 20674ms | 2 | 2109/625 | success |
| `E2E-100` | `unanswerable` | 1405 / 46 | 15642ms | 0 | 0/0 | success |
| `E2E-034` | `medicine_only_clean_ocr` | 1102 / 70 | 12875ms | 0 | 0/0 | success |
| `E2E-052` | `medicine_only_noisy_ocr` | 1285 / 101 | 17195ms | 0 | 0/0 | success |
| `E2E-024` | `symptom_only` | 1182 / 90 | 10732ms | 2 | 1804/671 | success |

*(Full per-case records saved to `evaluation/e2e/results/A6_1/resource_usage.jsonl`)*

