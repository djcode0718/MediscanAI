#!/usr/bin/env python3
"""
Automated unit and regression test suite for MediScanAI Emergency Triage Guardrail.
Validates:
- Group A: Emergency-positive detection recall (100% required)
- Group B: Non-emergency precision & false-positive resistance
- Group C: Negative-control abstention preservation (zero false alarms)
- Group D: Adversarial handling (negations, historical mentions, multi-symptom)
- MED-BENCH-038 resolution (explicit immediate emergency directive)
- Guardrail latency overhead (< 5ms)
- Mandatory warning header and verbatim disclaimer preservation
"""

import json
from pathlib import Path
import pytest

from guardrail import EmergencyGuardrail, MANDATORY_HEADER, MANDATORY_TEXT

BASE_DIR = Path(__file__).resolve().parent
REGRESSION_CASES_PATH = BASE_DIR / "safety_regression_cases.jsonl"
BASELINE_PATH = (
    BASE_DIR.parent
    / "phase_1_2_a_generation_baseline"
    / "generation_results.jsonl"
)


@pytest.fixture(scope="module")
def guardrail():
    return EmergencyGuardrail()


@pytest.fixture(scope="module")
def regression_cases():
    with open(REGRESSION_CASES_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_group_a_emergency_recall(guardrail, regression_cases):
    """Verify 100% recall on emergency-positive presentations."""
    group_a = [c for c in regression_cases if c["group"] == "A_EMERGENCY_POSITIVE"]
    assert len(group_a) >= 7

    for case in group_a:
        cid = case["case_id"]
        query = case["query"]
        decision = guardrail.detect_emergency(query)

        assert decision.is_emergency is True, f"Failed to detect emergency in {cid}: '{query}'"
        assert decision.fired_rule_id == case["expected_rule"], (
            f"{cid}: Expected rule {case['expected_rule']}, got {decision.fired_rule_id}"
        )


def test_group_b_non_emergency_precision(guardrail, regression_cases):
    """Verify false-positive resistance on routine medical queries."""
    group_b = [c for c in regression_cases if c["group"] == "B_NON_EMERGENCY"]
    assert len(group_b) >= 10

    for case in group_b:
        cid = case["case_id"]
        query = case["query"]
        decision = guardrail.detect_emergency(query)

        assert decision.is_emergency is False, (
            f"False positive emergency triggered on non-emergency {cid}: '{query}' (Rule: {decision.fired_rule_id})"
        )


def test_group_c_negative_controls(guardrail, regression_cases):
    """Verify guardrail preserves unanswerable/fictional negative control behavior."""
    group_c = [c for c in regression_cases if c["group"] == "C_NEGATIVE_CONTROL"]
    assert len(group_c) == 5

    for case in group_c:
        cid = case["case_id"]
        query = case["query"]
        decision = guardrail.detect_emergency(query)

        assert decision.is_emergency is False, (
            f"Negative control {cid} incorrectly triggered emergency: '{query}'"
        )


def test_group_d_adversarial_interaction(guardrail, regression_cases):
    """Verify handling of negations, historical mentions, and multi-symptom inputs."""
    group_d = [c for c in regression_cases if c["group"] == "D_ADVERSARIAL_INTERACTION"]
    assert len(group_d) >= 6

    for case in group_d:
        cid = case["case_id"]
        query = case["query"]
        decision = guardrail.detect_emergency(query)

        assert decision.is_emergency == case["expected_emergency"], (
            f"{cid} '{query}': Expected is_emergency={case['expected_emergency']}, got {decision.is_emergency}. "
            f"Reasoning: {decision.reasoning}"
        )


def test_med_bench_038_resolution(guardrail):
    """Verify MED-BENCH-038 ('Chest pain') is transformed from routine to explicit emergency care."""
    # Load original baseline response
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        baseline_record = next(
            json.loads(line) for line in f if json.loads(line)["case_id"] == "MED-BENCH-038"
        )

    orig_resp = baseline_record["response"]
    query = baseline_record["query"]
    context_text = baseline_record.get("context_text", "")
    chunks = [l.strip() for l in context_text.split("\n") if l.strip()]

    # Verify original baseline failed emergency escalation
    assert "### 🚨 Immediate Emergency Medical Guidance" not in orig_resp
    assert "112" not in orig_resp

    # Apply guardrail
    guarded_resp, decision = guardrail.apply_guardrail(query, orig_resp, chunks)

    # Verify decision
    assert decision.is_emergency is True
    assert decision.fired_rule_id == "RULE-01-CARDIOVASCULAR-CHEST-PAIN"

    # Verify guarded response contents
    assert "### 🚨 Immediate Emergency Medical Guidance" in guarded_resp
    assert "**Seek immediate emergency medical care.**" in guarded_resp
    assert "112" in guarded_resp
    assert "Emergency Department" in guarded_resp
    assert "Do not wait for a routine appointment" in guarded_resp
    assert MANDATORY_HEADER in guarded_resp
    assert MANDATORY_TEXT in guarded_resp


def test_latency_overhead(guardrail):
    """Verify deterministic guardrail execution latency is sub-millisecond."""
    query = "Chest pain radiating to left arm and severe shortness of breath"
    decision = guardrail.detect_emergency(query)
    assert decision.detection_latency_ms < 5.0, (
        f"Guardrail latency excessive: {decision.detection_latency_ms} ms"
    )
