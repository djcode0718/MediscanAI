#!/usr/bin/env python3
"""
MediScanAI Candidate Evaluation and Faithfulness Scoring Runner.
Evaluates candidate (e.g. A3, A4) against baseline (A2) across the 40 dev cases.
Uses the exact same judge config: llama3.1:8b, temp=0, seed=42, num_ctx=12288, format=json.
Reuses judge_cache.json and records all diagnostics and unsupported statements.
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import sys
import json
import time
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
from datasets import Dataset

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.evaluation import evaluate
from ragas.run_config import RunConfig

from evaluation.e2e.run_eval import TraceableFaithfulness, is_boilerplate_statement, compute_best_fuzzy_match
from evaluation.e2e.score_phase01b_faithfulness import (
    compute_cache_key,
    load_cache,
    save_cache,
    verify_ollama_state,
    JUDGE_CONFIG,
    get_stratified_order,
)

RESULTS_DIR = REPO_ROOT / "evaluation/e2e/results"


def score_faithfulness_single_candidate(
    record: Dict[str, Any],
    custom_faithfulness: TraceableFaithfulness,
    judge_wrapper: LangchainLLMWrapper,
    cache: Dict[str, Any],
) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    cid = record["case_id"]
    ans_core = record.get("answer_core", "").strip()
    contexts = record.get("retrieved_contexts", [])
    user_text = record.get("user_text", "") or f"Analyze medication: {record.get('ocr_text', '')}"

    inputs = {
        "question": user_text,
        "response": ans_core if ans_core else "No answer provided.",
        "retrieved_contexts": contexts,
    }

    cache_key = compute_cache_key("faithfulness", inputs, JUDGE_CONFIG)

    if cache_key in cache:
        cached = cache[cache_key]
        return cached["faithfulness"], cached.get("unsupported", []), cached.get("nan_reasons", {})

    ragas_ds = Dataset.from_dict({
        "question": [inputs["question"]],
        "response": [inputs["response"]],
        "retrieved_contexts": [inputs["retrieved_contexts"]],
    })

    ragas_run_cfg = RunConfig(max_workers=1, timeout=600, max_retries=2)
    judge_faithfulness = np.nan
    nan_reasons = {}
    unsupported_items = []

    try:
        scores_df = evaluate(
            dataset=ragas_ds,
            metrics=[custom_faithfulness],
            llm=judge_wrapper,
            run_config=ragas_run_cfg,
            show_progress=False,
        ).to_pandas()

        f_score = scores_df.iloc[0].get("faithfulness")
        judge_faithfulness = round(float(f_score), 4) if pd.notna(f_score) else np.nan
        if pd.isna(judge_faithfulness):
            nan_reasons["judge_faithfulness"] = "judge_returned_nan_or_empty_statements"

        if custom_faithfulness.last_verdicts_output:
            for v in custom_faithfulness.last_verdicts_output.statements:
                if int(v.verdict) == 0:
                    if not is_boilerplate_statement(v.statement):
                        f_match = compute_best_fuzzy_match(v.statement, contexts)
                        unsupported_items.append({
                            "case_id": cid,
                            "statement": v.statement,
                            "reason": v.reason,
                            "fuzzy_score": f_match,
                        })

    except Exception as e:
        err_msg = str(e)
        nan_reasons["judge_faithfulness"] = f"judge_error: {err_msg[:60]}"

    if pd.notna(judge_faithfulness):
        cache[cache_key] = {
            "faithfulness": judge_faithfulness,
            "unsupported": unsupported_items,
            "nan_reasons": nan_reasons,
        }
        save_cache(cache)

    return judge_faithfulness, unsupported_items, nan_reasons


def compute_cheap_diagnostics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    if n == 0:
        return {}

    latencies = [r.get("latency_ms", 0) for r in records]
    p_tokens = [r.get("prompt_tokens") or 0 for r in records]
    e_tokens = [r.get("evidence_tokens") or 0 for r in records]
    eval_counts = [r.get("eval_count") or 0 for r in records]
    truncated_count = sum(1 for r in records if r.get("truncated_by_length", False))
    abstained_count = sum(1 for r in records if r.get("abstained", False))
    invalid_tags_count = sum(len(r.get("invalid_tags", [])) for r in records)
    total_tags_count = sum(len(r.get("tags_found", [])) for r in records)

    routing_dist = defaultdict(int)
    for r in records:
        rt = r.get("routing_class") or r.get("case_type") or "UNKNOWN"
        routing_dist[rt] += 1

    return {
        "count": n,
        "avg_latency_ms": round(float(np.mean(latencies)), 1),
        "median_latency_ms": round(float(np.median(latencies)), 1),
        "avg_prompt_tokens": round(float(np.mean(p_tokens)), 1),
        "avg_evidence_tokens": round(float(np.mean(e_tokens)), 1),
        "avg_eval_tokens": round(float(np.mean(eval_counts)), 1),
        "truncated_count": truncated_count,
        "abstained_count": abstained_count,
        "invalid_tags_count": invalid_tags_count,
        "total_tags_count": total_tags_count,
        "routing_distribution": dict(routing_dist),
    }


def evaluate_candidate(candidate_name: str, baseline_name: str = "A2"):
    cand_dir = RESULTS_DIR / candidate_name
    base_dir = RESULTS_DIR / baseline_name

    cand_file = cand_dir / "generated_cases.jsonl"
    base_file = base_dir / "scored_results.jsonl"

    if not cand_file.exists():
        raise FileNotFoundError(f"Candidate file not found: {cand_file}")
    if not base_file.exists():
        raise FileNotFoundError(f"Baseline file not found: {base_file}")

    with open(cand_file, "r", encoding="utf-8") as f:
        cand_cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}
    with open(base_file, "r", encoding="utf-8") as f:
        base_cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    print(f"Loaded {len(cand_cases)} {candidate_name} cases and {len(base_cases)} {baseline_name} cases.")

    # 1. Cheap diagnostics
    cand_list = list(cand_cases.values())
    base_list = list(base_cases.values())

    cand_diag = compute_cheap_diagnostics(cand_list)
    base_diag = compute_cheap_diagnostics(base_list)

    print("\n📊 CHEAP DIAGNOSTICS COMPARISON:")
    print(f"  {baseline_name} Evidence tokens: avg {base_diag['avg_evidence_tokens']} | Prompt tokens: avg {base_diag['avg_prompt_tokens']} | Eval count: avg {base_diag['avg_eval_tokens']}")
    print(f"  {candidate_name} Evidence tokens: avg {cand_diag['avg_evidence_tokens']} | Prompt tokens: avg {cand_diag['avg_prompt_tokens']} | Eval count: avg {cand_diag['avg_eval_tokens']}")
    print(f"  {baseline_name} Routing: {base_diag['routing_distribution']}")
    print(f"  {candidate_name} Routing: {cand_diag['routing_distribution']}")

    # 2. Judge Evaluation
    verify_ollama_state()

    print(f"\n⚖️ Initializing judge for {candidate_name} evaluation...")
    judge_llm = ChatOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model=JUDGE_CONFIG["model"],
        temperature=JUDGE_CONFIG["temperature"],
        model_kwargs={
            "extra_body": {
                "options": {
                    "num_ctx": JUDGE_CONFIG["num_ctx"],
                    "seed": JUDGE_CONFIG["seed"],
                    "num_predict": 700,
                },
                "format": JUDGE_CONFIG["format"],
            }
        }
    )
    judge_wrapper = LangchainLLMWrapper(judge_llm)
    custom_faithfulness = TraceableFaithfulness(llm=judge_wrapper)
    cache = load_cache()
    print(f"Loaded judge cache with {len(cache)} entries.")

    ordered_case_ids = get_stratified_order(cand_list, seed=42)

    cand_scored = []
    all_unsupported = []
    t0 = time.time()
    nan_count = 0

    print(f"\n--- Scoring {candidate_name} Faithfulness ---")
    for idx, cid in enumerate(ordered_case_ids, 1):
        t_case_start = time.time()
        rec = cand_cases[cid]
        f_score, unsupp, n_reasons = score_faithfulness_single_candidate(
            rec, custom_faithfulness, judge_wrapper, cache
        )

        r_sc = dict(rec)
        r_sc["judge_faithfulness"] = f_score
        r_sc["nan_reasons"] = n_reasons
        cand_scored.append(r_sc)
        all_unsupported.extend(unsupp)

        if pd.isna(f_score):
            nan_count += 1

        dt = time.time() - t_case_start
        base_f = base_cases.get(cid, {}).get("judge_faithfulness")
        print(f"[{idx}/40] {cid} ({rec['category']}) | {candidate_name}={f_score} (base {baseline_name}={base_f}) | time={dt:.1f}s | unsupp={len(unsupp)}")

    # 3. Save Scored Candidate Files
    cand_scored_file = cand_dir / "scored_results.jsonl"
    cand_unsupp_file = cand_dir / "unsupported_statements.jsonl"

    with open(cand_scored_file, "w", encoding="utf-8") as f:
        for r in cand_scored:
            f.write(json.dumps(r) + "\n")

    with open(cand_unsupp_file, "w", encoding="utf-8") as f:
        for u in all_unsupported:
            f.write(json.dumps(u) + "\n")

    print(f"\n✅ Scored outputs saved to: {cand_scored_file}")
    print(f"✅ Unsupported statements saved to: {cand_unsupp_file} ({len(all_unsupported)} statements)")

    # 4. Generate Comparative Report
    generate_comparison_report(candidate_name, baseline_name, cand_scored, base_cases, cand_diag, base_diag, all_unsupported)


def generate_comparison_report(
    cand_name: str,
    base_name: str,
    cand_scored: List[Dict[str, Any]],
    base_cases: Dict[str, Any],
    cand_diag: Dict[str, Any],
    base_diag: Dict[str, Any],
    unsupported_items: List[Dict[str, Any]],
):
    def stats(vals):
        valid = [v for v in vals if v is not None and not np.isnan(v)]
        if not valid:
            return {"mean": 0.0, "median": 0.0, "valid_count": 0, "nan_count": len(vals)}
        arr = np.array(valid, dtype=float)
        return {
            "mean": round(float(np.mean(arr)), 4),
            "median": round(float(np.median(arr)), 4),
            "valid_count": len(valid),
            "nan_count": len(vals) - len(valid),
        }

    c_vals = [r["judge_faithfulness"] for r in cand_scored]
    b_vals = [base_cases[r["case_id"]]["judge_faithfulness"] for r in cand_scored if r["case_id"] in base_cases]

    s_c = stats(c_vals)
    s_b = stats(b_vals)

    # Per-category breakdown
    cats = sorted(list(set(r["category"] for r in cand_scored)))
    cat_rows = []
    deltas = []

    for cat in cats:
        c_sub = [r["judge_faithfulness"] for r in cand_scored if r["category"] == cat]
        b_sub = [base_cases[r["case_id"]]["judge_faithfulness"] for r in cand_scored if r["category"] == cat and r["case_id"] in base_cases]
        sc_sub = stats(c_sub)
        sb_sub = stats(b_sub)
        delta_cat = round(sc_sub["mean"] - sb_sub["mean"], 4)
        cat_rows.append({
            "category": cat,
            "count": len(c_sub),
            f"{base_name}_mean": sb_sub["mean"],
            f"{cand_name}_mean": sc_sub["mean"],
            "delta": delta_cat,
            f"{cand_name}_valid": f"{sc_sub['valid_count']}/{len(c_sub)}",
        })

    # Paired deltas on mutually valid cases
    paired_deltas = []
    wins = 0
    losses = 0
    ties = 0

    for r in cand_scored:
        cid = r["case_id"]
        cf = r["judge_faithfulness"]
        bf = base_cases.get(cid, {}).get("judge_faithfulness")
        if pd.notna(cf) and pd.notna(bf):
            d = round(cf - bf, 4)
            paired_deltas.append(d)
            if d > 0.001:
                wins += 1
            elif d < -0.001:
                losses += 1
            else:
                ties += 1

    mean_paired_delta = round(float(np.mean(paired_deltas)), 4) if paired_deltas else 0.0

    report_path = RESULTS_DIR / f"{cand_name}_EVAL_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# MediScanAI {cand_name} Evaluation Report (vs {base_name})\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Evaluator:** `SELF-JUDGED (llama3.1:8b)`\n")
        f.write(f"**Dataset:** `dev_subset_40.json` (40 frozen development cases)\n\n")

        f.write("## 1. Overall Faithfulness Summary\n\n")
        f.write(f"| Metric | {base_name} Baseline | {cand_name} Candidate | Delta |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| **Mean Faithfulness** | **{s_b['mean']:.4f}** | **{s_c['mean']:.4f}** | **{s_c['mean'] - s_b['mean']:+.4f}** |\n")
        f.write(f"| Median Faithfulness | {s_b['median']:.4f} | {s_c['median']:.4f} | {s_c['median'] - s_b['median']:+.4f} |\n")
        f.write(f"| Valid Cases (non-NaN) | {s_b['valid_count']}/40 | {s_c['valid_count']}/40 | {s_c['valid_count'] - s_b['valid_count']:+d} |\n")
        f.write(f"| NaN Count | {s_b['nan_count']} | {s_c['nan_count']} | {s_c['nan_count'] - s_b['nan_count']:+d} |\n")
        f.write(f"| Paired Mean Delta | - | - | {mean_paired_delta:+.4f} |\n")
        f.write(f"| Wins / Losses / Ties | - | - | {wins} wins / {losses} losses / {ties} ties |\n\n")

        f.write("## 2. Category-Level Faithfulness Breakdown\n\n")
        f.write(f"| Category | N | {base_name} Mean | {cand_name} Mean | Delta | Valid |\n")
        f.write("|---|---|---|---|---|---|\n")
        for cr in cat_rows:
            f.write(f"| `{cr['category']}` | {cr['count']} | {cr[f'{base_name}_mean']:.4f} | {cr[f'{cand_name}_mean']:.4f} | {cr['delta']:+.4f} | {cr[f'{cand_name}_valid']} |\n")
        f.write("\n")

        f.write("## 3. Cheap Diagnostics and Resource Metrics\n\n")
        f.write(f"| Metric | {base_name} | {cand_name} | Change |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| Avg Latency (ms) | {base_diag['avg_latency_ms']:.1f} | {cand_diag['avg_latency_ms']:.1f} | {cand_diag['avg_latency_ms'] - base_diag['avg_latency_ms']:+.1f} |\n")
        f.write(f"| Avg Prompt Tokens | {base_diag['avg_prompt_tokens']:.1f} | {cand_diag['avg_prompt_tokens']:.1f} | {cand_diag['avg_prompt_tokens'] - base_diag['avg_prompt_tokens']:+.1f} |\n")
        f.write(f"| Avg Evidence Tokens | {base_diag['avg_evidence_tokens']:.1f} | {cand_diag['avg_evidence_tokens']:.1f} | {cand_diag['avg_evidence_tokens'] - base_diag['avg_evidence_tokens']:+.1f} |\n")
        f.write(f"| Avg Eval Tokens | {base_diag['avg_eval_tokens']:.1f} | {cand_diag['avg_eval_tokens']:.1f} | {cand_diag['avg_eval_tokens'] - base_diag['avg_eval_tokens']:+.1f} |\n")
        f.write(f"| Truncated Generations | {base_diag['truncated_count']} | {cand_diag['truncated_count']} | {cand_diag['truncated_count'] - base_diag['truncated_count']:+d} |\n")
        f.write(f"| Abstained Generations | {base_diag['abstained_count']} | {cand_diag['abstained_count']} | {cand_diag['abstained_count'] - base_diag['abstained_count']:+d} |\n")
        f.write(f"| Invalid Citation Tags | {base_diag['invalid_tags_count']} | {cand_diag['invalid_tags_count']} | {cand_diag['invalid_tags_count'] - base_diag['invalid_tags_count']:+d} |\n")
        f.write(f"| Total Citation Tags | {base_diag['total_tags_count']} | {cand_diag['total_tags_count']} | {cand_diag['total_tags_count'] - base_diag['total_tags_count']:+d} |\n\n")

        f.write("### Routing Distribution\n")
        f.write(f"- **{base_name}:** `{base_diag['routing_distribution']}`\n")
        f.write(f"- **{cand_name}:** `{cand_diag['routing_distribution']}`\n\n")

        base_unsupp_file = RESULTS_DIR / base_name / "unsupported_statements.jsonl"
        base_unsupp_count = sum(1 for _ in open(base_unsupp_file)) if base_unsupp_file.exists() else "N/A"

        f.write(f"## 4. Unsupported Statements Analysis ({len(unsupported_items)} statements)\n\n")
        if unsupported_items:
            f.write(f"Found {len(unsupported_items)} unsupported statements flagged by judge in {cand_name} (vs {base_unsupp_count} in {base_name}).\n\n")
            f.write("| Case ID | Statement | Reason | Fuzzy Overlap |\n")
            f.write("|---|---|---|---|\n")
            for u in unsupported_items[:25]:  # list top 25
                clean_s = u["statement"].replace("\n", " ")
                clean_r = u["reason"].replace("\n", " ")
                f.write(f"| `{u['case_id']}` | {clean_s} | {clean_r} | {u.get('fuzzy_score', 0):.2f} |\n")
        else:
            f.write("Zero unsupported statements found!\n")

    print(f"\n🎉 Comparison report generated: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Candidate Evaluation Runner")
    parser.add_argument("--candidate", default="A3", help="Candidate run identifier (e.g. A3, A4)")
    parser.add_argument("--baseline", default="A2", help="Baseline run identifier (default: A2)")
    args = parser.parse_args()

    evaluate_candidate(args.candidate, args.baseline)


if __name__ == "__main__":
    main()
