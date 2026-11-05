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
from evaluation.e2e.eval_status import CaseResult, EvalStatus, aggregate_results
from evaluation.e2e.strict_scoring import score_case_strict
from evaluation.e2e.cache_v2 import CacheV2, build_cache_key_v2
from evaluation.e2e.manifest import RunManifest
from evaluation.e2e.reporting import generate_evaluation_markdown, load_scored_jsonl

RESULTS_DIR = REPO_ROOT / "evaluation/e2e/results"


def score_faithfulness_strict_candidate(
    record: Dict[str, Any],
    custom_faithfulness: TraceableFaithfulness,
    judge_wrapper: LangchainLLMWrapper,
    cache: Optional[Dict[str, Any]] = None,
    *,
    tracker: Any = None,
    run_dir: Optional[Path] = None,
    bypass_cache: bool = False,
    run_config: Optional[RunConfig] = None,
    cache_v2: Optional[CacheV2] = None,
    cache_mode: str = "default",  # "default", "no_cache", "refresh_cache"
    manifest: Optional[Any] = None,
) -> CaseResult:
    """P2: status-carrying scorer with Cache V2 support and run manifest tracking.

    Cache modes:
      - 'default': read from Cache V2 (or cache dict); on hit, return cached valid result; on miss, score & cache if valid.
      - 'no_cache': bypass both read and write.
      - 'refresh_cache': ignore cache on read (recompute), write valid result to cache.

    Only status == valid results are ever written to the cache; invalid results are never cached.
    """
    cid = record["case_id"]

    effective_read = not bypass_cache and (cache_mode == "default")
    effective_write = not bypass_cache and (cache_mode in ("default", "refresh_cache"))

    key_v2 = None
    key_comps = None
    if cache_v2 is not None:
        key_v2, key_comps = build_cache_key_v2(record, JUDGE_CONFIG, custom_faithfulness)

    # 1. Cache Read
    if effective_read:
        if cache_v2 is not None and key_v2 is not None:
            cached = cache_v2.get(key_v2)
            if cached is not None and cached.get("eval_status") == "valid":
                if manifest is not None:
                    manifest.record_cache_event("hit")
                return CaseResult(
                    case_id=cid,
                    status=EvalStatus.valid,
                    score=float(cached["faithfulness"]),
                    warnings=cached.get("warnings", []),
                    unsupported=cached.get("unsupported", []),
                    category=record.get("category"),
                    cache_hit=True,
                )
            else:
                if manifest is not None:
                    manifest.record_cache_event("miss")
        elif cache is not None:
            inputs = {
                "question": record.get("user_text", "") or f"Analyze medication: {record.get('ocr_text', '')}",
                "response": record.get("answer_core", "").strip() or "No answer provided.",
                "retrieved_contexts": record.get("retrieved_contexts", []),
            }
            cache_key = compute_cache_key("faithfulness", inputs, JUDGE_CONFIG)
            if cache_key in cache:
                cached = cache[cache_key]
                cached_score = cached.get("faithfulness")
                if isinstance(cached_score, (int, float)) and not np.isnan(cached_score):
                    if manifest is not None:
                        manifest.record_cache_event("hit")
                    return CaseResult(
                        case_id=cid, status=EvalStatus.valid, score=float(cached_score),
                        warnings=["served_from_legacy_cache_not_revalidated"],
                        unsupported=cached.get("unsupported", []), category=record.get("category"), cache_hit=True,
                    )
                else:
                    if manifest is not None:
                        manifest.record_cache_event("miss")
            else:
                if manifest is not None:
                    manifest.record_cache_event("miss")
    else:
        if manifest is not None:
            manifest.record_cache_event("bypassed")

    # 2. Strict Scoring
    res = score_case_strict(
        record, custom_faithfulness, judge_wrapper,
        tracker=tracker, run_dir=run_dir, run_config=run_config,
    )

    # 3. Cache Write: Only status == valid results are ever written (invalid results never are).
    if res.status is EvalStatus.valid and effective_write:
        if cache_v2 is not None and key_v2 is not None and key_comps is not None:
            cache_v2.put(key_v2, key_comps, {
                "faithfulness": res.score,
                "unsupported": res.unsupported,
                "eval_status": res.status.value,
                "eval_guard_version": res.guard_version,
            })
        elif cache is not None:
            inputs = {
                "question": record.get("user_text", "") or f"Analyze medication: {record.get('ocr_text', '')}",
                "response": record.get("answer_core", "").strip() or "No answer provided.",
                "retrieved_contexts": record.get("retrieved_contexts", []),
            }
            cache_key = compute_cache_key("faithfulness", inputs, JUDGE_CONFIG)
            cache[cache_key] = {
                "faithfulness": res.score,
                "unsupported": res.unsupported,
                "nan_reasons": {},
                "eval_status": res.status.value,
                "eval_guard_version": res.guard_version,
            }
            save_cache(cache)

    return res


def score_faithfulness_single_candidate(
    record: Dict[str, Any],
    custom_faithfulness: TraceableFaithfulness,
    judge_wrapper: LangchainLLMWrapper,
    cache: Dict[str, Any],
    *,
    tracker: Any = None,
    run_dir: Optional[Path] = None,
    bypass_cache: bool = False,
) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    """Legacy tuple API kept for existing callers (e.g. run_a6_1_evaluation). Invalid cases return NaN
    here for tuple compatibility ONLY, and always carry the status and cause in `nan_reasons`; they are
    never cached. New code should call score_faithfulness_strict_candidate()."""
    res = score_faithfulness_strict_candidate(
        record, custom_faithfulness, judge_wrapper, cache,
        tracker=tracker, run_dir=run_dir, bypass_cache=bypass_cache,
    )
    if res.status is EvalStatus.valid:
        return res.score, res.unsupported, {}
    nan_reasons = {
        "judge_faithfulness": f"{res.status.value}: {res.error_class}: {(res.error_message or '')[:60]}",
        "eval_status": res.status.value,
    }
    return np.nan, [], nan_reasons


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


def evaluate_candidate(
    candidate_name: str,
    baseline_name: str = "A2",
    no_cache: bool = False,
    refresh_cache: bool = False,
):
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

    # 2. Judge Evaluation Setup
    verify_ollama_state()

    # Determine Cache Mode
    if no_cache:
        cache_mode = "no_cache"
    elif refresh_cache:
        cache_mode = "refresh_cache"
    else:
        cache_mode = "default"

    cache_v2 = CacheV2()

    # Initialize Manifest
    probe_path = REPO_ROOT / "evaluation/e2e/audit/p1_preflight/judge_probe.json"
    manifest = RunManifest(
        run_dir=cand_dir,
        candidate_id=candidate_name,
        dataset_path=REPO_ROOT / "evaluation/e2e/dataset/dev_subset_40.json",
        input_answers_path=cand_file,
        judge_config=JUDGE_CONFIG,
        probe_result_path=probe_path if probe_path.exists() else None,
        cache_mode=cache_mode,
    )

    print(f"\n⚖️ Initializing judge for {candidate_name} evaluation (cache_mode={cache_mode})...")
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

    ordered_case_ids = get_stratified_order(cand_list, seed=42)

    cand_scored = []
    all_unsupported = []
    nan_count = 0

    print(f"\n--- Scoring {candidate_name} Faithfulness ---")
    case_results: List[CaseResult] = []
    for idx, cid in enumerate(ordered_case_ids, 1):
        t_case_start = time.time()
        rec = cand_cases[cid]
        res = score_faithfulness_strict_candidate(
            rec,
            custom_faithfulness,
            judge_wrapper,
            cache=None,
            cache_v2=cache_v2,
            cache_mode=cache_mode,
            manifest=manifest,
        )
        case_results.append(res)
        f_score = res.score if res.is_valid else np.nan
        unsupp = res.unsupported
        n_reasons = {} if res.is_valid else {"judge_faithfulness": f"{res.status.value}: {res.error_class}"}

        manifest.record_case_status(res.status.value)

        r_sc = dict(rec)
        r_sc["judge_faithfulness"] = f_score
        r_sc["eval_status"] = res.status.value
        r_sc["eval_warnings"] = res.warnings
        r_sc["nan_reasons"] = n_reasons
        cand_scored.append(r_sc)
        all_unsupported.extend(unsupp)

        if pd.isna(f_score):
            nan_count += 1

        dt = time.time() - t_case_start
        base_f = base_cases.get(cid, {}).get("judge_faithfulness")
        print(f"[{idx}/40] {cid} ({rec['category']}) | {candidate_name}={f_score} (base {baseline_name}={base_f}) | time={dt:.1f}s | unsupp={len(unsupp)}")

    agg = aggregate_results(case_results)
    manifest.set_status_counts(agg["n_invalid_by_status"])
    print(f"\n📊 Status-aware aggregate: n_valid={agg['n_valid']} n_invalid={agg['n_invalid']} "
          f"by_status={agg['n_invalid_by_status']} mean_valid={agg['mean_valid']}")

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

    # 4. Generate Comparative Report Using Dynamic Data-Only Module
    report_md = generate_evaluation_markdown(
        candidate_id=candidate_name,
        baseline_id=baseline_name,
        cand_records=cand_scored,
        base_records=list(base_cases.values()),
        cand_unsupported=all_unsupported,
        base_unsupported=None,
        seed=42,
    )
    report_path = RESULTS_DIR / f"{candidate_name}_EVAL_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    manifest_file = manifest.finalize()
    print(f"🎉 Run manifest finalized: {manifest_file}")
    print(f"🎉 Comparison report generated: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Candidate Evaluation Runner")
    parser.add_argument("--candidate", default="A3", help="Candidate run identifier (e.g. A3, A4)")
    parser.add_argument("--baseline", default="A2", help="Baseline run identifier (default: A2)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache reads and writes")
    parser.add_argument("--refresh-cache", action="store_true", help="Ignore cache on read, overwrite on write")
    args = parser.parse_args()

    evaluate_candidate(
        args.candidate,
        args.baseline,
        no_cache=args.no_cache,
        refresh_cache=args.refresh_cache,
    )


if __name__ == "__main__":
    main()
