#!/usr/bin/env python3
"""
Step 0 Reproducibility Guard.
Regenerates 8 dev cases with A6 configuration and compares text against saved A6 generated answers.
"""

import json
import time
import difflib
import subprocess
from pathlib import Path

from backend.core.config import Settings
from app.core import Pipeline
from app.llm import GenerationParams
from evaluation.e2e.sanitize import answer_full

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

CASE_IDS = [
    "E2E-001", "E2E-004", "E2E-005", "E2E-008",
    "E2E-009", "E2E-021", "E2E-024", "E2E-025"
]

def run_step0():
    # 1. Load saved A6 outputs
    saved_a6 = {}
    with open(REPO_ROOT / "evaluation/e2e/results/A6/generated_cases.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["case_id"] in CASE_IDS:
                saved_a6[rec["case_id"]] = rec

    # 2. Load dataset inputs
    cases_input = {}
    with open(REPO_ROOT / "evaluation/e2e/dataset/e2e_v1.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["case_id"] in CASE_IDS:
                cases_input[rec["case_id"]] = rec

    # 3. Setup A6 pipeline
    custom_settings = Settings(
        JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
        EVIDENCE_FORMAT="compact",
        PROMPT_VERSION="v5",
        ROUTING_VERSION="v2",
        GEN_TEMPERATURE=0.0,
        GEN_SEED=42,
        OLLAMA_NUM_CTX=8192,
        OLLAMA_NUM_PREDICT=700,
        EMERGENCY_GUARDRAIL_ENABLED=False,
        NEO4J_ENABLED=False,
        SANITIZER_A61=False,
    )
    pipeline = Pipeline(settings=custom_settings)
    gen_params = GenerationParams(
        temperature=0.0,
        seed=42,
        num_ctx=8192,
        num_predict=700,
    )

    print("Running Step 0 Reproducibility Guard on 8 dev cases...")
    exact_matches = 0
    comparisons = []

    for cid in CASE_IDS:
        c_in = cases_input[cid]
        saved = saved_a6[cid]
        saved_text = saved.get("final_output", "").strip()

        print(f"Generating {cid}...", end=" ", flush=True)
        t0 = time.time()
        res = pipeline.run(
            user_text=c_in.get("user_text"),
            ocr_text_override=c_in.get("ocr_text"),
            return_trace=True,
            gen_params=gen_params,
        )
        dur = round(time.time() - t0, 2)
        gen_text = res.get("trace", {}).get("final_output", "").strip()

        is_exact = (gen_text == saved_text)
        if is_exact:
            exact_matches += 1
            diff_text = ""
            print(f"MATCH ({dur}s)")
        else:
            diff_lines = list(difflib.unified_diff(
                saved_text.splitlines(keepends=True),
                gen_text.splitlines(keepends=True),
                fromfile=f"saved_A6_{cid}",
                tofile=f"regenerated_{cid}",
            ))
            diff_text = "".join(diff_lines)
            print(f"MISMATCH ({dur}s)")

        comparisons.append({
            "case_id": cid,
            "exact_match": is_exact,
            "duration_sec": dur,
            "saved_length": len(saved_text),
            "generated_length": len(gen_text),
            "diff": diff_text
        })

    # Unload model after test
    subprocess.run(["ollama", "stop", "llama3.1:8b"], capture_output=True, check=False)

    exact_rate = round(exact_matches / len(CASE_IDS) * 100.0, 2)
    print("\n" + "="*60)
    print(f"Exact match count: {exact_matches}/{len(CASE_IDS)} ({exact_rate}%)")
    print("="*60)

    report = {
        "timestamp": time.time(),
        "total_cases": len(CASE_IDS),
        "exact_matches": exact_matches,
        "exact_match_rate_pct": exact_rate,
        "comparisons": comparisons
    }

    out_file = REPO_ROOT / "evaluation/e2e/audit/step0_reproducibility.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Saved step0 reproducibility report to {out_file}")
    return report

if __name__ == "__main__":
    run_step0()
