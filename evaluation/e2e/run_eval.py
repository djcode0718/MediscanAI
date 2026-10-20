#!/usr/bin/env python3
"""
MediScanAI — End-to-End Evaluation Harness (Step 4 / Phase 01)

Features:
  - Sequential execution through Pipeline with return_trace=True and ocr_text_override.
  - Crash-safe line-by-line JSONL streaming with --resume.
  - Strict Judge enforcement: non-Llama, different from generator, cached by hash.
  - Offline local embeddings via sentence-transformers (all-MiniLM-L6-v2).
  - RAGAS metrics: faithfulness (answer_core and answer_full), answer_relevancy,
    LLM context_precision, LLM context_recall.
  - Deterministic ID-based context precision@k and recall treating equivalent_ids as hits.
  - Statement-level dump for faithfulness < 1 -> unsupported_statements.jsonl and taxonomy_to_fill.csv.
  - Emergency fast-path hit rate evaluated separately.
  - Run metadata and statistical summary (mean, median, p10, NaNs, token stats).
"""

import os
import sys
import json
import time
import re
import math
import difflib
import hashlib
import sqlite3
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np
import pandas as pd
from datasets import Dataset

from dotenv import load_dotenv
load_dotenv()

# Langchain & Ragas
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.metrics._faithfulness import Faithfulness, NLIStatementOutput, StatementGeneratorOutput
from ragas.evaluation import evaluate
from ragas.run_config import RunConfig

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.core import Pipeline
from app.llm import GenerationParams
from backend.core.config import get_settings, Settings
from evaluation.e2e.sanitize import answer_core, answer_full, is_fast_path

DEFAULT_DATASET = REPO_ROOT / "evaluation/e2e/dataset/e2e_v1.jsonl"
CACHE_DIR = REPO_ROOT / "evaluation/e2e/cache"


# ---------------------------------------------------------------------------
# Judge Caching Layer
# ---------------------------------------------------------------------------

CACHE_DIR.mkdir(parents=True, exist_ok=True)
import langchain
from langchain_community.cache import SQLiteCache
langchain.llm_cache = SQLiteCache(database_path=str(CACHE_DIR / "judge_cache.sqlite"))


# ---------------------------------------------------------------------------
# Traceable Faithfulness Subclass
# ---------------------------------------------------------------------------

class TraceableFaithfulness(Faithfulness):
    """Subclass of Ragas Faithfulness that exposes statement-level verdicts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_statements_output = None
        self.last_verdicts_output = None

    async def _ascore(self, row: dict, callbacks: Any) -> float:
        assert self.llm is not None, "LLM is not set"
        statements = await self._create_statements(row, callbacks)
        self.last_statements_output = statements
        stmts = statements.statements
        if not stmts:
            self.last_verdicts_output = None
            return np.nan

        verdicts = await self._create_verdicts(row, stmts, callbacks)
        self.last_verdicts_output = verdicts
        return self._compute_score(verdicts)


# ---------------------------------------------------------------------------
# Diagnostics Helpers
# ---------------------------------------------------------------------------

BOILERPLATE_PATTERNS = [
    re.compile(r"consult\s+(?:a|your)\s+(?:doctor|physician|healthcare\s+provider|pharmacist)", re.IGNORECASE),
    re.compile(r"informational\s+purposes\s+only", re.IGNORECASE),
    re.compile(r"not\s+a\s+substitute\s+for\s+professional\s+medical\s+advice", re.IGNORECASE),
    re.compile(r"emergency\s+(?:medical\s+)?attention", re.IGNORECASE),
    re.compile(r"call\s+(?:911|112)", re.IGNORECASE),
    re.compile(r"do\s+not\s+take\s+any\s+medication\s+without", re.IGNORECASE),
]


def is_boilerplate_statement(statement: str) -> bool:
    for pat in BOILERPLATE_PATTERNS:
        if pat.search(statement):
            return True
    return False


def compute_best_fuzzy_match(statement: str, contexts: List[str]) -> float:
    if not statement or not contexts:
        return 0.0
    stmt_clean = statement.lower().strip()
    best_score = 0.0
    for ctx in contexts:
        # Check against context sentences or chunks
        sentences = re.split(r"[.\n;]", ctx)
        for s in sentences:
            s_clean = s.lower().strip()
            if not s_clean:
                continue
            ratio = difflib.SequenceMatcher(None, stmt_clean, s_clean).ratio()
            if ratio > best_score:
                best_score = ratio
    return round(best_score, 4)


def compute_deterministic_id_metrics(
    retrieved_ids_per_channel: Dict[str, List[str]],
    reference_context_ids: List[str],
    equivalent_ids: List[str],
    k: int = 5,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Computes deterministic ID-based Precision@k and Recall.
    Treats any ID in equivalent_ids as a valid hit for drug targets.
    """
    if not reference_context_ids:
        return None, None

    # Flatten retrieved IDs across channels in deterministic order
    flat_retrieved: List[str] = []
    seen = set()
    for ch in ["diseases", "drugs", "drugs_from_ocr", "drug_dict", "graph_diseases", "graph_drugs"]:
        for rid in retrieved_ids_per_channel.get(ch, []):
            if rid not in seen:
                seen.add(rid)
                flat_retrieved.append(rid)

    top_k_retrieved = flat_retrieved[:k]
    valid_targets = set(reference_context_ids).union(set(equivalent_ids))

    hits_at_k = sum(1 for rid in top_k_retrieved if rid in valid_targets)
    precision_at_k = hits_at_k / len(top_k_retrieved) if top_k_retrieved else 0.0

    # Recall across all retrieved items
    covered_refs = 0
    for ref_id in reference_context_ids:
        if ref_id in flat_retrieved:
            covered_refs += 1
        elif any(eq_id in flat_retrieved for eq_id in equivalent_ids):
            covered_refs += 1

    recall = covered_refs / len(reference_context_ids) if reference_context_ids else 0.0
    return round(precision_at_k, 4), round(recall, 4)


# ---------------------------------------------------------------------------
# Git & Environment Metadata Helpers
# ---------------------------------------------------------------------------

def get_git_info() -> Dict[str, Any]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT).decode().strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT).decode().strip()
        is_dirty = len(status) > 0
        return {"commit_sha": sha, "branch": branch, "dirty": is_dirty}
    except Exception as e:
        return {"commit_sha": "unknown", "branch": "unknown", "dirty": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Main Evaluation Runner
# ---------------------------------------------------------------------------

def run_e2e_evaluation(args):
    print("=" * 80)
    print(f"🏥 MediScanAI End-to-End Evaluation Runner: Config '{args.config_name}'")
    print("=" * 80)

    # 1. Setup Judge
    judge_base_url = os.getenv("JUDGE_BASE_URL", "https://api.groq.com/openai/v1")
    judge_api_key = os.getenv("JUDGE_API_KEY") or os.getenv("GROQ_API_KEY")
    judge_model = os.getenv("JUDGE_MODEL", "qwen/qwen3.8-27b")

    if not judge_api_key:
        print("❌ Error: Neither JUDGE_API_KEY nor GROQ_API_KEY is configured in environment.")
        sys.exit(1)

    # Validate Judge Rule: Must NOT be Llama
    if "llama" in judge_model.lower():
        print(f"❌ Error: Judge rule violation! JUDGE_MODEL='{judge_model}' contains 'llama'.")
        print("   The judge must not be any Llama model. Please configure a non-Llama judge (e.g. qwen/qwen3.8-27b).")
        sys.exit(1)

    print(f"⚖️  Judge Endpoint: {judge_base_url}")
    print(f"⚖️  Judge Model:    {judge_model}")

    # Output directory
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / f"evaluation/e2e/results/{args.config_name}_{args.llm_mode}"
    out_dir.mkdir(parents=True, exist_ok=True)
    per_case_jsonl = out_dir / "per_case_results.jsonl"
    unsupported_jsonl = out_dir / "unsupported_statements.jsonl"
    taxonomy_csv = out_dir / "taxonomy_to_fill.csv"
    summary_json = out_dir / "summary.json"
    metadata_json = out_dir / "run_metadata.json"

    # Init taxonomy CSV if not present
    if not taxonomy_csv.exists():
        with open(taxonomy_csv, "w", encoding="utf-8") as f:
            f.write("case_id,statement,reason,diagnostics,label\n")

    # Load Dataset
    dataset_file = Path(args.dataset) if args.dataset else DEFAULT_DATASET
    if not dataset_file.exists():
        print(f"❌ Error: Dataset file not found at {dataset_file}")
        sys.exit(1)

    all_cases = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_cases.append(json.loads(line))

    # Filter categories if requested
    if args.categories:
        cat_filter = set(c.strip() for c in args.categories.split(","))
        cases = [c for c in all_cases if c["category"] in cat_filter]
    else:
        cases = list(all_cases)

    # Filter limit if requested
    if args.limit:
        cases = cases[:args.limit]

    print(f"Loaded {len(cases)} cases for evaluation run (limit={args.limit}).")

    # Resume handling
    finished_case_ids: Set[str] = set()
    if args.resume and per_case_jsonl.exists():
        with open(per_case_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        finished_case_ids.add(record["case_id"])
                    except Exception:
                        pass
        print(f"Found {len(finished_case_ids)} already completed cases in {per_case_jsonl}. Resuming...")

    # Configure Pipeline
    settings = get_settings()
    settings.NEO4J_ENABLED = False  # Baseline invariant
    # Keep EMERGENCY_GUARDRAIL_ENABLED as in current settings / env
    print(f"Settings: NEO4J_ENABLED={settings.NEO4J_ENABLED}, EMERGENCY_GUARDRAIL_ENABLED={settings.EMERGENCY_GUARDRAIL_ENABLED}")

    pipeline = Pipeline(settings=settings)

    # Generation parameters
    gen_params = GenerationParams(
        temperature=args.temperature,
        seed=args.seed,
        num_ctx=args.num_ctx,
        num_predict=None,
    )

    # Setup RAGAS components
    judge_llm = ChatOpenAI(
        base_url=judge_base_url,
        api_key=judge_api_key,
        model=judge_model,
        temperature=0.0,
        max_tokens=2048,
        timeout=60,
        max_retries=5,
    )
    judge_wrapper = LangchainLLMWrapper(judge_llm)

    embeddings_wrapper = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"local_files_only": True},
        )
    )

    custom_faithfulness = TraceableFaithfulness(llm=judge_wrapper)
    custom_faithfulness_full = TraceableFaithfulness(llm=judge_wrapper)

    ragas_run_cfg = RunConfig(max_workers=1, timeout=90, max_wait=30, max_retries=2)

    # Execution loop
    actual_generators_used: Set[str] = set()
    eval_records: List[Dict[str, Any]] = []

    f_jsonl = open(per_case_jsonl, "a", encoding="utf-8")
    f_unsupported = open(unsupported_jsonl, "a", encoding="utf-8")
    f_taxonomy = open(taxonomy_csv, "a", encoding="utf-8")

    start_wall_time = time.time()
    try:
        for idx, case in enumerate(cases, 1):
            cid = case["case_id"]
            if cid in finished_case_ids:
                continue

            print(f"\n[{idx}/{len(cases)}] Processing {cid} ({case['category']})...")
            t0 = time.time()

            # Pipeline execution
            run_res = pipeline.run(
                user_text=case["user_text"],
                ocr_text_override=case["ocr_text"],
                llm_mode=args.llm_mode,
                return_trace=True,
                gen_params=gen_params,
            )
            pipeline_latency_ms = int((time.time() - t0) * 1000)

            trace = run_res.get("trace", {})
            gen_meta = trace.get("generation_meta", {})
            actual_model = gen_meta.get("model", "unknown")
            actual_generators_used.add(actual_model)

            # Refuse to start / proceed if Judge Model equals Generator Model!
            if judge_model.strip().lower() == actual_model.strip().lower():
                raise RuntimeError(
                    f"CRITICAL: Judge model '{judge_model}' equals generator model '{actual_model}'. Refusing to continue!"
                )

            # Sanitize outputs
            raw_output = trace.get("raw_llm_output", "")
            final_output = trace.get("final_output", "")
            ans_core = answer_core(raw_output)
            ans_full = answer_full(final_output)
            fast_path_fired = is_fast_path(trace)

            # Evidence contexts (exact per-channel evidence strings from trace)
            retrievals_data = trace.get("retrievals_per_channel", {})
            channels_dict = retrievals_data.get("channels", {}) if isinstance(retrievals_data, dict) else {}
            retrieved_contexts_list = [v.strip() for v in channels_dict.values() if isinstance(v, str) and v.strip()]
            if not retrieved_contexts_list:
                user_ctx = retrievals_data.get("user_text_retrievals", "") if isinstance(retrievals_data, dict) else ""
                if isinstance(user_ctx, str) and user_ctx.strip():
                    retrieved_contexts_list = [user_ctx.strip()]
                else:
                    retrieved_contexts_list = ["No retrieved evidence."]

            # Deterministic ID metrics
            id_p_k, id_rec = compute_deterministic_id_metrics(
                retrieved_ids_per_channel=trace.get("retrieved_ids", {}),
                reference_context_ids=case.get("reference_context_ids", []),
                equivalent_ids=case.get("equivalent_ids", []),
                k=5,
            )

            # Record init
            rec = {
                "case_id": cid,
                "category": case["category"],
                "expected_behavior": case["expected_behavior"],
                "generator_model": actual_model,
                "prompt_tokens": trace.get("prompt_tokens_est", 0),
                "ollama_prompt_eval_count": gen_meta.get("prompt_eval_count"),
                "ollama_eval_count": gen_meta.get("eval_count"),
                "latency_ms": pipeline_latency_ms,
                "fast_path_fired": fast_path_fired,
                "truncated_by_length": gen_meta.get("truncated_by_length", False),
                "likely_prompt_truncated": gen_meta.get("likely_prompt_truncated", False),
                "id_precision_at_5": id_p_k,
                "id_recall": id_rec,
                "faithfulness_core": None,
                "faithfulness_full": None,
                "answer_relevancy": None,
                "context_precision": None,
                "context_recall": None,
                "nan_reasons": {},
                "answer_core": ans_core,
                "answer_full": ans_full,
            }

            # Emergency handling
            if case["category"] == "emergency":
                rec["emergency_hit"] = fast_path_fired or ("emergency" in ans_core.lower() or "911" in ans_core)
                rec["nan_reasons"]["all"] = "emergency_fast_path_case_excluded_from_ragas"
                print(f"   ↳ Emergency case: fast_path_fired={fast_path_fired}, emergency_hit={rec['emergency_hit']}")
                f_jsonl.write(json.dumps(rec) + "\n")
                f_jsonl.flush()
                eval_records.append(rec)
                continue

            # Ragas scoring
            user_input_str = case["user_text"] if case.get("user_text") else f"Analyze medication label: {case.get('ocr_text', '')}"
            ragas_data = {
                "user_input": [user_input_str],
                "question": [user_input_str],
                "response": [ans_core if ans_core else "No answer provided."],
                "retrieved_contexts": [retrieved_contexts_list],
                "reference": [case["reference"]],
            }
            ragas_ds = Dataset.from_dict(ragas_data)

            # Active metrics
            if case["expected_behavior"] == "abstain":
                active_metrics = [custom_faithfulness, answer_relevancy]
                rec["nan_reasons"]["context_precision"] = "unanswerable_negative_control"
                rec["nan_reasons"]["context_recall"] = "unanswerable_negative_control"
            else:
                active_metrics = [custom_faithfulness, answer_relevancy, context_precision, context_recall]

            try:
                scores_df = evaluate(
                    dataset=ragas_ds,
                    metrics=active_metrics,
                    llm=judge_wrapper,
                    embeddings=embeddings_wrapper,
                    run_config=ragas_run_cfg,
                    show_progress=False,
                ).to_pandas()

                for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
                    if m in scores_df.columns:
                        v = scores_df[m].iloc[0]
                        if pd.isna(v) or v is None:
                            val = None
                            if m not in rec["nan_reasons"]:
                                rec["nan_reasons"][m] = "judge_returned_nan"
                        else:
                            val = round(float(v), 4)
                        if m == "faithfulness":
                            rec["faithfulness_core"] = val
                        else:
                            rec[m] = val

                # Evaluate answer_full faithfulness
                ragas_full_data = {
                    "user_input": [user_input_str],
                    "question": [user_input_str],
                    "response": [ans_full if ans_full else "No answer provided."],
                    "retrieved_contexts": [retrieved_contexts_list],
                    "reference": [case["reference"]],
                }
                full_scores_df = evaluate(
                    dataset=Dataset.from_dict(ragas_full_data),
                    metrics=[custom_faithfulness_full],
                    llm=judge_wrapper,
                    embeddings=embeddings_wrapper,
                    run_config=ragas_run_cfg,
                    show_progress=False,
                ).to_pandas()
                if "faithfulness" in full_scores_df.columns:
                    fv = full_scores_df["faithfulness"].iloc[0]
                    rec["faithfulness_full"] = round(float(fv), 4) if (not pd.isna(fv) and fv is not None) else None

                # Statement-level extraction for faithfulness < 1.0
                core_f = rec["faithfulness_core"]
                if core_f is not None and core_f < 1.0 and custom_faithfulness.last_verdicts_output:
                    verdicts = custom_faithfulness.last_verdicts_output.statements
                    for v in verdicts:
                        if v.verdict == 0:
                            f_score = compute_best_fuzzy_match(v.statement, retrieved_contexts_list)
                            b_plate = is_boilerplate_statement(v.statement)
                            trunc = rec["likely_prompt_truncated"]
                            diag_str = f"fuzzy={f_score:.2f}|boilerplate={b_plate}|truncated={trunc}"

                            unsupp_rec = {
                                "case_id": cid,
                                "statement": v.statement,
                                "verdict": v.verdict,
                                "reason": v.reason,
                                "fuzzy_score": f_score,
                                "is_boilerplate": b_plate,
                                "likely_prompt_truncated": trunc,
                            }
                            f_unsupported.write(json.dumps(unsupp_rec) + "\n")
                            f_unsupported.flush()

                            stmt_escaped = f'"{v.statement.replace(chr(34), chr(39))}"'
                            reason_escaped = f'"{v.reason.replace(chr(34), chr(39))}"'
                            f_taxonomy.write(f'{cid},{stmt_escaped},{reason_escaped},"{diag_str}",\n')
                            f_taxonomy.flush()

            except Exception as e:
                print(f"   ⚠️ Ragas evaluation failed for {cid}: {e}")
                rec["nan_reasons"]["ragas_eval_exception"] = str(e)

            print(
                f"   ↳ Result: FaithCore={rec['faithfulness_core']}, FaithFull={rec['faithfulness_full']}, "
                f"Relevancy={rec['answer_relevancy']}, ID-P@5={rec['id_precision_at_5']}, Latency={rec['latency_ms']}ms"
            )

            f_jsonl.write(json.dumps(rec) + "\n")
            f_jsonl.flush()
            eval_records.append(rec)
            time.sleep(1.0)

    finally:
        f_jsonl.close()
        f_unsupported.close()
        f_taxonomy.close()

    # ---------------------------------------------------------------------------
    # Summary & Metadata
    # ---------------------------------------------------------------------------
    print("\n📊 Computing Run Aggregates & Statistics...")
    summary = compute_evaluation_summary(per_case_jsonl)
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    git_info = get_git_info()
    metadata = {
        "config_name": args.config_name,
        "llm_mode": args.llm_mode,
        "evidence_format": args.evidence_format,
        "generation_params": {
            "temperature": args.temperature,
            "seed": args.seed,
            "num_ctx": args.num_ctx,
        },
        "judge": {
            "base_url": judge_base_url,
            "model": judge_model,
        },
        "generators_actually_used": sorted(list(actual_generators_used)),
        "git": git_info,
        "env_flags": {
            "NEO4J_ENABLED": settings.NEO4J_ENABLED,
            "EMERGENCY_GUARDRAIL_ENABLED": settings.EMERGENCY_GUARDRAIL_ENABLED,
        },
        "packages": {
            "ragas": "0.2.15",
            "langchain": "1.4.6",
            "datasets": "3.6.0",
            "sentence_transformers": "5.1.0",
        },
        "total_cases_evaluated": len(eval_records),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    with open(metadata_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Run finished! Results saved to {out_dir}")
    print(f"Summary saved to: {summary_json}")
    print(f"Metadata saved to: {metadata_json}")


def compute_evaluation_summary(per_case_jsonl_path: Path) -> Dict[str, Any]:
    records_by_id = {}
    with open(per_case_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                records_by_id[r["case_id"]] = r
    records = list(records_by_id.values())

    metrics = [
        "faithfulness_core",
        "faithfulness_full",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "id_precision_at_5",
        "id_recall",
    ]

    metric_stats = {}
    for m in metrics:
        vals = [r[m] for r in records if r.get(m) is not None]
        nan_count = len(records) - len(vals)
        if vals:
            metric_stats[m] = {
                "n": len(vals),
                "nan_count": nan_count,
                "mean": round(float(np.mean(vals)), 4),
                "median": round(float(np.median(vals)), 4),
                "p10": round(float(np.percentile(vals, 10)), 4),
            }
        else:
            metric_stats[m] = {
                "n": 0,
                "nan_count": nan_count,
                "mean": None,
                "median": None,
                "p10": None,
            }

    # Token and Latency Stats
    prompt_tokens = [r["prompt_tokens"] for r in records if r.get("prompt_tokens")]
    latencies = [r["latency_ms"] for r in records if r.get("latency_ms")]
    likely_trunc = [1 if r.get("likely_prompt_truncated") else 0 for r in records]
    len_trunc = [1 if r.get("truncated_by_length") else 0 for r in records]

    # Category breakdowns
    categories = sorted(list(set(r["category"] for r in records)))
    per_category = {}
    for cat in categories:
        cat_recs = [r for r in records if r["category"] == cat]
        cat_stats = {"total_cases": len(cat_recs)}
        for m in ["faithfulness_core", "faithfulness_full", "answer_relevancy", "id_precision_at_5", "id_recall"]:
            cvals = [r[m] for r in cat_recs if r.get(m) is not None]
            cat_stats[m] = round(float(np.mean(cvals)), 4) if cvals else None
        per_category[cat] = cat_stats

    # Emergency hit rate
    emergency_recs = [r for r in records if r["category"] == "emergency"]
    emergency_hits = sum(1 for r in emergency_recs if r.get("emergency_hit"))
    emergency_hit_rate = round(emergency_hits / len(emergency_recs), 4) if emergency_recs else None

    # Proxy vs real token ratio
    proxy_ratios = []
    for r in records:
        proxy = r.get("prompt_tokens")
        real = r.get("ollama_prompt_eval_count")
        if proxy and real and real > 0:
            proxy_ratios.append(proxy / real)

    return {
        "total_records": len(records),
        "metrics": metric_stats,
        "prompt_tokens": {
            "mean": round(float(np.mean(prompt_tokens)), 1) if prompt_tokens else 0,
            "p95": round(float(np.percentile(prompt_tokens, 95)), 1) if prompt_tokens else 0,
        },
        "proxy_vs_real_token_ratio": {
            "mean": round(float(np.mean(proxy_ratios)), 4) if proxy_ratios else None,
            "min": round(float(np.min(proxy_ratios)), 4) if proxy_ratios else None,
            "max": round(float(np.max(proxy_ratios)), 4) if proxy_ratios else None,
        },
        "latency_ms": {
            "mean": round(float(np.mean(latencies)), 1) if latencies else 0,
            "p95": round(float(np.percentile(latencies, 95)), 1) if latencies else 0,
        },
        "pct_likely_prompt_truncated": round(float(np.mean(likely_trunc)) * 100, 2) if likely_trunc else 0.0,
        "pct_truncated_by_length": round(float(np.mean(len_trunc)) * 100, 2) if len_trunc else 0.0,
        "emergency_fast_path_hit_rate": emergency_hit_rate,
        "per_category": per_category,
    }


def main():
    parser = argparse.ArgumentParser(description="MediScanAI E2E RAG Evaluation Runner")
    parser.add_argument("--config-name", required=True, help="Configuration name (e.g. R0, R1, R2, R3)")
    parser.add_argument("--llm-mode", choices=["offline", "online"], default="offline", help="Generator LLM mode")
    parser.add_argument("--evidence-format", choices=["legacy", "compact"], default="legacy", help="Evidence format")
    parser.add_argument("--temperature", type=float, default=None, help="Generation temperature override")
    parser.add_argument("--seed", type=int, default=None, help="Generation seed override")
    parser.add_argument("--num-ctx", type=int, default=None, help="Context window size override")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases to evaluate")
    parser.add_argument("--categories", type=str, default=None, help="Comma-separated categories to filter")
    parser.add_argument("--repeat", type=int, default=1, help="Repetitions for variance check")
    parser.add_argument("--resume", action="store_true", help="Resume prior run skipping finished case_ids")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--dataset", type=str, default=None, help="Custom dataset path")

    args = parser.parse_args()
    run_e2e_evaluation(args)


if __name__ == "__main__":
    main()
