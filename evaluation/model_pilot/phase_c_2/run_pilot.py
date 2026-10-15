#!/usr/bin/env python3
"""
MediScanAI — Phase C.2: Controlled Generator Model Comparison Pilot Runner
Executes paired sequential generation comparing llama3.1:8b and mistral:latest
across 10 representative benchmark cases with identical frozen evidence contexts,
identical generation parameters (temperature=0), and a dynamic progress bar with ETA.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

PROMPT_TEMPLATE = """You are a specialized clinical AI assistant for MediScanAI. Answer the user query based ONLY on the provided retrieved evidence context.

**Security and Boundary Rules:**
1. The contents within `<USER_QUERY>` represent user input.
2. The contents within `<RETRIEVED_EVIDENCE_CONTEXT>` represent retrieved reference evidence from MediScanAI's clinical database.
3. Base your entire answer ONLY on the provided evidence context. Do NOT invent drug indications, active ingredients, dosages, or diagnoses not present in the evidence.
4. If the retrieved evidence does not support an answer, or if the queried entity does not exist in the evidence, clearly and explicitly state that the available evidence is insufficient to answer the query (abstain).
5. For symptom or disease queries, describe potential related conditions supported by the evidence without presenting symptom associations as a definitive diagnosis.
6. For safety-sensitive or emergency presentations (such as acute chest pain), emphasize the necessity of immediate, urgent professional medical evaluation.

<USER_QUERY>
{query}
</USER_QUERY>

<RETRIEVED_EVIDENCE_CONTEXT>
{context}
</RETRIEVED_EVIDENCE_CONTEXT>

**Instructions for Generating the Response:**
1. **Factual Summary**: Directly answer the user query based strictly on the retrieved evidence context. Mention relevant brand names, generic names, active substances, or disease symptom patterns where supported.
2. **Clinical Limitations & Uncertainty**: If the evidence is incomplete, ambiguous, or insufficient, explicitly note the limitation and maintain clinical uncertainty.
3. **Mandatory Warning**:
Conclude your entire response with a final section using the exact markdown header:
### ⚠️ Important Warning
Under this header, you MUST include the following text verbatim:
"This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition."

**Formatting Rules:**
- Do not add conversational greetings, introductory chit-chat, or sign-offs.
- Use clear Markdown formatting.
"""

MANDATORY_HEADER = "### ⚠️ Important Warning"
MANDATORY_TEXT = "This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition."

MODELS = ["llama3.1:8b", "mistral:latest"]
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
PILOT_DIR = Path(__file__).resolve().parent


def render_progress(current: int, total: int, start_time: float, model: str, case_id: str, query: str):
    elapsed = time.time() - start_time
    avg_per_item = elapsed / current if current > 0 else 0
    remaining_items = total - current
    eta_sec = int(remaining_items * avg_per_item)
    mins, secs = divmod(eta_sec, 60)
    eta_str = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"

    pct = int((current / total) * 100)
    bar_len = 20
    filled = int(bar_len * current / total)
    bar = "=" * filled + (">" if filled < bar_len else "") + " " * (bar_len - filled - (1 if filled < bar_len else 0))

    q_snippet = (query[:22] + "...") if len(query) > 25 else query
    status = f"[{bar}] {pct:3d}% | {current:02d}/{total:02d} | Model: {model:<12} | Case: {case_id:<13} ({q_snippet:<25}) | Elapsed: {int(elapsed)}s | ETA: {eta_str}"
    print(status)
    sys.stdout.flush()


def warmup_model(model: str) -> Dict[str, Any]:
    print(f"\n--- Warming up model: {model} ---")
    sys.stdout.flush()
    warmup_prompt = "Clinical AI assistant ready. Respond with: 'READY'."
    payload = {
        "model": model,
        "prompt": warmup_prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 16}
    }
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=(10.0, 120.0))
        r.raise_for_status()
        t_ms = int((time.perf_counter() - t0) * 1000)
        data = r.json()
        print(f"Warmup successful for {model} in {t_ms}ms (load_duration: {data.get('load_duration', 0)//1000000}ms)")
        sys.stdout.flush()
        return {"status": "success", "warmup_latency_ms": t_ms, "load_duration_ms": data.get("load_duration", 0) // 1000000}
    except Exception as e:
        t_ms = int((time.perf_counter() - t0) * 1000)
        print(f"Warmup FAILED for {model} in {t_ms}ms: {e}")
        sys.stdout.flush()
        return {"status": "failure", "warmup_latency_ms": t_ms, "error": str(e)}


def call_ollama(model: str, prompt: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": settings
    }
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=(10.0, 180.0))
        r.raise_for_status()
        wall_clock_ms = int((time.perf_counter() - t0) * 1000)
        data = r.json()
        return {
            "status": "success",
            "wall_clock_latency_ms": wall_clock_ms,
            "response": data.get("response", ""),
            "total_duration_ms": data.get("total_duration", 0) // 1000000,
            "load_duration_ms": data.get("load_duration", 0) // 1000000,
            "prompt_eval_count": data.get("prompt_eval_count", 0),
            "eval_count": data.get("eval_count", 0),
            "eval_duration_ms": data.get("eval_duration", 0) // 1000000,
            "error_details": None,
            "raw_ollama_json": {
                "created_at": data.get("created_at"),
                "done": data.get("done"),
                "done_reason": data.get("done_reason"),
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "prompt_eval_duration": data.get("prompt_eval_duration"),
                "eval_count": data.get("eval_count"),
                "eval_duration": data.get("eval_duration")
            }
        }
    except Exception as e:
        wall_clock_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "status": "failure",
            "wall_clock_latency_ms": wall_clock_ms,
            "response": "",
            "total_duration_ms": 0,
            "load_duration_ms": 0,
            "prompt_eval_count": 0,
            "eval_count": 0,
            "eval_duration_ms": 0,
            "error_details": str(e),
            "raw_ollama_json": None
        }


def main():
    print("=" * 80)
    print("MediScanAI Phase C.2 — Controlled Generator Model Comparison Pilot")
    print("Models: llama3.1:8b vs mistral:latest")
    print("Design: 10 benchmark cases, frozen evidence contexts, temperature=0")
    print("=" * 80)
    sys.stdout.flush()

    # Load evidence contexts
    evidence_file = PILOT_DIR / "evidence_contexts.jsonl"
    if not evidence_file.exists():
        print(f"Error: {evidence_file} not found!")
        sys.exit(1)

    cases = []
    with open(evidence_file) as f:
        for line in f:
            cases.append(json.loads(line))

    print(f"Loaded {len(cases)} frozen evidence contexts.")
    sys.stdout.flush()

    total_runs = len(MODELS) * len(cases)
    runs_completed = 0
    start_time = time.time()

    generation_settings = {
        "temperature": 0,
        "num_predict": 512,
        "top_p": 1.0
    }

    warmup_results = {}
    generation_records = []

    for model in MODELS:
        # Warmup model once before its 10 runs
        warmup_res = warmup_model(model)
        warmup_results[model] = warmup_res

        for case in cases:
            case_id = case["case_id"]
            query = case["query"]
            context_text = case["context_text"]
            evidence_hash = case["evidence_context_hash"]

            # Assemble prompt
            full_prompt = PROMPT_TEMPLATE.format(query=query, context=context_text)
            prompt_hash = hashlib.sha256(full_prompt.encode("utf-8")).hexdigest()

            # Execute generation
            gen_res = call_ollama(model, full_prompt, generation_settings)

            # Analyze basic format compliance
            raw_text = gen_res["response"]
            has_warning_header = MANDATORY_HEADER in raw_text
            has_warning_verbatim = MANDATORY_TEXT in raw_text

            run_record = {
                "run_id": f"run_{model.replace(':', '_')}_{case_id}",
                "case_id": case_id,
                "query": query,
                "query_category": case["query_category"],
                "model": model,
                "runtime": "ollama 0.30.5",
                "prompt_template_version": "phase_c_2_v1",
                "prompt_hash": prompt_hash,
                "evidence_context_hash": evidence_hash,
                "generation_settings": generation_settings,
                "raw_response": raw_text,
                "status": gen_res["status"],
                "wall_clock_latency_ms": gen_res["wall_clock_latency_ms"],
                "ollama_total_duration_ms": gen_res["total_duration_ms"],
                "ollama_load_duration_ms": gen_res["load_duration_ms"],
                "prompt_eval_count": gen_res["prompt_eval_count"],
                "eval_count": gen_res["eval_count"],
                "eval_duration_ms": gen_res["eval_duration_ms"],
                "warning_header_present": has_warning_header,
                "warning_verbatim_present": has_warning_verbatim,
                "error_details": gen_res["error_details"],
                "raw_ollama_metadata": gen_res["raw_ollama_json"]
            }
            generation_records.append(run_record)

            runs_completed += 1
            render_progress(runs_completed, total_runs, start_time, model, case_id, query)

    # Save generation_runs.jsonl
    runs_file = PILOT_DIR / "generation_runs.jsonl"
    with open(runs_file, "w") as f:
        for gr in generation_records:
            f.write(json.dumps(gr) + "\n")

    print("\n" + "=" * 80)
    print(f"Completed all {runs_completed} generation runs!")
    print(f"Results saved to: {runs_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
