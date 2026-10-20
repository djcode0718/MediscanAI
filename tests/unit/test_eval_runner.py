#!/usr/bin/env python3
"""
Unit tests for End-to-End Evaluation Runner (Step 4).
"""

import json
from pathlib import Path
import pytest

from evaluation.e2e.run_eval import (
    is_boilerplate_statement,
    compute_best_fuzzy_match,
    compute_deterministic_id_metrics,
    compute_evaluation_summary,
)


def test_is_boilerplate_statement():
    assert is_boilerplate_statement("Please consult your doctor before taking this medication.") is True
    assert is_boilerplate_statement("This advice is for informational purposes only.") is True
    assert is_boilerplate_statement("Call 911 or emergency services immediately.") is True
    assert is_boilerplate_statement("Atorvastatin is an HMG-CoA reductase inhibitor.") is False
    assert is_boilerplate_statement("Common side effects include headache and nausea.") is False


def test_compute_best_fuzzy_match():
    statement = "Atorvastatin reduces the risk of myocardial infarction."
    contexts = [
        "Brand: Lipitor; Generic: atorvastatin calcium. Indications: Atorvastatin reduces the risk of myocardial infarction and stroke.",
        "Other unrelated clinical text."
    ]
    score = compute_best_fuzzy_match(statement, contexts)
    assert score > 0.70

    unrelated_score = compute_best_fuzzy_match("Completely nonexistent alien disease entity.", contexts)
    assert unrelated_score < 0.35


def test_compute_deterministic_id_metrics_with_equivalents():
    # Case with disease chunk and drug
    retrieved_dict = {
        "diseases": ["disease_chunk_10", "disease_chunk_20"],
        "drugs": ["drug_999", "drug_555"],  # drug_999 is equivalent to target drug_123
        "drug_dict": [],
    }
    target_ids = ["disease_chunk_10", "drug_123"]
    equiv_ids = ["drug_999"]

    # In top 5:
    # flat retrieved: disease_chunk_10, disease_chunk_20, drug_999, drug_555
    # targets + equivs: disease_chunk_10, drug_123, drug_999
    # hits: disease_chunk_10 (yes), drug_999 (yes) -> 2 hits out of 4 items
    p_k, rec = compute_deterministic_id_metrics(retrieved_dict, target_ids, equiv_ids, k=5)
    assert p_k == 0.5  # 2/4
    assert rec == 1.0  # both disease_chunk_10 and drug_123 (via drug_999) hit


def test_compute_evaluation_summary(tmp_path):
    jsonl_file = tmp_path / "test_results.jsonl"
    recs = [
        {
            "case_id": "E2E-001",
            "category": "symptom_only",
            "prompt_tokens": 1000,
            "ollama_prompt_eval_count": 950,
            "latency_ms": 2000,
            "faithfulness_core": 0.8,
            "faithfulness_full": 0.5,
            "answer_relevancy": 0.9,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "id_precision_at_5": 0.4,
            "id_recall": 1.0,
            "likely_prompt_truncated": False,
            "truncated_by_length": False,
        },
        # Duplicate record for E2E-001 (simulate resume / retry - should be deduplicated)
        {
            "case_id": "E2E-001",
            "category": "symptom_only",
            "prompt_tokens": 1000,
            "ollama_prompt_eval_count": 1000,
            "latency_ms": 2000,
            "faithfulness_core": 1.0,
            "faithfulness_full": 0.7,
            "answer_relevancy": 0.9,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "id_precision_at_5": 0.4,
            "id_recall": 1.0,
            "likely_prompt_truncated": False,
            "truncated_by_length": False,
        },
        {
            "case_id": "E2E-002",
            "category": "emergency",
            "prompt_tokens": 500,
            "ollama_prompt_eval_count": 500,
            "latency_ms": 50,
            "faithfulness_core": None,
            "faithfulness_full": None,
            "answer_relevancy": None,
            "context_precision": None,
            "context_recall": None,
            "id_precision_at_5": None,
            "id_recall": None,
            "emergency_hit": True,
            "likely_prompt_truncated": False,
            "truncated_by_length": False,
        },
    ]
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")

    summary = compute_evaluation_summary(jsonl_file)
    assert summary["total_records"] == 2  # Deduplicated E2E-001
    assert summary["metrics"]["faithfulness_core"]["n"] == 1
    assert summary["metrics"]["faithfulness_core"]["mean"] == 1.0
    assert summary["emergency_fast_path_hit_rate"] == 1.0
    assert summary["proxy_vs_real_token_ratio"]["mean"] == 1.0
