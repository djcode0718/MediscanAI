#!/usr/bin/env python3
"""
MediScanAI Phase C.5 — Paired Ragas Evaluation Runner
Evaluates 50 benchmark cases under paired baseline vs graph-assisted conditions (100 total runs).
Metrics:
  - Faithfulness (N=50 pairs)
  - Answer Relevancy (N=50 pairs)
  - Context Precision (N=45 pairs; 5 negative controls ineligible)
  - Context Recall (N=45 pairs; 5 negative controls ineligible)

Enforces:
  - max_workers=1 sequential execution
  - local_files_only=True offline embeddings
  - per-case checkpointing and restartability
  - strict metric contract and explicit denominators
"""

import os
import sys
import json
import time
import math
import hashlib
import warnings
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
from datasets import Dataset

# Suppress deprecation warnings for cleaner logging
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.evaluation import evaluate
from ragas.run_config import RunConfig


BASE_DIR = Path("/Users/sj/Documents/mediscanai")
C4_DIR = BASE_DIR / "evaluation/ragas/phase_c_4"
C5_DIR = BASE_DIR / "evaluation/ragas/phase_c_5"
REF_PATH = BASE_DIR / "evaluation/benchmark/narrative_references/reference_answers.jsonl"
PAIRED_PATH = C4_DIR / "paired_responses.jsonl"
CTX_PATH = C4_DIR / "retrieval_contexts.jsonl"
GEN_PATH = C4_DIR / "generation_runs.jsonl"

SCORES_CSV = C5_DIR / "case_level_scores.csv"
DELTAS_CSV = C5_DIR / "paired_metric_deltas.csv"
AGGREGATE_JSON = C5_DIR / "aggregate_metrics.json"
FAILURES_JSONL = C5_DIR / "metric_failures.jsonl"
PROGRESS_JSON = C5_DIR / "progress.json"
MANIFEST_JSON = C5_DIR / "run_manifest.json"

NEGATIVE_CONTROL_CASES = {
    "MED-BENCH-041",
    "MED-BENCH-042",
    "MED-BENCH-043",
    "MED-BENCH-044",
    "MED-BENCH-045",
}

SCORES_HEADER = [
    "case_id",
    "query_category",
    "track",
    "query",
    "answerability",
    "faithfulness",
    "faithfulness_eligibility",
    "answer_relevancy",
    "answer_relevancy_eligibility",
    "context_precision",
    "context_precision_eligibility",
    "context_recall",
    "context_recall_eligibility",
    "failure_reason",
    "retries",
    "latency_seconds",
    "run_id",
    "context_hash",
    "response_hash",
    "timestamp",
]


def load_inputs():
    """Loads and indexes all frozen input artifacts."""
    with open(REF_PATH, "r", encoding="utf-8") as f:
        references = {r["case_id"]: r for r in (json.loads(line) for line in f if line.strip())}

    with open(CTX_PATH, "r", encoding="utf-8") as f:
        contexts = {(r["case_id"], r["condition"]): r for r in (json.loads(line) for line in f if line.strip())}

    with open(PAIRED_PATH, "r", encoding="utf-8") as f:
        paired = [json.loads(line) for line in f if line.strip()]

    return references, contexts, paired


def extract_context_chunks(context_text: str) -> List[str]:
    """Extracts individual evidence item chunks from formatted context text."""
    chunks = [
        l.strip()
        for l in context_text.split("\n")
        if l.strip()
        and not l.strip().startswith("--")
        and l.strip() != "No additional graph evidence found."
    ]
    return chunks


def init_scores_csv():
    """Initializes CSV header if file does not exist."""
    if not SCORES_CSV.exists():
        with open(SCORES_CSV, "w", encoding="utf-8") as f:
            f.write(",".join(SCORES_HEADER) + "\n")


def get_completed_runs() -> set:
    """Returns set of (case_id, track) already evaluated."""
    if not SCORES_CSV.exists():
        return set()
    df = pd.read_csv(SCORES_CSV)
    if df.empty or "case_id" not in df.columns or "track" not in df.columns:
        return set()
    return set(zip(df["case_id"], df["track"]))


def evaluate_sample_with_retry(
    dataset: Dataset,
    metric_list: list,
    judge: LangchainLLMWrapper,
    embeddings: LangchainEmbeddingsWrapper,
    run_cfg: RunConfig,
    max_retries: int = 2
) -> Tuple[Optional[Dict[str, float]], int, Optional[str]]:
    """Evaluates sample with bounded retries."""
    retries = 0
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            res = evaluate(
                dataset=dataset,
                metrics=metric_list,
                llm=judge,
                embeddings=embeddings,
                run_config=run_cfg,
                show_progress=False,
            )
            df = res.to_pandas()
            result_dict = {}
            for col in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
                if col in df.columns:
                    val = df[col].iloc[0]
                    result_dict[col] = None if (pd.isna(val) or val is None) else float(val)
                else:
                    result_dict[col] = None
            return result_dict, retries, None
        except Exception as e:
            last_error = str(e)
            retries += 1
            if attempt < max_retries:
                time.sleep(5)
    return None, retries, last_error


def run_evaluation(max_cases: Optional[int] = None):
    print("=" * 80)
    print("MediScanAI Phase C.5 — Paired Ragas Evaluation Runner")
    print("=" * 80)

    C5_DIR.mkdir(parents=True, exist_ok=True)
    init_scores_csv()

    references, contexts, paired_cases = load_inputs()
    completed_runs = get_completed_runs()
    print(f"Loaded {len(paired_cases)} paired cases, {len(completed_runs)} runs already completed.")

    judge = LangchainLLMWrapper(ChatOllama(model="llama3.1:8b", temperature=0.0))
    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"local_files_only": True}
        )
    )
    run_cfg = RunConfig(max_workers=1, timeout=180, max_wait=60)

    total_runs_target = len(paired_cases) * 2
    if max_cases:
        paired_cases = paired_cases[:max_cases]
        total_runs_target = len(paired_cases) * 2

    start_wall_time = time.time()
    run_count = len(completed_runs)

    for case_idx, p in enumerate(paired_cases, 1):
        cid = p["case_id"]
        ref_obj = references[cid]
        query = p["query"]
        category = p["query_category"]
        answerability = ref_obj.get("answerability", "answerable")
        is_negative_control = cid in NEGATIVE_CONTROL_CASES

        # Metrics list: negative controls only get faithfulness + relevancy
        if is_negative_control:
            active_metrics = [faithfulness, answer_relevancy]
            cp_elig = "ineligible_unanswerable_negative_control"
            cr_elig = "ineligible_unanswerable_negative_control"
        else:
            active_metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
            cp_elig = "eligible"
            cr_elig = "eligible"

        # Tracks: baseline and graph_assisted
        tracks = [
            ("baseline", p["baseline_run"]),
            ("graph_assisted", p["graph_assisted_run"])
        ]

        for track_name, run_data in tracks:
            if (cid, track_name) in completed_runs:
                continue

            run_start_t = time.time()
            ctx_key = (cid, track_name)
            ctx_rec = contexts[ctx_key]
            chunks = extract_context_chunks(ctx_rec["context_text"])
            response_text = run_data["raw_output"]
            ref_text = ref_obj["reference_answer"]

            sample_dict = {
                "user_input": [query],
                "response": [response_text],
                "retrieved_contexts": [chunks],
                "reference": [ref_text],
            }
            ds = Dataset.from_dict(sample_dict)

            res_scores, retries, err = evaluate_sample_with_retry(
                dataset=ds,
                metric_list=active_metrics,
                judge=judge,
                embeddings=embeddings,
                run_cfg=run_cfg,
            )

            latency = time.time() - run_start_t
            run_count += 1

            if res_scores is not None:
                f_score = res_scores.get("faithfulness")
                ar_score = res_scores.get("answer_relevancy")
                cp_score = res_scores.get("context_precision") if not is_negative_control else None
                cr_score = res_scores.get("context_recall") if not is_negative_control else None
                fail_reason = ""
            else:
                f_score = None
                ar_score = None
                cp_score = None
                cr_score = None
                fail_reason = f"Judge failure: {err}"
                # Log failure
                with open(FAILURES_JSONL, "a", encoding="utf-8") as f_fail:
                    f_fail.write(json.dumps({
                        "case_id": cid,
                        "track": track_name,
                        "error": err,
                        "retries": retries,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }) + "\n")

            row = [
                cid,
                category,
                track_name,
                f'"{query.replace(chr(34), chr(39))}"',
                answerability,
                "" if f_score is None else f"{f_score:.6f}",
                "eligible",
                "" if ar_score is None else f"{ar_score:.6f}",
                "eligible",
                "" if cp_score is None else f"{cp_score:.6f}",
                cp_elig,
                "" if cr_score is None else f"{cr_score:.6f}",
                cr_elig,
                f'"{fail_reason}"' if fail_reason else '""',
                str(retries),
                f"{latency:.2f}",
                run_data["run_id"],
                ctx_rec["context_hash"],
                run_data["raw_output_hash"],
                datetime.now(timezone.utc).isoformat(),
            ]

            # Write row immediately to CSV with flush
            with open(SCORES_CSV, "a", encoding="utf-8") as f_csv:
                f_csv.write(",".join(row) + "\n")
                f_csv.flush()

            completed_runs.add((cid, track_name))

            # Progress calculations
            elapsed = time.time() - start_wall_time
            avg_per_run = elapsed / max(1, (run_count - len(completed_runs) + 1))
            remaining_runs = total_runs_target - run_count
            eta_seconds = remaining_runs * 80  # estimate ~80s per run
            eta_min = eta_seconds / 60

            pct = (run_count / total_runs_target) * 100
            bar_len = 25
            filled_len = int(bar_len * run_count // total_runs_target)
            bar = "=" * filled_len + "-" * (bar_len - filled_len)

            print(
                f"[{run_count:3d}/{total_runs_target}] [{bar}] {pct:5.1f}% | "
                f"{cid} ({track_name:14s}) | "
                f"F:{f_score if f_score is not None else 0.0:.2f} "
                f"AR:{ar_score if ar_score is not None else 0.0:.2f} "
                f"CP:{cp_score if cp_score is not None else -1:.2f} "
                f"CR:{cr_score if cr_score is not None else -1:.2f} | "
                f"{latency:4.1f}s | ETA: {eta_min:4.1f}m"
            )

            # Update progress.json
            with open(PROGRESS_JSON, "w", encoding="utf-8") as f_prog:
                json.dump({
                    "current_case": cid,
                    "completed_runs": run_count,
                    "total_runs": total_runs_target,
                    "percent_complete": round(pct, 2),
                    "elapsed_seconds": round(elapsed, 1),
                    "estimated_remaining_seconds": round(eta_seconds, 1),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }, f_prog, indent=2)

    print("\nAll evaluation runs complete! Post-processing results...")
    post_process_evaluation()


def bootstrap_ci(deltas: np.ndarray, num_resamples: int = 1000, ci: float = 0.95, seed: int = 42) -> Tuple[float, float]:
    """Computes bootstrap confidence interval for mean delta."""
    if len(deltas) == 0:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    boot_means = [np.mean(rng.choice(deltas, size=len(deltas), replace=True)) for _ in range(num_resamples)]
    alpha = (1.0 - ci) / 2.0
    low = float(np.percentile(boot_means, alpha * 100))
    high = float(np.percentile(boot_means, (1.0 - alpha) * 100))
    return low, high


def post_process_evaluation():
    """Computes paired deltas, aggregate metrics, confidence intervals, and updates manifest."""
    df = pd.read_csv(SCORES_CSV)
    b_df = df[df["track"] == "baseline"].set_index("case_id")
    g_df = df[df["track"] == "graph_assisted"].set_index("case_id")

    paired_cases = sorted(list(set(b_df.index).intersection(set(g_df.index))))

    deltas_rows = []
    metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

    for cid in paired_cases:
        brow = b_df.loc[cid]
        grow = g_df.loc[cid]

        cat = brow["query_category"]
        ans = brow["answerability"]
        is_nc = cid in NEGATIVE_CONTROL_CASES

        d_row = {
            "case_id": cid,
            "query_category": cat,
            "answerability": ans,
        }

        for m in metrics:
            b_val = brow[m] if pd.notna(brow[m]) else None
            g_val = grow[m] if pd.notna(grow[m]) else None

            d_row[f"{m}_baseline"] = round(b_val, 6) if b_val is not None else ""
            d_row[f"{m}_graph"] = round(g_val, 6) if g_val is not None else ""

            if b_val is not None and g_val is not None:
                delta = g_val - b_val
                d_row[f"{m}_delta"] = round(delta, 6)
                if delta > 0.01:
                    d_row[f"delta_status_{m}"] = "improved"
                elif delta < -0.01:
                    d_row[f"delta_status_{m}"] = "regressed"
                else:
                    d_row[f"delta_status_{m}"] = "unchanged"
            else:
                d_row[f"{m}_delta"] = ""
                d_row[f"delta_status_{m}"] = "ineligible" if is_nc and "context" in m else "missing"

        deltas_rows.append(d_row)

    deltas_df = pd.DataFrame(deltas_rows)
    deltas_df.to_csv(DELTAS_CSV, index=False)
    print(f"Saved {len(deltas_df)} paired delta rows to {DELTAS_CSV}")

    # Compute aggregates
    aggregates = {
        "evaluation_phase": "Phase C.5 — Paired Ragas Evaluation",
        "timestamp_computed": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(paired_cases),
        "metrics": {}
    }

    for m in metrics:
        b_series = pd.to_numeric(deltas_df[f"{m}_baseline"], errors="coerce").dropna()
        g_series = pd.to_numeric(deltas_df[f"{m}_graph"], errors="coerce").dropna()
        delta_series = pd.to_numeric(deltas_df[f"{m}_delta"], errors="coerce").dropna()

        n_pairs = len(delta_series)
        deltas_arr = delta_series.to_numpy()

        ci_low, ci_high = bootstrap_ci(deltas_arr, num_resamples=1000, ci=0.95, seed=42)

        improved = int((delta_series > 0.01).sum())
        unchanged = int((delta_series.abs() <= 0.01).sum())
        regressed = int((delta_series < -0.01).sum())

        aggregates["metrics"][m] = {
            "eligible_paired_cases": n_pairs,
            "baseline_mean": round(float(b_series.mean()), 6) if n_pairs > 0 else None,
            "baseline_median": round(float(b_series.median()), 6) if n_pairs > 0 else None,
            "graph_mean": round(float(g_series.mean()), 6) if n_pairs > 0 else None,
            "graph_median": round(float(g_series.median()), 6) if n_pairs > 0 else None,
            "mean_paired_delta": round(float(delta_series.mean()), 6) if n_pairs > 0 else None,
            "median_paired_delta": round(float(delta_series.median()), 6) if n_pairs > 0 else None,
            "bootstrap_95_ci_mean_delta": [round(ci_low, 6), round(ci_high, 6)],
            "counts": {
                "improved": improved,
                "unchanged": unchanged,
                "regressed": regressed,
            }
        }

    # Stratification by query_category
    strat_cat = {}
    for cat, group in deltas_df.groupby("query_category"):
        cat_stats = {"sample_size": len(group)}
        for m in metrics:
            d_col = pd.to_numeric(group[f"{m}_delta"], errors="coerce").dropna()
            if len(d_col) > 0:
                cat_stats[f"{m}_mean_delta"] = round(float(d_col.mean()), 4)
                cat_stats[f"{m}_improved"] = int((d_col > 0.01).sum())
                cat_stats[f"{m}_regressed"] = int((d_col < -0.01).sum())
        strat_cat[cat] = cat_stats
    aggregates["stratified_by_query_category"] = strat_cat

    # Stratification by answerability
    strat_ans = {}
    for ans, group in deltas_df.groupby("answerability"):
        ans_stats = {"sample_size": len(group)}
        for m in metrics:
            d_col = pd.to_numeric(group[f"{m}_delta"], errors="coerce").dropna()
            if len(d_col) > 0:
                ans_stats[f"{m}_mean_delta"] = round(float(d_col.mean()), 4)
        strat_ans[ans] = ans_stats
    aggregates["stratified_by_answerability"] = strat_ans

    with open(AGGREGATE_JSON, "w", encoding="utf-8") as f:
        json.dump(aggregates, f, indent=2)
    print(f"Saved aggregate metrics to {AGGREGATE_JSON}")

    # Update manifest
    if MANIFEST_JSON.exists():
        with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["status"] = "COMPLETED"
        manifest["timestamp_completed"] = datetime.now(timezone.utc).isoformat()
        with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print("Updated run_manifest.json to COMPLETED.")

    print("\n================ SUMMARY OF PAIRED AGGREGATE RESULTS ================")
    for m in metrics:
        data = aggregates["metrics"][m]
        print(f"\nMetric: {m.upper()} (N = {data['eligible_paired_cases']} paired cases)")
        print(f"  Baseline:  Mean = {data['baseline_mean']:.4f} | Median = {data['baseline_median']:.4f}")
        print(f"  Graph:     Mean = {data['graph_mean']:.4f} | Median = {data['graph_median']:.4f}")
        print(f"  Delta (Graph - Base): Mean = {data['mean_paired_delta']:+.4f} | Median = {data['median_paired_delta']:+.4f}")
        print(f"  95% CI on Mean Delta: [{data['bootstrap_95_ci_mean_delta'][0]:+.4f}, {data['bootstrap_95_ci_mean_delta'][1]:+.4f}]")
        print(f"  Outcomes: {data['counts']['improved']} Improved, {data['counts']['unchanged']} Unchanged, {data['counts']['regressed']} Regressed")
    print("=====================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MediScanAI Phase C.5 Paired Ragas Evaluation Runner")
    parser.add_argument("--max-cases", type=int, default=None, help="Limit number of cases to evaluate (for testing)")
    parser.add_argument("--post-process-only", action="store_true", help="Skip evaluation and compute deltas/aggregates from existing CSV")
    args = parser.parse_args()

    if args.post_process_only:
        post_process_evaluation()
    else:
        run_evaluation(max_cases=args.max_cases)
