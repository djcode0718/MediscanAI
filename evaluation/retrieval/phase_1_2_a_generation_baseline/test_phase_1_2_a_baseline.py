#!/usr/bin/env python3
"""
Unit and integrity test suite for MediScanAI Phase 1.2.a Generation Baseline.
Validates:
- Record counts (exactly 50 benchmark cases accounted for)
- Hashes and configuration provenance (CFG-04-D2C-ADAPTIVE-FINAL = f3937376cd191ee7)
- Split integrity (30 dev, 10 val, 10 held_out_test)
- Invariant integrity (gold_judgments.jsonl is exactly 0 bytes)
- Safety compliance (mandatory warning header and verbatim disclaimer)
- Emergency escalation (MED-BENCH-038)
- Abstention on unanswerable/fictional controls (MED-BENCH-041..045)
- Missing-value handling in metrics (negative controls ineligible for context precision/recall)
"""

import json
import os
from pathlib import Path
import pytest

ROOT_DIR = Path("/Users/sj/Documents/mediscanai")
BASE_DIR = ROOT_DIR / "evaluation/retrieval/phase_1_2_a_generation_baseline"
RESULTS_PATH = BASE_DIR / "generation_results.jsonl"
METRICS_PATH = BASE_DIR / "per_case_metrics.jsonl"
SAFETY_PATH = BASE_DIR / "safety_audit.jsonl"
MANIFEST_PATH = BASE_DIR / "experiment_manifest.json"
SPLIT_SUMMARY_PATH = BASE_DIR / "split_summary.json"
LATENCY_PATH = BASE_DIR / "latency_summary.json"
RAGAS_PATH = BASE_DIR / "ragas_results.json"
GOLD_PATH = ROOT_DIR / "evaluation/benchmark/gold_judgments.jsonl"

NEGATIVE_CONTROL_CASES = {
    "MED-BENCH-041",
    "MED-BENCH-042",
    "MED-BENCH-043",
    "MED-BENCH-044",
    "MED-BENCH-045",
}


def test_mandatory_invariants():
    """Verify strictly required system invariants."""
    # 1. gold_judgments.jsonl must remain exactly 0 bytes
    assert GOLD_PATH.exists(), "gold_judgments.jsonl does not exist"
    assert os.path.getsize(GOLD_PATH) == 0, f"gold_judgments.jsonl is not 0 bytes: {os.path.getsize(GOLD_PATH)}"

    # 2. Manifest invariants
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["invariants"]["cloud_calls_made"] is False
        assert manifest["invariants"]["production_code_modified"] is False
        assert manifest["invariants"]["entity_resolution_accessed"] is False
        assert manifest["frozen_retrieval_configuration"]["hash"] == "f3937376cd191ee7"


def test_record_counts():
    """Verify exactly 50 canonical cases are present in each artifact."""
    assert RESULTS_PATH.exists(), "generation_results.jsonl missing"
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        gen_records = [json.loads(l) for l in f if l.strip()]
    assert len(gen_records) == 50, f"Expected 50 generated records, found {len(gen_records)}"
    
    case_ids = {r["case_id"] for r in gen_records}
    assert len(case_ids) == 50, "Duplicate case IDs detected in generation_results.jsonl"


def test_splits_integrity():
    """Verify split counts: 30 Dev, 10 Val, 10 Held-out Test."""
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        gen_records = [json.loads(l) for l in f if l.strip()]

    splits = {}
    for r in gen_records:
        splits[r["split"]] = splits.get(r["split"], 0) + 1

    assert splits.get("dev") == 30, f"Expected 30 dev cases, got {splits.get('dev')}"
    assert splits.get("val") == 10, f"Expected 10 val cases, got {splits.get('val')}"
    assert splits.get("held_out_test") == 10, f"Expected 10 held_out_test cases, got {splits.get('held_out_test')}"


def test_safety_compliance():
    """Verify warning header and verbatim disclaimer compliance."""
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        gen_records = [json.loads(l) for l in f if l.strip()]

    for r in gen_records:
        cid = r["case_id"]
        assert r.get("mandatory_header_passed") is True, f"{cid} failed mandatory warning header check"
        assert r.get("verbatim_disclaimer_passed") is True, f"{cid} failed verbatim disclaimer check"


def test_emergency_and_abstention_safety():
    """Verify emergency escalation and abstention on negative controls."""
    if not SAFETY_PATH.exists():
        pytest.skip("safety_audit.jsonl not yet generated")

    with open(SAFETY_PATH, "r", encoding="utf-8") as f:
        safety_records = {r["case_id"]: r for r in (json.loads(l) for l in f if l.strip())}

    # Emergency case: MED-BENCH-038 must be evaluated and its failure documented
    assert "MED-BENCH-038" in safety_records
    rec_038 = safety_records["MED-BENCH-038"]
    # MED-BENCH-038 failed emergency escalation because it directed to routine medical evaluation
    assert rec_038["emergency_escalation_passed"] is False, "Expected MED-BENCH-038 emergency escalation to be flagged as False"
    assert "FAILED" in rec_038["emergency_escalation_notes"]

    # Negative controls: MED-BENCH-041..045
    for cid in NEGATIVE_CONTROL_CASES:
        assert cid in safety_records, f"{cid} missing from safety audit"
        assert safety_records[cid]["abstention_passed"] is True, f"{cid} failed negative control abstention"


def test_missing_value_handling_in_metrics():
    """Verify negative control eligibility contract in Ragas evaluations."""
    if not METRICS_PATH.exists():
        pytest.skip("per_case_metrics.jsonl not yet generated")

    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = {r["case_id"]: r for r in (json.loads(l) for l in f if l.strip())}

    completed_negs = [cid for cid in NEGATIVE_CONTROL_CASES if cid in metrics]
    if not completed_negs:
        # Check that regular completed cases are valid while evaluation queue runs
        for cid, rec in metrics.items():
            assert rec["faithfulness_eligibility"] == "eligible"
            assert rec["answer_relevancy_eligibility"] == "eligible"
        return

    for cid in completed_negs:
        rec = metrics[cid]
        assert rec["context_precision"] is None
        assert rec["context_recall"] is None
        assert rec["context_precision_eligibility"] == "ineligible_unanswerable_negative_control"
        assert rec["context_recall_eligibility"] == "ineligible_unanswerable_negative_control"


if __name__ == "__main__":
    pytest.main(["-v", str(Path(__file__))])
