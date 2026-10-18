#!/usr/bin/env python3
"""
Unit and integration tests for Phase 1.2.c proposed integration design.
Confined strictly to evaluation/retrieval/phase_1_2_c_integration_proposal/
Zero production code is modified.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest

from evaluation.retrieval.phase_1_2_c_integration_proposal.guardrail_integration import (
    IntegratedEmergencyGuardrail,
    GuardrailAuditRecord
)


def test_feature_flag_disabled_by_default():
    """Verify that by default (enabled=False), guardrail acts as transparent passthrough."""
    guardrail = IntegratedEmergencyGuardrail(enabled=False)
    query = "Severe crushing chest pain radiating to my left arm"
    baseline = "Here is some routine health info."

    # Pre-gen check should pass
    is_emerg, fast_path, audit_pre = guardrail.pre_generation_check(query)
    assert not is_emerg
    assert fast_path is None
    assert audit_pre.action_taken == "FEATURE_FLAG_DISABLED"

    # Post-gen guard should pass through baseline untouched
    guarded_resp, audit_post = guardrail.post_generation_guard(query, baseline)
    assert guarded_resp == baseline
    assert not audit_post.response_modified
    assert audit_post.action_taken == "FEATURE_FLAG_DISABLED"


def test_pre_generation_fast_path_emergency():
    """Verify that when enabled, Tier-1 emergencies trigger immediate fast-path return."""
    guardrail = IntegratedEmergencyGuardrail(enabled=True, fast_path_enabled=True)
    query = "Crushing chest pain and difficulty breathing"

    is_emerg, fast_path, audit = guardrail.pre_generation_check(query)
    assert is_emerg is True
    assert fast_path is not None
    assert "112" in fast_path or "911" in fast_path
    assert "Emergency Department" in fast_path
    assert audit.action_taken == "FAST_PATH_OVERRIDE"
    assert audit.is_emergency is True
    assert audit.response_modified is True
    assert audit.latency_ms < 5.0  # Ultra-fast sub-millisecond check


def test_post_generation_contradictory_advice_elimination():
    """Verify Gate 05: Contradictory routine appointment advice is eliminated in emergency response."""
    guardrail = IntegratedEmergencyGuardrail(enabled=True)
    query = "Chest pain"
    unsafe_baseline = (
        "Based on context, chest pain can indicate acute myocardial infarction. "
        "Please schedule an appointment with your primary care doctor next week."
    )

    guarded_resp, audit = guardrail.post_generation_guard(query, unsafe_baseline)
    assert audit.is_emergency is True
    assert audit.response_modified is True
    assert "112" in guarded_resp
    assert "Emergency Department" in guarded_resp
    # Routine appointment scheduling advice must be strictly eliminated
    assert "schedule an appointment with your primary care doctor" not in guarded_resp.lower()
    assert "Do not wait for a routine appointment or outpatient consultation" in guarded_resp


def test_non_emergency_pass_through_fidelity():
    """Verify that non-emergency queries pass through byte-for-byte unchanged."""
    guardrail = IntegratedEmergencyGuardrail(enabled=True)
    query = "I have a mild headache for 2 hours after working on a laptop."
    safe_baseline = "Take a break, drink water, and rest in a dark quiet room."

    guarded_resp, audit = guardrail.post_generation_guard(query, safe_baseline)
    assert guarded_resp == safe_baseline
    assert audit.is_emergency is False
    assert audit.response_modified is False
    assert audit.action_taken == "PASS_THROUGH"


def test_negative_control_abstention_preserved():
    """Verify Gate 03: Negative controls preserve medical abstention without false alarms."""
    guardrail = IntegratedEmergencyGuardrail(enabled=True)
    query = "How do I bake sourdough bread?"
    abstention_baseline = "I cannot provide medical advice for questions unrelated to human health."

    guarded_resp, audit = guardrail.post_generation_guard(query, abstention_baseline)
    assert guarded_resp == abstention_baseline
    assert audit.is_emergency is False
    assert audit.action_taken == "ABSTENTION_PRESERVED"
    assert not audit.response_modified


def test_negation_handling_pass():
    """Verify that explicit symptom negation does not trigger false positive emergency escalation."""
    guardrail = IntegratedEmergencyGuardrail(enabled=True)
    query = "I have a runny nose and slight cough, but no chest pain and without shortness of breath."
    baseline = "Rest and maintain hydration for common cold symptoms."

    guarded_resp, audit = guardrail.post_generation_guard(query, baseline)
    assert guarded_resp == baseline
    assert audit.is_emergency is False
    assert not audit.response_modified


def test_fail_safe_fallback_on_fault():
    """Verify Gate 06: Missing or invalid config does not drop emergency signal (fail-safe fallback)."""
    # Initialize with non-existent config path to simulate configuration fault
    guardrail = IntegratedEmergencyGuardrail(enabled=True, config_path=Path("/tmp/nonexistent_config.json"))
    assert guardrail._guardrail is None  # Init failed

    query = "Crushing chest pain radiating to left arm"
    baseline = "Some routine advice."

    # Guardrail should NOT crash or drop signal; it must engage fail-safe fallback
    guarded_resp, audit = guardrail.post_generation_guard(query, baseline)
    assert audit.is_emergency is True
    assert audit.fallback_engaged is True
    assert audit.action_taken == "FAILSAFE_EMERGENCY_OVERRIDE"
    assert "112" in guarded_resp
    assert "Emergency Department" in guarded_resp


def test_privacy_data_minimization():
    """Verify Gate 08: Audit records do not log raw patient text or generated response text."""
    guardrail = IntegratedEmergencyGuardrail(enabled=True)
    query = "Severe chest pain"
    baseline = "Some response"

    _, audit = guardrail.post_generation_guard(query, baseline)
    audit_dict = vars(audit)

    # Verify no raw patient query or response in audit dictionary
    assert "query" not in audit_dict
    assert "baseline_response" not in audit_dict
    assert "guarded_response" not in audit_dict
    assert "Severe chest pain" not in str(audit_dict)
    assert "Some response" not in str(audit_dict)
    # Verify expected structured metadata fields
    assert "event_type" in audit_dict
    assert "is_emergency" in audit_dict
    assert "latency_ms" in audit_dict
