#!/usr/bin/env python3
"""
MediScanAI Evaluation Utility: Rescore Missing Judge Metrics
Populates missing external judge metrics (faithfulness, relevancy, precision, recall)
on already-generated pipeline traces without re-running expensive local LLM generation.
"""

import os
import sys
import json
import time
import difflib
import re
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Ensure root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv()

from app.core import Pipeline, normalize_text
from backend.core.config import get_settings
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import (
    Faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas import evaluate, RunConfig
from datasets import Dataset

from evaluation.e2e.run_eval import (
    TraceableFaithfulness,
    is_boilerplate_statement,
    compute_best_fuzzy_match,
    compute_evaluation_summary,
)


def rescore_missing(results_dir_str: str):
    results_dir = Path(results_dir_str)
    per_case_jsonl = results_dir / "per_case_results.jsonl"
    unsupported_jsonl = results_dir / "unsupported_statements.jsonl"
    taxonomy_csv = results_dir / "taxonomy_to_fill.csv"
    summary_json = results_dir / "summary.json"
    metadata_json = results_dir / "run_metadata.json"
    dataset_file = REPO_ROOT / "evaluation/e2e/dataset/e2e_v1.jsonl"

    if not per_case_jsonl.exists():
        print(f"Error: {per_case_jsonl} does not exist.")
        sys.exit(1)

    with open(dataset_file, "r", encoding="utf-8") as f:
        cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    records = []
    with open(per_case_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Identify records needing rescoring
    missing_ids = []
    for r in records:
        if r["category"] == "emergency":
            continue
        if r.get("faithfulness_core") is None or r.get("answer_relevancy") is None:
            missing_ids.append(r["case_id"])

    print(f"Total records: {len(records)}. Records needing judge scoring: {len(missing_ids)}.")
    if not missing_ids:
        print("All non-emergency records already scored! Recomputing summary...")
        summary = compute_evaluation_summary(per_case_jsonl)
        with open(summary_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print("Done.")
        return

    # Setup Pipeline for fast deterministic retrieval
    settings = get_settings()
    settings.NEO4J_ENABLED = False
    settings.EMERGENCY_GUARDRAIL_ENABLED = False
    pipeline = Pipeline(settings=settings)

    # Setup Judge
    judge_base_url = os.getenv("JUDGE_BASE_URL", "https://openrouter.ai/api/v1")
    judge_api_key = os.getenv("JUDGE_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    judge_model = os.getenv("JUDGE_MODEL", "minimax/minimax-m3.1-flash:free")

    print(f"⚖️ Judge Base URL: {judge_base_url}")
    print(f"⚖️ Judge Model:    {judge_model}")

    judge_llm = ChatOpenAI(
        base_url=judge_base_url,
        api_key=judge_api_key,
        model=judge_model,
        temperature=0.0,
        max_tokens=1024,
        timeout=60,
        max_retries=3,
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

    f_unsupported = open(unsupported_jsonl, "a", encoding="utf-8")
    f_taxonomy = open(taxonomy_csv, "a", encoding="utf-8")

    rec_map = {r["case_id"]: r for r in records}

    try:
        for idx, cid in enumerate(missing_ids, 1):
            c = cases[cid]
            rec = rec_map[cid]
            print(f"[{idx}/{len(missing_ids)}] Scoring {cid} ({c['category']})...")

            # Fast deterministic retrieval reconstruction
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

            contexts = []
            for k, v in retrievals_user.items():
                s = pipeline._format_retrievals({k: v}).strip()
                if s: contexts.append(s)
            for k, v in retrievals_ocr.items():
                s = pipeline._format_retrievals({k: v}).strip()
                if s: contexts.append(s)
            if not contexts:
                contexts = ["No retrieved evidence."]

            ans_core = rec.get("answer_core", "")
            ans_full = rec.get("answer_full", "")
            user_input_str = c["user_text"] if c.get("user_text") else f"Analyze medication label: {ocr_text}"

            ragas_data = {
                "user_input": [user_input_str],
                "question": [user_input_str],
                "response": [ans_core if ans_core else "No answer provided."],
                "retrieved_contexts": [contexts],
                "reference": [c["reference"]],
            }
            ragas_ds = Dataset.from_dict(ragas_data)

            if c["expected_behavior"] == "abstain":
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
                            if m in rec["nan_reasons"]:
                                del rec["nan_reasons"][m]
                        if m == "faithfulness":
                            rec["faithfulness_core"] = val
                        else:
                            rec[m] = val

                # Evaluate answer_full faithfulness
                ragas_full_data = {
                    "user_input": [user_input_str],
                    "question": [user_input_str],
                    "response": [ans_full if ans_full else "No answer provided."],
                    "retrieved_contexts": [contexts],
                    "reference": [c["reference"]],
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

                # Unsupported statement diagnostics
                core_f = rec["faithfulness_core"]
                if core_f is not None and core_f < 1.0 and custom_faithfulness.last_verdicts_output:
                    verdicts = custom_faithfulness.last_verdicts_output.statements
                    for v in verdicts:
                        if v.verdict == 0:
                            f_score = compute_best_fuzzy_match(v.statement, contexts)
                            b_plate = is_boilerplate_statement(v.statement)
                            trunc = rec.get("likely_prompt_truncated", False)
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

                # Clean any previous ragas_eval_exception
                rec["nan_reasons"].pop("ragas_eval_exception", None)

            except Exception as e:
                print(f"   ⚠️ Rescoring failed for {cid}: {e}")
                rec["nan_reasons"]["ragas_eval_exception"] = str(e)

            print(
                f"   ↳ Result: FaithCore={rec['faithfulness_core']}, FaithFull={rec['faithfulness_full']}, "
                f"Relevancy={rec['answer_relevancy']}, Prec={rec['context_precision']}, Rec={rec['context_recall']}"
            )

            # Persist intermediate results safely
            with open(per_case_jsonl, "w", encoding="utf-8") as f_out:
                for item in records:
                    f_out.write(json.dumps(item) + "\n")

    finally:
        f_unsupported.close()
        f_taxonomy.close()

    print("\n📊 Computing updated summary statistics...")
    summary = compute_evaluation_summary(per_case_jsonl)
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Update metadata judge info
    if metadata_json.exists():
        with open(metadata_json, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["judge"] = {
            "base_url": judge_base_url,
            "model": judge_model,
        }
        meta["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        with open(metadata_json, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    print(f"✅ Successfully rescored all missing judge metrics. Results in {results_dir}")


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "evaluation/e2e/results/R0_offline"
    rescore_missing(target_dir)
