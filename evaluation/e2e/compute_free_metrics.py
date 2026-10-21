#!/usr/bin/env python3
"""
Compute Free Metrics (no LLM judge) for R0s, A1, and A2 (Step 2).
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import json
import re
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
from transformers import AutoModelForSequenceClassification

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.e2e.score_phase01b import compute_hhem_faithfulness, compute_deterministic_evidence_metrics

def stats(vals):
    valid = [v for v in vals if v is not None and not np.isnan(v)]
    if not valid:
        return {"mean": 0.0, "median": 0.0, "p10": 0.0, "p95": 0.0, "n": 0}
    arr = np.array(valid, dtype=float)
    return {
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "p10": round(float(np.percentile(arr, 10)), 4),
        "p95": round(float(np.percentile(arr, 95)), 4),
        "n": len(valid),
    }

def main():
    print("Loading HHEM model...")
    hhem = AutoModelForSequenceClassification.from_pretrained(
        "vectara/hallucination_evaluation_model", trust_remote_code=True
    )

    runs = ["R0s", "A1", "A2"]
    data = {}
    for r in runs:
        with open(REPO_ROOT / f"evaluation/e2e/results/{r}/generated_cases.jsonl") as f:
            data[r] = [json.loads(line) for line in f if line.strip()]

    results = {}
    for rname in runs:
        cases = data[rname]
        hhem_scores = []
        ev_hit3_list = []
        ev_mrr_list = []
        raw_hit5_list = []
        ev_tokens_list = []
        prompt_tokens_list = []
        latencies_list = []
        truncated_list = []

        for c in cases:
            # Deterministic metrics
            shown_items = c.get("shown_evidence_items", [])
            raw_ids = c.get("raw_retrieved_ids", [])
            ref_ids = c.get("reference_context_ids", [])
            eq_ids = c.get("equivalent_ids", [])

            h3, mrr, rh5 = compute_deterministic_evidence_metrics(
                shown_items, raw_ids, ref_ids, eq_ids, k=3
            )
            ev_hit3_list.append(h3)
            ev_mrr_list.append(mrr)
            raw_hit5_list.append(rh5)

            # Tokens & Latency
            ev_tokens_list.append(c.get("evidence_tokens", 0))
            prompt_tokens_list.append(c.get("prompt_tokens", 0))
            latencies_list.append(c.get("latency_ms", 0))
            truncated_list.append(1.0 if c.get("truncated_by_length", False) else 0.0)

            # HHEM
            premise = "\n".join(c.get("retrieved_contexts", []))
            ans_core = c.get("answer_core", "")
            hscore = compute_hhem_faithfulness(hhem, premise, ans_core)
            hhem_scores.append(hscore)

        results[rname] = {
            "n": len(cases),
            "hhem": stats(hhem_scores),
            "ev_hit3": stats(ev_hit3_list),
            "ev_mrr": stats(ev_mrr_list),
            "raw_hit5": stats(raw_hit5_list),
            "ev_tokens": stats(ev_tokens_list),
            "prompt_tokens": stats(prompt_tokens_list),
            "latency_ms": stats(latencies_list),
            "truncation_pct": round(float(np.mean(truncated_list)) * 100, 2),
            "hhem_raw": hhem_scores,
        }

    # A2 citation stats
    a2_cases = data["A2"]
    invalid_tag_cases = sum(1 for c in a2_cases if c.get("citation_stats", {}).get("invalid_tags"))
    abstained_total = sum(1 for c in a2_cases if c.get("citation_stats", {}).get("abstained", False))

    # Sentence-level citation pct across A2
    total_sentences = 0
    sentences_with_tag = 0
    tag_pattern = re.compile(r"\[E\d+\]")

    for c in a2_cases:
        raw_out = c.get("raw_llm_output", "")
        # Split sentences roughly
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", raw_out) if s.strip()]
        for s in sents:
            if s.startswith("#") or s.startswith("**Verdict"):
                continue
            total_sentences += 1
            if tag_pattern.search(s):
                sentences_with_tag += 1

    pct_sentences_tagged = round((sentences_with_tag / total_sentences) * 100, 2) if total_sentences else 0.0

    # Abstention per category for A2
    cats = sorted(list(set(c["category"] for c in a2_cases)))
    cat_abstention = {}
    for cat in cats:
        cat_cases = [c for c in a2_cases if c["category"] == cat]
        abs_c = sum(1 for c in cat_cases if c.get("citation_stats", {}).get("abstained", False))
        cat_abstention[cat] = {
            "abstained": abs_c,
            "total": len(cat_cases),
            "rate_pct": round((abs_c / len(cat_cases)) * 100, 2)
        }

    output_payload = {
        "results": results,
        "a2_citations": {
            "invalid_tag_rate_pct": round((invalid_tag_cases / len(a2_cases)) * 100, 2),
            "pct_sentences_with_tag": pct_sentences_tagged,
            "total_sentences_checked": total_sentences,
            "sentences_with_tag": sentences_with_tag,
            "overall_abstention_pct": round((abstained_total / len(a2_cases)) * 100, 2),
            "by_category": cat_abstention,
        }
    }

    out_file = REPO_ROOT / "evaluation/e2e/results/free_metrics_summary.json"
    with open(out_file, "w") as f:
        json.dump(output_payload, f, indent=2)
    print(f"Saved free metrics to: {out_file}")

if __name__ == "__main__":
    main()
