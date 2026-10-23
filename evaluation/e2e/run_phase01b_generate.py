#!/usr/bin/env python3
"""
MediScanAI Phase 01b Generation Runner (Step 5).
Runs generation for 40-case dev subset:
  - R0s: Existing R0 offline traces restricted to 40 cases (no regeneration).
  - A1:  EVIDENCE_FORMAT=compact, PROMPT_VERSION=legacy, temp=0, seed=42, num_ctx=8192
  - A2:  EVIDENCE_FORMAT=compact, PROMPT_VERSION=v2,     temp=0, seed=42, num_ctx=8192
Sequential generation with memory and timing metrics recorded per case.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.core.config import get_settings, Settings
from app.core import Pipeline, normalize_text
from app.llm import GenerationParams
from evaluation.e2e.sanitize import answer_core, answer_full, is_fast_path


DATASET_FILE = REPO_ROOT / "evaluation/e2e/dataset/e2e_v1.jsonl"
DEV_SUBSET_FILE = REPO_ROOT / "evaluation/e2e/dataset/dev_subset_40.json"
R0_RESULTS_FILE = REPO_ROOT / "evaluation/e2e/results/R0_offline/per_case_results.jsonl"
RESULTS_DIR = REPO_ROOT / "evaluation/e2e/results"


def get_ollama_ps() -> Dict[str, Any]:
    """Capture current Ollama memory and context info."""
    try:
        proc = subprocess.run(["ollama", "ps"], capture_output=True, text=True, check=True)
        lines = proc.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            # NAME ID SIZE PROCESSOR CONTEXT UNTIL
            name = parts[0]
            size = parts[2] + " " + parts[3] if len(parts) > 3 and parts[3] in ("GB", "MB") else parts[2]
            ctx = [p for p in parts if p.isdigit() and int(p) >= 1024]
            context_val = ctx[0] if ctx else "unknown"
            return {"raw": proc.stdout.strip(), "size": size, "context": context_val, "model": name}
        return {"raw": proc.stdout.strip(), "size": "unknown", "context": "unknown"}
    except Exception as e:
        return {"raw": "", "size": "unknown", "context": "unknown", "error": str(e)}


def load_dev_subset_cases() -> List[Dict[str, Any]]:
    """Loads all 40 dev subset cases preserving order in dev_subset_40.json."""
    with open(DEV_SUBSET_FILE, "r", encoding="utf-8") as f:
        dev_ids = json.load(f)["case_ids"]

    all_cases = {}
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                all_cases[item["case_id"]] = item

    return [all_cases[cid] for cid in dev_ids if cid in all_cases]


def assemble_r0s_records(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Restricts existing R0 offline traces to the 40 cases without regenerating.
    Reconstructs exact legacy retrieved evidence contexts and covers_ids.
    """
    print("\n📦 Assembling R0s run records from existing R0 traces...")
    with open(R0_RESULTS_FILE, "r", encoding="utf-8") as f:
        r0_map = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    # Initialize deterministic pipeline retriever for R0 context strings
    settings = get_settings()
    settings.NEO4J_ENABLED = False
    settings.EMERGENCY_GUARDRAIL_ENABLED = False
    pipeline = Pipeline(settings=settings)

    r0s_records = []
    for c in cases:
        cid = c["case_id"]
        r0_item = r0_map[cid]

        # Deterministic retrieval reconstruction for R0 legacy strings
        user_norm = normalize_text(c["user_text"] or "")
        ocr_text = c.get("ocr_text", "")
        retrievals_user = {}
        if user_norm:
            retrievals_user["diseases"] = pipeline.retriever.search_specific("diseases", user_norm, top_k=5)
            retrievals_user["drugs"] = pipeline.retriever.search_specific("drugs", user_norm, top_k=5)
        retrievals_ocr = {}
        if ocr_text:
            retrievals_ocr["drug_dict"] = pipeline.retriever.search_specific("drug_dict", ocr_text, top_k=5)
            retrievals_ocr["drugs_from_ocr"] = pipeline.retriever.search_specific("drugs", ocr_text, top_k=5)

        all_rets = {**retrievals_user, **retrievals_ocr}
        retrieved_contexts = []
        shown_items = []
        raw_retrieved_ids = []

        # In R0 legacy format, all retrieved items were presented in full
        item_counter = 1
        for ch_name, items in all_rets.items():
            formatted_ch = pipeline._format_retrievals({ch_name: items}).strip()
            if formatted_ch:
                retrieved_contexts.append(formatted_ch)
            for key, score, obj in items:
                raw_id = str(key)
                if ch_name == "diseases" and isinstance(obj, dict):
                    raw_chunk = obj.get("chunk", {}).get("chunk_id", obj.get("id", key))
                    raw_id = f"disease_chunk_{raw_chunk}"
                elif ch_name in ("drugs", "drugs_from_ocr") and isinstance(obj, dict) and "id" in obj:
                    raw_id = f"drug_{obj['id']}"
                elif ch_name == "drug_dict" and isinstance(obj, dict) and "id" in obj:
                    raw_id = f"drug_dict_{obj['id']}"

                raw_retrieved_ids.append(raw_id)
                shown_items.append({
                    "id": raw_id,
                    "covers_ids": [raw_id],
                    "tag": f"[E{item_counter}]",
                    "channel": ch_name,
                    "tokens": len(str(obj)) // 4,
                })
                item_counter += 1

        if not retrieved_contexts:
            retrieved_contexts = ["No retrieved evidence."]

        raw_out = r0_item.get("answer_core", "")
        fin_out = r0_item.get("answer_full", "")

        record = {
            "case_id": cid,
            "category": c["category"],
            "expected_behavior": c["expected_behavior"],
            "reference_context_ids": c.get("reference_context_ids", []),
            "equivalent_ids": c.get("equivalent_ids", []),
            "user_text": c.get("user_text", ""),
            "ocr_text": c.get("ocr_text", ""),
            "reference": c.get("reference", ""),
            "prompt": "",
            "raw_llm_output": raw_out,
            "final_output": fin_out,
            "answer_core": answer_core(raw_out),
            "answer_full": answer_full(fin_out),
            "latency_ms": r0_item.get("latency_ms", 0),
            "prompt_eval_count": r0_item.get("ollama_prompt_eval_count"),
            "eval_count": r0_item.get("ollama_eval_count"),
            "prompt_tokens": r0_item.get("prompt_tokens"),
            "evidence_tokens": sum(itm["tokens"] for itm in shown_items),
            "truncated_by_length": r0_item.get("truncated_by_length", False),
            "likely_prompt_truncated": r0_item.get("likely_prompt_truncated", False),
            "fast_path_fired": r0_item.get("fast_path_fired", False),
            "raw_retrieved_ids": raw_retrieved_ids,
            "shown_evidence_items": shown_items,
            "retrieved_contexts": retrieved_contexts,
            "citation_stats": None,
            "tags_found": [],
            "invalid_tags": [],
            "citation_pct": 0.0,
            "abstained": False,
        }
        r0s_records.append(record)

    out_dir = RESULTS_DIR / "R0s"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "generated_cases.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in r0s_records:
            f.write(json.dumps(r) + "\n")
    print(f"✅ R0s records saved: {out_file} ({len(r0s_records)} cases)")
    return r0s_records


def run_generation_experiment(
    config_name: str,
    evidence_format: str,
    prompt_version: str,
    cases: List[Dict[str, Any]],
    routing_version: str = "legacy",
    out_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Executes sequential generation on the dev or held-out cases for a specific configuration.
    """
    print(f"\n========================================================")
    print(f"🚀 Starting Generation Run: {config_name}")
    print(f"   EVIDENCE_FORMAT={evidence_format}, PROMPT_VERSION={prompt_version}, ROUTING_VERSION={routing_version}")
    print(f"   Settings: temp=0, seed=42, num_ctx=8192, num_predict=700")
    print(f"========================================================")

    out_dir = out_dir or (RESULTS_DIR / config_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "generated_cases.jsonl"
    metadata_file = out_dir / "generation_metadata.json"

    # Settings setup
    custom_settings = Settings(
        JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
        EVIDENCE_FORMAT=evidence_format,
        PROMPT_VERSION=prompt_version,
        ROUTING_VERSION=routing_version,
        GEN_TEMPERATURE=0.0,
        GEN_SEED=42,
        OLLAMA_NUM_CTX=8192,
        OLLAMA_NUM_PREDICT=700,
        EMERGENCY_GUARDRAIL_ENABLED=False,  # Dev subset contains no emergency cases
        NEO4J_ENABLED=False,
    )
    pipeline = Pipeline(settings=custom_settings)
    gen_params = GenerationParams(
        temperature=0.0,
        seed=42,
        num_ctx=8192,
        num_predict=700,
    )

    initial_ps = get_ollama_ps()
    print(f"Initial Ollama state: SIZE={initial_ps.get('size')}, CONTEXT={initial_ps.get('context')}")

    records = []
    ps_snapshots = [initial_ps]
    start_total_t = time.time()

    for idx, c in enumerate(cases, 1):
        cid = c["case_id"]
        cat = c["category"]
        print(f"[{idx}/{len(cases)}] Generating {cid} ({cat})...", end=" ", flush=True)

        t0 = time.time()
        run_res = pipeline.run(
            user_text=c["user_text"],
            ocr_text_override=c.get("ocr_text"),
            return_trace=True,
            gen_params=gen_params,
        )
        wall_time_ms = int((time.time() - t0) * 1000)

        trace = run_res.get("trace", {})
        gen_meta = trace.get("generation_meta") or {}

        raw_output = trace.get("raw_llm_output", "")
        final_output = trace.get("final_output", "")
        ans_core = answer_core(raw_output)
        ans_full = answer_full(final_output)

        evidence_items = trace.get("evidence_items", [])
        total_ev_tokens = trace.get("total_evidence_tokens")
        if total_ev_tokens is None:
            total_ev_tokens = sum(itm.get("tokens", 0) for itm in evidence_items)

        # Contexts shown to LLM: exactly the evidence strings shown to the LLM
        if prompt_version in ("v2", "v3", "v4", "v5", "v6", "v7"):
            prompt_str = trace.get("prompt", "")
            if "EVIDENCE:\n" in prompt_str:
                ev_part = prompt_str.split("EVIDENCE:\n")[1].split("TASK:")[0].strip()
                retrieved_contexts = [line.strip() for line in ev_part.split("\n") if line.strip()]
            else:
                retrieved_contexts = ["No retrieved evidence."]
        else:
            retrievals_data = trace.get("retrievals_per_channel", {})
            u_text = retrievals_data.get("user_text_retrievals", "") if isinstance(retrievals_data, dict) else ""
            o_text = retrievals_data.get("ocr_text_retrievals", "") if isinstance(retrievals_data, dict) else ""
            retrieved_contexts = [s.strip() for s in (u_text, o_text) if s and s.strip()]
            if not retrieved_contexts:
                retrieved_contexts = ["No retrieved evidence."]

        raw_retrieved_dict = trace.get("retrieved_ids", {})
        raw_ids_flat = [uid for uids in raw_retrieved_dict.values() for uid in uids]

        # Citation stats
        cit_stats = trace.get("citation_stats") or {}
        shown_ids = [itm.get("id") for itm in evidence_items]
        omitted_ids = trace.get("retrieved_but_omitted_ids", [])

        record = {
            "case_id": cid,
            "category": cat,
            "expected_behavior": c["expected_behavior"],
            "reference_context_ids": c.get("reference_context_ids", []),
            "equivalent_ids": c.get("equivalent_ids", []),
            "user_text": c.get("user_text", ""),
            "ocr_text": c.get("ocr_text", ""),
            "reference": c.get("reference", ""),
            "prompt": trace.get("prompt", ""),
            "system_prompt": trace.get("system_prompt"),
            "role_separation_mode": trace.get("role_separation_mode", "single_user"),
            "case_type": trace.get("case_type"),
            "routing_class": trace.get("case_type"),
            "raw_llm_output": raw_output,
            "final_output": final_output,
            "answer_core": ans_core,
            "answer_full": ans_full,
            "latency_ms": wall_time_ms,
            "prompt_eval_count": gen_meta.get("prompt_eval_count"),
            "eval_count": gen_meta.get("eval_count"),
            "prompt_tokens": trace.get("prompt_tokens_est", gen_meta.get("prompt_eval_count", 0)),
            "evidence_tokens": total_ev_tokens,
            "truncated_by_length": gen_meta.get("truncated_by_length", False),
            "likely_prompt_truncated": gen_meta.get("likely_prompt_truncated", False),
            "generation_error": gen_meta.get("error"),
            "fast_path_fired": trace.get("fast_path_fired", False),
            "raw_retrieved_ids": raw_ids_flat,
            "retrieved_evidence_ids": raw_ids_flat,
            "shown_evidence_items": evidence_items,
            "shown_evidence_ids": shown_ids,
            "omitted_evidence_ids": omitted_ids,
            "retrieved_contexts": retrieved_contexts,
            "citation_stats": cit_stats,
            "tags_found": cit_stats.get("tags_found", trace.get("tags_found", [])),
            "invalid_tags": cit_stats.get("invalid_tags", trace.get("invalid_tags", [])),
            "citation_pct": cit_stats.get("citation_pct", trace.get("citation_pct", 0.0)),
            "abstained": cit_stats.get("abstained", trace.get("abstained", False)),
            "effective_runtime_config": trace.get("effective_settings", {}),
        }
        records.append(record)
        print(f"done ({wall_time_ms}ms, prompt_eval={gen_meta.get('prompt_eval_count')}, eval={gen_meta.get('eval_count')})")

        if idx % 10 == 0 or idx == len(cases):
            ps_snapshots.append(get_ollama_ps())

    total_wall_sec = time.time() - start_total_t
    print(f"\nCompleted {config_name}: 40 cases in {total_wall_sec:.1f}s (avg {total_wall_sec/40:.2f}s/case).")

    # Save outputs
    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    latest_ps = get_ollama_ps()
    meta = {
        "config_name": config_name,
        "evidence_format": evidence_format,
        "prompt_version": prompt_version,
        "routing_version": routing_version,
        "total_cases": len(records),
        "total_wall_seconds": round(total_wall_sec, 2),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in records) / len(records), 1),
        "avg_prompt_tokens": round(sum((r["prompt_tokens"] or 0) for r in records) / len(records), 1),
        "avg_eval_count": round(sum((r["eval_count"] or 0) for r in records) / len(records), 1),
        "truncated_count": sum(1 for r in records if r["truncated_by_length"]),
        "ollama_ps_at_finish": latest_ps,
    }
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"✅ Generated outputs written to: {out_file}")
    return records


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MediScanAI Generation Runner")
    parser.add_argument(
        "--run",
        choices=["all", "R0s", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"],
        default="A7",
        help="Which configuration to run (default: A7)",
    )
    args = parser.parse_args()

    cases = load_dev_subset_cases()
    print(f"Loaded {len(cases)} cases from dev_subset_40.json.")

    if args.run in ("all", "R0s"):
        # 1. R0s
        assemble_r0s_records(cases)

    if args.run in ("all", "A1"):
        # 2. A1
        run_generation_experiment(
            config_name="A1",
            evidence_format="compact",
            prompt_version="legacy",
            cases=cases,
        )

    if args.run in ("all", "A2"):
        # 3. A2
        run_generation_experiment(
            config_name="A2",
            evidence_format="compact",
            prompt_version="v2",
            cases=cases,
        )

    if args.run in ("all", "A3"):
        # 4. A3: EVIDENCE_FORMAT=compact, PROMPT_VERSION=v2, ROUTING_VERSION=v2
        run_generation_experiment(
            config_name="A3",
            evidence_format="compact",
            prompt_version="v2",
            routing_version="v2",
            cases=cases,
        )

    if args.run in ("all", "A4"):
        # 5. A4: EVIDENCE_FORMAT=compact, PROMPT_VERSION=v3, ROUTING_VERSION=v2
        run_generation_experiment(
            config_name="A4",
            evidence_format="compact",
            prompt_version="v3",
            routing_version="v2",
            cases=cases,
        )

    if args.run in ("all", "A5"):
        # 6. A5: EVIDENCE_FORMAT=compact, PROMPT_VERSION=v4, ROUTING_VERSION=v2
        run_generation_experiment(
            config_name="A5",
            evidence_format="compact",
            prompt_version="v4",
            routing_version="v2",
            cases=cases,
        )

    if args.run in ("all", "A6"):
        # 7. A6: EVIDENCE_FORMAT=compact, PROMPT_VERSION=v5, ROUTING_VERSION=v2
        run_generation_experiment(
            config_name="A6",
            evidence_format="compact",
            prompt_version="v5",
            routing_version="v2",
            cases=cases,
        )

    if args.run in ("all", "A7"):
        # 8. A7: EVIDENCE_FORMAT=compact, PROMPT_VERSION=v6, ROUTING_VERSION=v2
        run_generation_experiment(
            config_name="A7",
            evidence_format="compact",
            prompt_version="v6",
            routing_version="v2",
            cases=cases,
        )

    if args.run in ("all", "A8"):
        # 9. A8: EVIDENCE_FORMAT=compact, PROMPT_VERSION=v7, ROUTING_VERSION=v2
        run_generation_experiment(
            config_name="A8",
            evidence_format="compact",
            prompt_version="v7",
            routing_version="v2",
            cases=cases,
        )

    print(f"\n🎉 Generation run '{args.run}' finished successfully!")


if __name__ == "__main__":
    main()
