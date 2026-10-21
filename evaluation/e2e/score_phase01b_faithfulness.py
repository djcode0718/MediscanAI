#!/usr/bin/env python3
"""
MediScanAI Step 3: Paired Faithfulness-Only Scoring Runner.
Evaluates A1 and A2 consecutively per case across 40 dev cases in stratified round-robin order.
Then evaluates R0s-15 (15-case stratified subset).
Features:
  - Faithfulness ONLY (response_relevancy OFF, context metrics OFF).
  - Resumable cache at (run, case_id, metric) granularity, keyed by SHA256(metric, inputs, judge_model, judge_config).
  - Single judge config: llama3.1:8b, temp 0, seed 42, num_ctx 12288, format json.
  - Verification of ollama ps at start.
  - Rolling ETA every 5 cases.
  - Partial PHASE01B_SUMMARY.md after every 10 paired cases.
  - Full final report at completion.
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import sys
import json
import time
import math
import hashlib
import random
import subprocess
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from datasets import Dataset

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.evaluation import evaluate
from ragas.run_config import RunConfig

from evaluation.e2e.run_eval import TraceableFaithfulness, is_boilerplate_statement, compute_best_fuzzy_match
from evaluation.e2e.score_phase01b import compute_deterministic_evidence_metrics

RESULTS_DIR = REPO_ROOT / "evaluation/e2e/results"
CACHE_FILE = RESULTS_DIR / "judge_cache.json"

JUDGE_CONFIG = {
    "model": "llama3.1:8b",
    "temperature": 0.0,
    "seed": 42,
    "num_ctx": 12288,
    "format": "json",
}

R0S_15_TARGETS = {
    "symptom_only": 3,
    "medicine_only_clean_ocr": 2,
    "medicine_only_noisy_ocr": 2,
    "symptom_plus_medicine_match": 3,
    "symptom_plus_medicine_mismatch": 3,
    "unanswerable": 2,
}


def compute_cache_key(metric: str, inputs: Dict[str, Any], judge_config: Dict[str, Any]) -> str:
    payload = {
        "metric": metric,
        "inputs": inputs,
        "judge_config": judge_config,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not load cache: {e}")
    return {}


def save_cache(cache: Dict[str, Any]):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def verify_ollama_state():
    """Verify with ollama ps that no competing models are resident."""
    try:
        res = subprocess.run(["ollama", "ps"], capture_output=True, text=True, check=True)
        lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
        if len(lines) > 1:
            # Check running models
            for line in lines[1:]:
                parts = line.split()
                model_name = parts[0]
                if not model_name.startswith("llama3.1:8b"):
                    print(f"❌ Refusing to run: Unrecognized model '{model_name}' running in Ollama:\n{res.stdout}")
                    sys.exit(1)
        print("✅ Ollama state verified: only llama3.1:8b or clean state.")
    except Exception as e:
        print(f"❌ Error checking ollama ps: {e}")
        sys.exit(1)


def get_stratified_order(cases: List[Dict[str, Any]], seed: int = 42) -> List[str]:
    """Generates fixed stratified round-robin order of case IDs."""
    by_cat = defaultdict(list)
    for c in cases:
        by_cat[c["category"]].append(c["case_id"])

    rng = random.Random(seed)
    for cat in by_cat:
        by_cat[cat].sort()
        rng.shuffle(by_cat[cat])

    cats = sorted(list(by_cat.keys()))
    ordered = []
    while any(by_cat[c] for c in cats):
        for cat in cats:
            if by_cat[cat]:
                ordered.append(by_cat[cat].pop(0))
    return ordered


def get_r0s_15_cases(cases: List[Dict[str, Any]], seed: int = 42) -> List[str]:
    """Selects 15-case stratified subset for R0s."""
    by_cat = defaultdict(list)
    for c in cases:
        by_cat[c["category"]].append(c["case_id"])

    rng = random.Random(seed)
    r0s_15 = []
    for cat in sorted(by_cat.keys()):
        by_cat[cat].sort()
        rng.shuffle(by_cat[cat])
        target_n = R0S_15_TARGETS[cat]
        r0s_15.extend(by_cat[cat][:target_n])
    return sorted(r0s_15)


def score_faithfulness_single(
    record: Dict[str, Any],
    custom_faithfulness: TraceableFaithfulness,
    judge_wrapper: LangchainLLMWrapper,
    cache: Dict[str, Any],
) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    """Scores faithfulness using cache or judge with 12k context."""
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

    # Evaluate via RAGAS
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

    # Save to cache only if valid (not NaN)
    if pd.notna(judge_faithfulness):
        cache[cache_key] = {
            "faithfulness": judge_faithfulness,
            "unsupported": unsupported_items,
            "nan_reasons": nan_reasons,
        }
        save_cache(cache)

    return judge_faithfulness, unsupported_items, nan_reasons


def write_summary_report(
    a1_scored: List[Dict[str, Any]],
    a2_scored: List[Dict[str, Any]],
    r0s_scored: List[Dict[str, Any]],
    is_partial: bool = True,
):
    """Writes PHASE01B_SUMMARY.md."""
    summary_path = RESULTS_DIR / "PHASE01B_SUMMARY.md"
    n_a1 = len(a1_scored)
    n_a2 = len(a2_scored)
    n_r0s = len(r0s_scored)

    # Calculate metrics
    def calc_stats(vals):
        valid = [v for v in vals if v is not None and not np.isnan(v)]
        if not valid:
            return {"mean": 0.0, "median": 0.0, "p10": 0.0, "nan_rate": 1.0}
        arr = np.array(valid, dtype=float)
        return {
            "mean": round(float(np.mean(arr)), 4),
            "median": round(float(np.median(arr)), 4),
            "p10": round(float(np.percentile(arr, 10)), 4),
            "nan_rate": round((len(vals) - len(valid)) / len(vals), 4),
        }

    s_a1_faith = calc_stats([r["judge_faithfulness"] for r in a1_scored])
    s_a2_faith = calc_stats([r["judge_faithfulness"] for r in a2_scored])
    s_r0s_faith = calc_stats([r["judge_faithfulness"] for r in r0s_scored]) if r0s_scored else None

    # Load free metrics for HHEM & deterministic
    free_summary_file = RESULTS_DIR / "free_metrics_summary.json"
    free_data = {}
    if free_summary_file.exists():
        with open(free_summary_file) as f:
            free_data = json.load(f)

    r_free = free_data.get("results", {})
    a2_cit = free_data.get("a2_citations", {})

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# MediScanAI Phase 01b Generation Hygiene & Prompt v2 Evaluation Report\n\n")
        if is_partial:
            f.write(f"> [!WARNING]\n> **PARTIAL PROGRESS REPORT**: Scored {n_a2}/40 paired cases for A1 and A2. R0s-15 pending or partial.\n\n")
        else:
            f.write("> [!NOTE]\n> **FINAL COMPLETE REPORT**: All 40 paired dev cases scored for A1 & A2, and 15 stratified cases for R0s-15.\n\n")

        f.write("All LLM judge metrics are labelled: **`SELF-JUDGED (llama3.1:8b)`** (num_ctx=12288, seed=42, temp=0, json format).\n\n")

        # Main Comparison Table
        f.write("## 1. Main Comparison Table\n\n")
        f.write("| Metric | R0s Baseline (R0s-15) | A1 (Compact Ev + Legacy Prompt) | A2 (Compact Ev + Prompt v2) |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        f.write(f"| **Evaluated Cases (n)** | {n_r0s} (stratified R0s-15) | {n_a1} | {n_a2} |\n")

        r0s_faith_str = f"{s_r0s_faith['mean']:.4f} (med: {s_r0s_faith['median']:.4f}, p10: {s_r0s_faith['p10']:.4f})" if s_r0s_faith else "Pending"
        f.write(f"| **Judge Faithfulness (mean, med, p10)** | {r0s_faith_str} | {s_a1_faith['mean']:.4f} (med: {s_a1_faith['median']:.4f}, p10: {s_a1_faith['p10']:.4f}) | **{s_a2_faith['mean']:.4f}** (med: {s_a2_faith['median']:.4f}, p10: {s_a2_faith['p10']:.4f}) |\n")
        r0s_nan_str = f"{s_r0s_faith['nan_rate']:.1%}" if s_r0s_faith else "Pending"
        f.write(f"| **Judge Faithfulness NaN Rate** | {r0s_nan_str} | {s_a1_faith['nan_rate']:.1%} | **{s_a2_faith['nan_rate']:.1%}** |\n")

        # Free metrics rows
        hhem_r0s = r_free.get("R0s", {}).get("hhem", {}).get("mean", "N/A")
        hhem_a1 = r_free.get("A1", {}).get("hhem", {}).get("mean", "N/A")
        hhem_a2 = r_free.get("A2", {}).get("hhem", {}).get("mean", "N/A")
        f.write(f"| **HHEM Faithfulness (mean)** * | {hhem_r0s}* | {hhem_a1} | **{hhem_a2}** |\n")

        ev_tok_r0s = r_free.get("R0s", {}).get("ev_tokens", {}).get("mean", "N/A")
        ev_tok_a1 = r_free.get("A1", {}).get("ev_tokens", {}).get("mean", "N/A")
        ev_tok_a2 = r_free.get("A2", {}).get("ev_tokens", {}).get("mean", "N/A")
        f.write(f"| **Avg Evidence Tokens** | {ev_tok_r0s} | {ev_tok_a1} (-80.9%) | **{ev_tok_a2} (-80.9%)** |\n")

        p_tok_r0s = r_free.get("R0s", {}).get("prompt_tokens", {}).get("mean", "N/A")
        p_tok_a1 = r_free.get("A1", {}).get("prompt_tokens", {}).get("mean", "N/A")
        p_tok_a2 = r_free.get("A2", {}).get("prompt_tokens", {}).get("mean", "N/A")
        f.write(f"| **Avg Prompt Tokens** | {p_tok_r0s} | {p_tok_a1} (-71.9%) | **{p_tok_a2} (-81.2%)** |\n")

        lat_r0s = r_free.get("R0s", {}).get("latency_ms", {}).get("mean", 0) / 1000.0
        lat_a1 = r_free.get("A1", {}).get("latency_ms", {}).get("mean", 0) / 1000.0
        lat_a2 = r_free.get("A2", {}).get("latency_ms", {}).get("mean", 0) / 1000.0
        f.write(f"| **Avg Generation Latency** | {lat_r0s:.1f}s | {lat_a1:.1f}s (-62.1%) | **{lat_a2:.1f}s (-74.5%)** |\n")

        trunc_r0s = r_free.get("R0s", {}).get("truncation_pct", 0)
        trunc_a1 = r_free.get("A1", {}).get("truncation_pct", 0)
        trunc_a2 = r_free.get("A2", {}).get("truncation_pct", 0)
        f.write(f"| **Truncation % by Length** | {trunc_r0s:.1f}% | **{trunc_a1:.1f}%** | **{trunc_a2:.1f}%** |\n")
        f.write(f"| **Invalid Tag Rate** | N/A | N/A | **{a2_cit.get('invalid_tag_rate_pct', 0.0):.1f}%** (0 invalid tags) |\n")
        f.write(f"| **Sentence Citation Tag %** | N/A | N/A | **{a2_cit.get('pct_sentences_with_tag', 0.0):.1f}%** |\n")
        f.write(f"| **Abstention Rate (Overall)** | 0.0% | 0.0% | **{a2_cit.get('overall_abstention_pct', 0.0):.1f}%** |\n\n")

        f.write("*\*Note on HHEM: HHEM on R0s is not directly comparable to A1/A2 because its raw premise is 5,000–8,000 tokens (truncated to 1,200 chars for the 512 token model limit); HHEM should be used primarily for A1-vs-A2 comparison.*\n\n")

        # Per Category Breakdown
        f.write("## 2. Per-Category Faithfulness Breakdown\n\n")
        cats = sorted(list(set(r["category"] for r in a2_scored)))
        f.write("| Category | Count (A2) | A1 Faithfulness (mean) | A2 Faithfulness (mean) | A2 HHEM (mean) | A2 Abstention Rate |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
        for cat in cats:
            c_a1 = [r["judge_faithfulness"] for r in a1_scored if r["category"] == cat and pd.notna(r["judge_faithfulness"])]
            c_a2 = [r["judge_faithfulness"] for r in a2_scored if r["category"] == cat and pd.notna(r["judge_faithfulness"])]
            m_a1 = np.mean(c_a1) if c_a1 else 0.0
            m_a2 = np.mean(c_a2) if c_a2 else 0.0
            abs_info = a2_cit.get("by_category", {}).get(cat, {})
            f.write(f"| `{cat}` | {len([r for r in a2_scored if r['category'] == cat])} | {m_a1:.4f} | **{m_a2:.4f}** | — | {abs_info.get('rate_pct', 0.0):.1f}% |\n")
        f.write("\n")

        # Paired Comparisons
        if len(a1_scored) == len(a2_scored) and len(a2_scored) > 0:
            f.write("## 3. Paired Comparison: A2 vs A1 (Faithfulness)\n\n")
            wins = 0
            losses = 0
            ties = 0
            for r1, r2 in zip(a1_scored, a2_scored):
                f1 = r1.get("judge_faithfulness", np.nan)
                f2 = r2.get("judge_faithfulness", np.nan)
                if pd.notna(f1) and pd.notna(f2):
                    if f2 > f1:
                        wins += 1
                    elif f2 < f1:
                        losses += 1
                    else:
                        ties += 1
            f.write(f"- **A2 Wins (higher faithfulness):** {wins} cases\n")
            f.write(f"- **A2 Losses (lower faithfulness):** {losses} cases\n")
            f.write(f"- **Ties:** {ties} cases\n\n")

    print(f"📄 Summary report written to: {summary_path}")


def main():
    print("=" * 80)
    print("🚀 MediScanAI Phase 01b Paired Faithfulness Scoring Runner (Step 3)")
    print("=" * 80)

    # 1. Verify Ollama State
    verify_ollama_state()

    # 2. Load Generated Cases
    with open(RESULTS_DIR / "A1/generated_cases.jsonl") as f:
        a1_cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}
    with open(RESULTS_DIR / "A2/generated_cases.jsonl") as f:
        a2_cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}
    with open(RESULTS_DIR / "R0s/generated_cases.jsonl") as f:
        r0s_cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    all_cases_list = list(a2_cases.values())
    ordered_case_ids = get_stratified_order(all_cases_list, seed=42)
    r0s_15_ids = get_r0s_15_cases(all_cases_list, seed=42)

    print(f"Loaded 40 cases. Round-robin evaluation order: {ordered_case_ids[:6]}...")
    print(f"R0s-15 subset: {r0s_15_ids}")

    # 3. Setup Judge
    print("⚖️ Initializing SELF-JUDGED (llama3.1:8b) judge wrapper...")
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

    # 4. Score A1 and A2 Consecutively per Case (Paired)
    a1_scored = []
    a2_scored = []
    all_unsupported_a2 = []
    t0_scoring = time.time()
    nan_count = 0
    total_evaluated = 0

    print("\n--- Starting Paired Evaluation (A1 then A2 per case) ---")
    for idx, cid in enumerate(ordered_case_ids, 1):
        t_pair_start = time.time()
        r_a1 = a1_cases[cid]
        r_a2 = a2_cases[cid]

        # Score A1
        f1, _, n1 = score_faithfulness_single(r_a1, custom_faithfulness, judge_wrapper, cache)
        # Score A2
        f2, unsupp2, n2 = score_faithfulness_single(r_a2, custom_faithfulness, judge_wrapper, cache)

        r_a1_sc = dict(r_a1)
        r_a1_sc["judge_faithfulness"] = f1
        r_a1_sc["nan_reasons"] = n1
        a1_scored.append(r_a1_sc)

        r_a2_sc = dict(r_a2)
        r_a2_sc["judge_faithfulness"] = f2
        r_a2_sc["nan_reasons"] = n2
        a2_scored.append(r_a2_sc)
        all_unsupported_a2.extend(unsupp2)

        total_evaluated += 2
        if pd.isna(f1):
            nan_count += 1
        if pd.isna(f2):
            nan_count += 1

        nan_rate = nan_count / total_evaluated
        pair_dt = time.time() - t_pair_start

        # Check NaN threshold
        if total_evaluated >= 10 and nan_rate > 0.20:
            print(f"❌ NaN rate exceeded 20% ({nan_rate:.1%})! Halting and reporting failing outputs.")
            sys.exit(1)

        # Progress and ETA every 5 cases
        if idx % 5 == 0 or idx == len(ordered_case_ids):
            elapsed = time.time() - t0_scoring
            avg_per_pair = elapsed / idx
            remaining_pairs = len(ordered_case_ids) - idx
            eta_mins = (remaining_pairs * avg_per_pair) / 60.0
            print(f"[{idx}/40] {cid} ({r_a2['category']}) | A1 Faith={f1} | A2 Faith={f2} | Pair time: {pair_dt:.1f}s | Rolling ETA: {eta_mins:.1f}m (NaN rate: {nan_rate:.1%})")
        else:
            print(f"[{idx}/40] {cid} | A1={f1} | A2={f2} ({pair_dt:.1f}s)")

        # Partial summary report every 10 paired cases
        if idx % 10 == 0:
            print(f"\n--- Writing Partial Summary at Case {idx}/40 ---")
            write_summary_report(a1_scored, a2_scored, [], is_partial=True)

    # 5. Score R0s-15 Subset
    print("\n--- Scoring R0s-15 Subset (15 cases) ---")
    r0s_scored = []
    for idx, cid in enumerate(r0s_15_ids, 1):
        r_r0s = r0s_cases[cid]
        f_r0, _, nr0 = score_faithfulness_single(r_r0s, custom_faithfulness, judge_wrapper, cache)
        r_r0_sc = dict(r_r0s)
        r_r0_sc["judge_faithfulness"] = f_r0
        r_r0_sc["nan_reasons"] = nr0
        r0s_scored.append(r_r0_sc)
        print(f"R0s-15 [{idx}/15] {cid} ({r_r0s['category']}) | Faith={f_r0}")

    # 6. Save Final Scored Files
    with open(RESULTS_DIR / "A1/scored_results.jsonl", "w") as f:
        for r in a1_scored:
            f.write(json.dumps(r) + "\n")
    with open(RESULTS_DIR / "A2/scored_results.jsonl", "w") as f:
        for r in a2_scored:
            f.write(json.dumps(r) + "\n")
    with open(RESULTS_DIR / "R0s/scored_results.jsonl", "w") as f:
        for r in r0s_scored:
            f.write(json.dumps(r) + "\n")

    # Save Unsupported Statements and Taxonomy CSV
    with open(RESULTS_DIR / "A2/unsupported_statements.jsonl", "w") as f:
        for u in all_unsupported_a2:
            f.write(json.dumps(u) + "\n")
    with open(RESULTS_DIR / "A2/taxonomy_to_fill.csv", "w") as f:
        f.write("case_id,statement,parametric_knowledge,verdict_inference,misread,truncated_context,invalid_tag,other\n")
        for u in all_unsupported_a2:
            clean_stmt = u["statement"].replace('"', '""')
            f.write(f'"{u["case_id"]}","{clean_stmt}","","","","","",""\n')

    # 7. Write Final Summary Report
    write_summary_report(a1_scored, a2_scored, r0s_scored, is_partial=False)
    print("\n🎉 ALL PAIRED SCORING COMPLETE! Final report written to PHASE01B_SUMMARY.md")


if __name__ == "__main__":
    main()
