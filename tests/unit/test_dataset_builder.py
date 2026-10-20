#!/usr/bin/env python3
"""
Unit tests for End-to-End Evaluation Dataset Generator (Step 3).
"""

import json
import random
from pathlib import Path
import pytest

from evaluation.e2e.build_dataset import build_noisy_ocr, clean_text, DATASET_PATH, STATS_PATH, README_PATH


def test_build_noisy_ocr_deterministic():
    rng1 = random.Random(42)
    res1 = build_noisy_ocr("Lipitor", "atorvastatin calcium", "20mg", rng1)
    
    rng2 = random.Random(42)
    res2 = build_noisy_ocr("Lipitor", "atorvastatin calcium", "20mg", rng2)
    
    assert res1 == res2
    assert "Lipitor" in res1 or "Lipit0r" in res1 or "L1pitor" in res1
    assert "20mg" in res1


def test_clean_text():
    assert clean_text("  hello   world \n test  ") == "hello world test"
    assert clean_text("") == ""
    assert clean_text(None) == ""


def test_dataset_file_structure():
    assert DATASET_PATH.exists(), f"Dataset file missing: {DATASET_PATH}"
    assert STATS_PATH.exists(), f"Stats file missing: {STATS_PATH}"
    assert README_PATH.exists(), f"README missing: {README_PATH}"

    cases = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            cases.append(json.loads(line))

    assert len(cases) == 110, f"Expected 110 cases, got {len(cases)}"

    # Required fields
    required_fields = {
        "case_id",
        "category",
        "user_text",
        "ocr_text",
        "reference",
        "reference_context_ids",
        "equivalent_ids",
        "expected_behavior",
        "reference_status",
    }

    category_counts = {}
    for case in cases:
        missing = required_fields - set(case.keys())
        assert not missing, f"Case {case.get('case_id')} missing fields: {missing}"
        assert case["reference_status"] == "auto_from_source"
        assert case["expected_behavior"] in ("answer", "abstain", "emergency")
        assert isinstance(case["reference_context_ids"], list)
        assert isinstance(case["equivalent_ids"], list)
        cat = case["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    expected_categories = {
        "symptom_only": 25,
        "medicine_only_clean_ocr": 15,
        "medicine_only_noisy_ocr": 15,
        "symptom_plus_medicine_match": 20,
        "symptom_plus_medicine_mismatch": 15,
        "unanswerable": 10,
        "emergency": 10,
    }
    assert category_counts == expected_categories


def test_unanswerable_and_emergency_invariants():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]

    unanswerables = [c for c in cases if c["category"] == "unanswerable"]
    assert len(unanswerables) == 10
    for u in unanswerables:
        assert u["expected_behavior"] == "abstain"
        assert u["reference_context_ids"] == []

    emergencies = [c for c in cases if c["category"] == "emergency"]
    assert len(emergencies) == 10
    for e in emergencies:
        assert e["expected_behavior"] == "emergency"
        assert e["reference_context_ids"] == []
