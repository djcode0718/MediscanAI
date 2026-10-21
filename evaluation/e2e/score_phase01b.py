#!/usr/bin/env python3
"""
MediScanAI Phase 01b Scoring Runner (Step 6).
Evaluates R0s, A1, and A2 runs using:
  - SELF-JUDGED (llama3.1:8b) via Ollama:
      * RAGAS Faithfulness (answer_core, traceable statement verdicts)
      * RAGAS Response Relevancy (answer_core)
      * Context precision/recall OFF
  - HHEM Faithfulness (vectara/hallucination_evaluation_model)
  - Deterministic metrics:
      * evidence_hit@k and MRR over equivalent_ids on ACTUALLY shown evidence (covers_ids)
      * hit@5 on raw retrieved list
      * token stats (avg/p95 evidence tokens, prompt tokens, latency, % truncated)
      * abstention and invalid-citation rates
  - Scoring Gate: first 5 cases evaluated per run to verify NaN rate <= 20% and estimate wall time.
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import sys
import json
import time
import math
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from datasets import Dataset

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import answer_relevancy
from ragas.evaluation import evaluate
from ragas.run_config import RunConfig
from transformers import AutoModelForSequenceClassification

from evaluation.e2e.run_eval import TraceableFaithfulness, is_boilerplate_statement, compute_best_fuzzy_match


RESULTS_DIR = REPO_ROOT / "evaluation/e2e/results"
RUN_NAMES = ["R0s", "A1", "A2"]


def compute_deterministic_evidence_metrics(
    shown_items: List[Dict[str, Any]],
    raw_retrieved_ids: List[str],
    reference_context_ids: List[str],
    equivalent_ids: List[str],
    k: int = 3,
) -> Tuple[float, float, float]:
    """
    Computes:
      1. evidence_hit@k on ACTUALLY shown items (using covers_ids)
      2. MRR on ACTUALLY shown items
      3. hit@5 on raw retrieved list
    Target IDs: reference_context_ids U equivalent_ids.
    """
    target_ids = set(reference_context_ids) | set(equivalent_ids)
    if not target_ids:
        return 0.0, 0.0, 0.0

    # 1. Raw hit@5
    raw_hit_5 = 1.0 if any(rid in target_ids for rid in raw_retrieved_ids[:5]) else 0.0

    # 2. Shown items hit@k and MRR
    first_hit_rank = None
    hit_at_k = 0.0

    for rank_idx, itm in enumerate(shown_items, 1):
        item_id = itm.get("id", "")
        covers = itm.get("covers_ids", [item_id])
        item_id_set = set(covers) | {item_id}

        is_hit = bool(item_id_set & target_ids)
        if is_hit:
            if first_hit_rank is None:
                first_hit_rank = rank_idx
            if rank_idx <= k:
                hit_at_k = 1.0

    mrr = 1.0 / first_hit_rank if first_hit_rank is not None else 0.0
    return round(hit_at_k, 4), round(mrr, 4), round(raw_hit_5, 4)


def compute_hhem_faithfulness(hhem_model, premise: str, answer_core: str) -> float:
    """
    Computes HHEM faithfulness score across sentences of answer_core given premise.
    Returns average probability of consistency (non-hallucination) in [0, 1].
    """
    if not answer_core or not answer_core.strip():
        return np.nan

    # Split into sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer_core) if s.strip()]
    sentences = [s for s in sentences if len(s) > 3 and not s.startswith("###")]
    if not sentences:
        sentences = [answer_core.strip()]

    # Truncate premise safely if very large for HHEM foundation model
    safe_premise = premise[:1200] if len(premise) > 1200 else premise
    pairs = [(safe_premise, s) for s in sentences]

    try:
        raw_scores = hhem_model.predict(pairs)
        scores = [float(s.item()) for s in raw_scores]
        return round(float(np.mean(scores)), 4)
    except Exception as e:
        print(f"HHEM prediction error: {e}")
        return np.nan


def setup_judge_and_models():
    """Initializes Ollama llama3.1:8b judge wrapper and HHEM model."""
    print("⚖️ Initializing SELF-JUDGED (llama3.1:8b) with num_ctx=12288, seed=42, temp=0...")
    judge_llm = ChatOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="llama3.1:8b",
        temperature=0.0,
        model_kwargs={
            "extra_body": {
                "options": {
                    "num_ctx": 12288,
                    "seed": 42,
                    "num_predict": 700,
                },
                "format": "json"
            }
        }
    )
    judge_wrapper = LangchainLLMWrapper(judge_llm)
    embeddings_wrapper = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"local_files_only": True},
        )
    )

    print("🧠 Loading HHEM (vectara/hallucination_evaluation_model)...")
    hhem_model = AutoModelForSequenceClassification.from_pretrained(
        "vectara/hallucination_evaluation_model",
        trust_remote_code=True
    )

    return judge_wrapper, embeddings_wrapper, hhem_model


def score_single_case(
    record: Dict[str, Any],
    custom_faithfulness: TraceableFaithfulness,
    judge_wrapper: LangchainLLMWrapper,
    embeddings_wrapper: LangchainEmbeddingsWrapper,
    hhem_model: Any,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Scores a single case across RAGAS, HHEM, and deterministic metrics.
    Returns (scored_record, unsupported_statements_list).
    """
    cid = record["case_id"]
    ans_core = record.get("answer_core", "")
    retrieved_contexts = record.get("retrieved_contexts", ["No retrieved evidence."])
    shown_items = record.get("shown_evidence_items", [])
    raw_retrieved_ids = record.get("raw_retrieved_ids", [])
    ref_ids = record.get("reference_context_ids", [])
    eq_ids = record.get("equivalent_ids", [])
    expected = record.get("expected_behavior", "answer")

    # 1. Deterministic retrieval metrics
    ev_hit_3, ev_mrr, raw_hit_5 = compute_deterministic_evidence_metrics(
        shown_items=shown_items,
        raw_retrieved_ids=raw_retrieved_ids,
        reference_context_ids=ref_ids,
        equivalent_ids=eq_ids,
        k=3,
    )

    # 2. HHEM Faithfulness
    premise_str = "\n".join(retrieved_contexts)
    hhem_score = compute_hhem_faithfulness(hhem_model, premise_str, ans_core)

    # 3. RAGAS Metrics
    user_input_str = record.get("user_text") or f"Analyze medication label: {record.get('ocr_text', '')}"
    if not user_input_str.strip():
        user_input_str = "Medical inquiry."

    ragas_ds = Dataset.from_dict({
        "question": [user_input_str],
        "response": [ans_core if ans_core else "No answer provided."],
        "retrieved_contexts": [retrieved_contexts],
    })

    judge_faithfulness = np.nan
    response_relevancy_val = np.nan
    nan_reasons = {}
    unsupported_items = []

    # Check for judge context overflow in R0s
    total_context_chars = sum(len(c) for c in retrieved_contexts)
    if total_context_chars > 45000:
        nan_reasons["judge_faithfulness"] = "judge_context_overflow"
        nan_reasons["response_relevancy"] = "judge_context_overflow"
    else:
        ragas_run_cfg = RunConfig(max_workers=1, timeout=300, max_retries=2)
        try:
            # 1. Evaluate Faithfulness
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

            # Capture unsupported statements
            if custom_faithfulness.last_verdicts_output:
                for v in custom_faithfulness.last_verdicts_output.statements:
                    if int(v.verdict) == 0:
                        if not is_boilerplate_statement(v.statement):
                            f_match = compute_best_fuzzy_match(v.statement, retrieved_contexts)
                            unsupported_items.append({
                                "case_id": cid,
                                "statement": v.statement,
                                "reason": v.reason,
                                "fuzzy_score": f_match,
                            })

            # 2. Evaluate Response Relevancy
            scores_df_rel = evaluate(
                dataset=ragas_ds,
                metrics=[answer_relevancy],
                llm=judge_wrapper,
                embeddings=embeddings_wrapper,
                run_config=ragas_run_cfg,
                show_progress=False,
            ).to_pandas()

            r_score = scores_df_rel.iloc[0].get("answer_relevancy")
            response_relevancy_val = round(float(r_score), 4) if pd.notna(r_score) else np.nan
            if pd.isna(response_relevancy_val):
                nan_reasons["response_relevancy"] = "judge_returned_nan_relevancy"

        except Exception as e:
            err_msg = str(e)
            nan_reasons["judge_error"] = err_msg[:60]

    scored = dict(record)
    scored.update({
        "judge_label": "SELF-JUDGED (llama3.1:8b)",
        "judge_faithfulness": judge_faithfulness,
        "hhem_faithfulness": hhem_score,
        "response_relevancy": response_relevancy_val,
        "evidence_hit_at_3": ev_hit_3,
        "evidence_mrr": ev_mrr,
        "raw_hit_at_5": raw_hit_5,
        "nan_reasons": nan_reasons,
    })
    return scored, unsupported_items


def compute_run_summary(records: List[Dict[str, Any]], run_name: str) -> Dict[str, Any]:
    """Computes comprehensive mean, median, p10, p95, and rate statistics for a run."""
    def stats(vals):
        valid = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
        if not valid:
            return {"mean": None, "median": None, "p10": None, "nan_count": len(vals), "total": len(vals)}
        arr = np.array(valid, dtype=float)
        return {
            "mean": round(float(np.mean(arr)), 4),
            "median": round(float(np.median(arr)), 4),
            "p10": round(float(np.percentile(arr, 10)), 4),
            "p95": round(float(np.percentile(arr, 95)), 4),
            "nan_count": len(vals) - len(valid),
            "total": len(vals),
        }

    faith_j = [r["judge_faithfulness"] for r in records]
    faith_h = [r["hhem_faithfulness"] for r in records]
    relevancy = [r["response_relevancy"] for r in records]
    ev_hit3 = [r["evidence_hit_at_3"] for r in records]
    ev_mrr = [r["evidence_mrr"] for r in records]
    raw_hit5 = [r["raw_hit_at_5"] for r in records]
    latencies = [r["latency_ms"] for r in records]
    prompt_toks = [r["prompt_tokens"] for r in records]
    ev_toks = [r["evidence_tokens"] for r in records]

    # Rates
    abstained_cases = sum(1 for r in records if r.get("abstained", False))
    invalid_cit_cases = sum(1 for r in records if r.get("invalid_tags"))
    truncated_cases = sum(1 for r in records if r.get("truncated_by_length", False))

    # Category breakdown
    cats = sorted(list(set(r["category"] for r in records)))
    cat_summary = {}
    for c in cats:
        c_recs = [r for r in records if r["category"] == c]
        c_faith_j = [r["judge_faithfulness"] for r in c_recs]
        c_faith_h = [r["hhem_faithfulness"] for r in c_recs]
        c_rel = [r["response_relevancy"] for r in c_recs]
        c_abstained = sum(1 for r in c_recs if r.get("abstained", False))
        cat_summary[c] = {
            "count": len(c_recs),
            "judge_faithfulness": stats(c_faith_j),
            "hhem_faithfulness": stats(c_faith_h),
            "response_relevancy": stats(c_rel),
            "abstention_rate": round(c_abstained / len(c_recs), 4) if c_recs else 0.0,
        }

    # Spearman correlation between Judge Faithfulness and HHEM
    valid_pairs = [
        (r["judge_faithfulness"], r["hhem_faithfulness"])
        for r in records
        if pd.notna(r["judge_faithfulness"]) and pd.notna(r["hhem_faithfulness"])
    ]
    if len(valid_pairs) >= 5:
        corr, pval = spearmanr([p[0] for p in valid_pairs], [p[1] for p in valid_pairs])
        spearman_corr = round(float(corr), 4) if not math.isnan(corr) else 0.0
    else:
        spearman_corr = 0.0

    return {
        "judge_label": "SELF-JUDGED (llama3.1:8b)",
        "run_name": run_name,
        "n_cases": len(records),
        "judge_faithfulness": stats(faith_j),
        "hhem_faithfulness": stats(faith_h),
        "response_relevancy": stats(relevancy),
        "evidence_hit_at_3": stats(ev_hit3),
        "evidence_mrr": stats(ev_mrr),
        "raw_hit_at_5": stats(raw_hit5),
        "latency_ms": stats(latencies),
        "prompt_tokens": stats(prompt_toks),
        "evidence_tokens": stats(ev_toks),
        "abstention_rate": round(abstained_cases / len(records), 4) if records else 0.0,
        "invalid_citation_rate": round(invalid_cit_cases / len(records), 4) if records else 0.0,
        "truncation_rate": round(truncated_cases / len(records), 4) if records else 0.0,
        "spearman_judge_hhem": spearman_corr,
        "by_category": cat_summary,
    }


def run_scoring_gate(
    run_records_dict: Dict[str, List[Dict[str, Any]]],
    judge_wrapper,
    embeddings_wrapper,
    hhem_model,
) -> bool:
    """
    Scoring Gate: evaluates 5 cases per run first.
    Prints wall time, NaN rates per metric, and raw failing judge outputs.
    Estimates total scoring time for 40 cases.
    Returns True if gate passes (NaN <= 20% and estimate <= 90 mins).
    """
    print("\n" + "=" * 80)
    print("🚦 RUNNING SCORING GATE (First 5 cases per run: R0s, A1, A2)")
    print("=" * 80)

    total_gate_start = time.time()
    for run_name, records in run_records_dict.items():
        gate_subset = records[:5]
        print(f"\n--- Testing Gate on {run_name} (5 cases) ---")
        t0 = time.time()
        custom_faithfulness = TraceableFaithfulness(llm=judge_wrapper)

        gate_scored = []
        for idx, r in enumerate(gate_subset, 1):
            sc, _ = score_single_case(
                r, custom_faithfulness, judge_wrapper, embeddings_wrapper, hhem_model
            )
            gate_scored.append(sc)
            print(f"  [{idx}/5] {r['case_id']}: J_Faith={sc['judge_faithfulness']}, HHEM={sc['hhem_faithfulness']}, Rel={sc['response_relevancy']}")

        elapsed = time.time() - t0
        nan_j_faith = sum(1 for s in gate_scored if pd.isna(s["judge_faithfulness"]))
        nan_rel = sum(1 for s in gate_scored if pd.isna(s["response_relevancy"]))
        nan_hhem = sum(1 for s in gate_scored if pd.isna(s["hhem_faithfulness"]))

        nan_rate_j = nan_j_faith / 5.0
        nan_rate_rel = nan_rel / 5.0

        print(f"Gate {run_name} summary: 5 cases in {elapsed:.1f}s ({elapsed/5:.1f}s/case)")
        print(f"  NaN rates: Judge Faithfulness={nan_rate_j:.1%}, Relevancy={nan_rate_rel:.1%}, HHEM={nan_hhem/5.0:.1%}")

        failing = [s for s in gate_scored if s.get("nan_reasons")]
        if failing:
            print(f"  Raw failing reasons:")
            for f in failing:
                print(f"    {f['case_id']}: {f['nan_reasons']}")

        if nan_rate_j > 0.20 or nan_rate_rel > 0.20:
            print(f"❌ Gate failure: NaN rate > 20% on {run_name}!")
            return False

    total_gate_time = time.time() - total_gate_start
    est_total_scoring_time = (total_gate_time / 15.0) * (40 * 3)
    est_minutes = est_total_scoring_time / 60.0
    print(f"\n✅ SCORING GATE PASSED! Estimated scoring time for 3 runs (120 cases): {est_minutes:.1f} minutes.")
    if est_minutes > 90.0:
        print(f"⚠️ Warning: Estimated scoring time exceeds 90 minutes ({est_minutes:.1f}m).")
        return False
    return True


def execute_full_scoring(run_name: str, records: List[Dict[str, Any]], judge_wrapper, embeddings_wrapper, hhem_model):
    """Executes full scoring for all 40 cases of a run and saves outputs."""
    print(f"\n========================================================")
    print(f"📊 Scoring Full Run: {run_name} (40 cases)")
    print(f"   Label: SELF-JUDGED (llama3.1:8b)")
    print(f"========================================================")

    out_dir = RESULTS_DIR / run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    scored_file = out_dir / "scored_results.jsonl"
    summary_file = out_dir / "summary.json"
    unsupported_file = out_dir / "unsupported_statements.jsonl"
    taxonomy_file = out_dir / "taxonomy_to_fill.csv"

    custom_faithfulness = TraceableFaithfulness(llm=judge_wrapper)
    scored_records = []
    all_unsupported = []

    t0_run = time.time()
    for idx, r in enumerate(records, 1):
        cid = r["case_id"]
        print(f"[{idx}/{len(records)}] Scoring {cid}...", end=" ", flush=True)
        t_case = time.time()
        sc, unsupp = score_single_case(r, custom_faithfulness, judge_wrapper, embeddings_wrapper, hhem_model)
        scored_records.append(sc)
        all_unsupported.extend(unsupp)
        dt = time.time() - t_case
        print(f"done ({dt:.1f}s) -> J_Faith={sc['judge_faithfulness']}, HHEM={sc['hhem_faithfulness']}")

    total_t = time.time() - t0_run
    print(f"\nFinished scoring {run_name} in {total_t:.1f}s.")

    # Write scored results
    with open(scored_file, "w", encoding="utf-8") as f:
        for s in scored_records:
            f.write(json.dumps(s) + "\n")

    # Write unsupported statements
    with open(unsupported_file, "w", encoding="utf-8") as f:
        for u in all_unsupported:
            f.write(json.dumps(u) + "\n")

    # Write taxonomy CSV
    with open(taxonomy_file, "w", encoding="utf-8") as f:
        f.write("case_id,statement,parametric_knowledge,verdict_inference,misread,truncated_context,invalid_tag,other\n")
        for u in all_unsupported:
            clean_stmt = u["statement"].replace('"', '""')
            f.write(f'"{u["case_id"]}","{clean_stmt}","","","","","",""\n')

    # Compute and save summary
    summary = compute_run_summary(scored_records, run_name)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Scored results written to: {scored_file}")
    print(f"✅ Summary written to: {summary_file}")
    print(f"✅ Unsupported statements ({len(all_unsupported)}) written to: {unsupported_file}")
    return scored_records, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-only", action="store_true", help="Run only the 5-case scoring gate")
    args = parser.parse_args()

    # Load generated cases for all 3 runs
    run_records = {}
    for rname in RUN_NAMES:
        gpath = RESULTS_DIR / rname / "generated_cases.jsonl"
        if not gpath.exists():
            print(f"Error: {gpath} does not exist. Run generation first!")
            sys.exit(1)
        with open(gpath, "r", encoding="utf-8") as f:
            run_records[rname] = [json.loads(line) for line in f if line.strip()]

    judge_wrapper, embeddings_wrapper, hhem_model = setup_judge_and_models()

    # 1. Scoring Gate
    gate_ok = run_scoring_gate(run_records, judge_wrapper, embeddings_wrapper, hhem_model)
    if not gate_ok:
        print("❌ Scoring gate failed. Halting.")
        sys.exit(1)

    if args.gate_only:
        print("Gate-only test completed successfully.")
        return

    # 2. Full Scoring for all 3 runs
    all_summaries = {}
    for rname in RUN_NAMES:
        scored_recs, summary = execute_full_scoring(
            run_name=rname,
            records=run_records[rname],
            judge_wrapper=judge_wrapper,
            embeddings_wrapper=embeddings_wrapper,
            hhem_model=hhem_model,
        )
        all_summaries[rname] = summary

    # Save overall combined comparison summary
    comb_path = RESULTS_DIR / "PHASE01B_SCORED_ALL.json"
    with open(comb_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)

    print(f"\n🎉 ALL SCORING COMPLETE! Combined summaries saved to: {comb_path}")


if __name__ == "__main__":
    main()
