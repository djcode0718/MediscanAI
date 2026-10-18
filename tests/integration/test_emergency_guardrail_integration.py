#!/usr/bin/env python3
"""
MediScanAI — Phase 1.2.d Controlled Emergency Guardrail Integration Test Suite
Verifies:
1. Feature flag disabled mode preserves 100% baseline behavior.
2. Feature flag enabled mode correctly executes pre-gen fast-path and post-gen enforcement.
3. All 19 required clinical, adversarial, multimodal, and failure scenarios.
4. Privacy-conscious telemetry (no raw queries or medical responses in audit logs).
5. Rollback verification.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core.config import Settings
from app.core import Pipeline
from app.guardrail import EmergencyGuardrail, EmergencyDecision, MANDATORY_HEADER, MANDATORY_TEXT


# Fixtures
@pytest.fixture
def disabled_settings():
    return Settings(
        EMERGENCY_GUARDRAIL_ENABLED=False,
        EMERGENCY_GUARDRAIL_CONFIG_PATH="app/guardrail_config.json",
        EMERGENCY_GUARDRAIL_FAST_PATH=True,
    )


@pytest.fixture
def enabled_settings():
    return Settings(
        EMERGENCY_GUARDRAIL_ENABLED=True,
        EMERGENCY_GUARDRAIL_CONFIG_PATH="app/guardrail_config.json",
        EMERGENCY_GUARDRAIL_FAST_PATH=True,
    )


@pytest.fixture
def mock_retriever():
    ret = MagicMock()
    ret.search_specific.return_value = []
    return ret


# --- Group 1: Feature Flag and Disabled Mode Baseline Fidelity ---

def test_feature_flag_disabled_by_default():
    """Verify that feature flag defaults to disabled and guardrail is None."""
    default_settings = Settings()
    assert default_settings.EMERGENCY_GUARDRAIL_ENABLED is False


def test_disabled_mode_preserves_baseline_pipeline(disabled_settings, mock_retriever):
    """Verify that when disabled, pipeline runs normal generation without guardrail."""
    pipeline = Pipeline(settings=disabled_settings, retriever=mock_retriever)
    assert pipeline.guardrail is None

    with patch("app.core.generate_with_mode", return_value="Baseline advice for chest pain."):
        result = pipeline.run(user_text="Chest pain")
        assert "guardrail" not in result["meta"]
        assert result["card"]["llm_output"] == "Baseline advice for chest pain."
        assert "guardrail_fast_path_ms" not in result["pipeline_timings"]


# --- Group 2: Emergency Fast-Path (Pre-Generation) ---

def test_med_bench_038_fast_path_resolution(enabled_settings, mock_retriever):
    """Verify MED-BENCH-038 'Chest pain' immediately triggers pre-gen fast-path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    assert pipeline.guardrail is not None

    result = pipeline.run(user_text="Chest pain")
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-01-CARDIOVASCULAR-CHEST-PAIN"
    output = result["card"]["llm_output"]
    assert "112" in output
    assert "911" in output
    assert "Emergency Department" in output
    assert "Do not wait for a routine appointment or outpatient consultation" in output
    assert "Do not drive yourself" in output
    assert MANDATORY_HEADER in output
    assert MANDATORY_TEXT in output
    # Verify retrieval was completely bypassed
    assert mock_retriever.search_specific.call_count == 0


def test_severe_respiratory_distress(enabled_settings, mock_retriever):
    """Verify acute severe respiratory distress triggers fast-path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    result = pipeline.run(user_text="Severe shortness of breath, gasping for air, bluish lips")
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-02-RESPIRATORY-DISTRESS"


def test_stroke_fast_symptoms(enabled_settings, mock_retriever):
    """Verify FAST stroke symptoms trigger fast-path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    result = pipeline.run(user_text="Sudden weakness on one side of face with slurred speech")
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-03-NEUROLOGICAL-STROKE"


def test_acute_anaphylaxis(enabled_settings, mock_retriever):
    """Verify acute anaphylaxis triggers fast-path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    result = pipeline.run(user_text="Severe throat swelling and anaphylaxis after bee sting")
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-02-RESPIRATORY-DISTRESS"


def test_unconsciousness_collapse(enabled_settings, mock_retriever):
    """Verify unconsciousness and sudden collapse triggers fast-path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    result = pipeline.run(user_text="Patient collapsed and is unconscious and unresponsive")
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-04-UNCONSCIOUSNESS-COLLAPSE"


def test_mixed_symptoms_precedence(enabled_settings, mock_retriever):
    """Verify emergency symptom takes precedence over co-occurring minor symptoms."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    result = pipeline.run(user_text="Mild runny nose, slight dry cough, and crushing chest pain")
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-01-CARDIOVASCULAR-CHEST-PAIN"


# --- Group 3: Non-Emergency, Negation, and History Gating ---

def test_routine_headache_pass_through(enabled_settings, mock_retriever):
    """Verify routine headache passes through to generation without false alarm."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Rest and drink plenty of water."):
        result = pipeline.run(user_text="Mild dull headache for 2 hours after working on computer")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False
        assert result["card"]["llm_output"] == "Rest and drink plenty of water."


def test_routine_lipitor_metformin(enabled_settings, mock_retriever):
    """Verify routine drug lookups pass through untouched."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Information on Lipitor and Metformin."):
        result = pipeline.run(user_text="What is the mechanism and dose of Metformin and Lipitor?")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False
        assert result["card"]["llm_output"] == "Information on Lipitor and Metformin."


def test_routine_oral_suspension(enabled_settings, mock_retriever):
    """Verify pediatric suspension queries pass through untouched."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Administer according to body weight."):
        result = pipeline.run(user_text="How to administer paracetamol oral suspension for child?")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False


def test_explicit_negation_no_emergency(enabled_settings, mock_retriever):
    """Verify explicit negation ('no chest pain') does not trigger emergency alert."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Hydrate and rest for viral cough."):
        result = pipeline.run(user_text="I have a runny nose and cough, but no chest pain and without shortness of breath")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False


def test_historical_symptoms_no_emergency(enabled_settings, mock_retriever):
    """Verify symptoms in remote past do not trigger emergency alert."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Seasonal allergy recommendations."):
        result = pipeline.run(user_text="I had chest pain 5 years ago in 2019, now asking about seasonal allergies")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False


def test_family_history_no_emergency(enabled_settings, mock_retriever):
    """Verify family history mentions do not trigger emergency alert."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Healthy diet recommendations."):
        result = pipeline.run(user_text="My father had a heart attack last year; what are healthy diet options?")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False


def test_substring_collisions_no_emergency(enabled_settings, mock_retriever):
    """Verify substring collisions like 'chest decongestant' do not trigger emergency."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Decongestant usage guide."):
        result = pipeline.run(user_text="What chest decongestant is safe for nasal congestion?")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False


def test_fictional_medicine_negative_control(enabled_settings, mock_retriever):
    """Verify negative control out-of-domain query preserves abstention."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="I cannot provide medical advice for questions unrelated to human health."):
        result = pipeline.run(user_text="How to bake sourdough bread?")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False
        assert "cannot provide medical advice" in result["card"]["llm_output"]


# --- Group 4: Input Modalities ---

def test_voice_transcription_modality(enabled_settings, mock_retriever):
    """Verify voice transcription format triggers emergency fast path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    # When Whisper transcribes speech, it appends '(Spoken: ...)'
    query = "I felt unwell (Spoken: crushing chest pain radiating to left arm)"
    result = pipeline.run(user_text=query)
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True


def test_ocr_packaging_text_modality(enabled_settings, mock_retriever):
    """Verify benign medicine packaging OCR text does not trigger false emergency."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    with patch("app.core.generate_with_mode", return_value="Amoxicillin indication guide."):
        result = pipeline.run(user_text="Amoxicillin 500mg capsules")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is False


# --- Group 5: Post-Generation Enforcement and Contradiction Elimination ---

def test_post_generation_contradiction_elimination(enabled_settings, mock_retriever):
    """Verify post-generation guardrail strips routine outpatient advice when emergency fires."""
    # Create pipeline with fast_path disabled to force request through generation
    settings = Settings(
        EMERGENCY_GUARDRAIL_ENABLED=True,
        EMERGENCY_GUARDRAIL_CONFIG_PATH="app/guardrail_config.json",
        EMERGENCY_GUARDRAIL_FAST_PATH=False,
    )
    pipeline = Pipeline(settings=settings, retriever=mock_retriever)

    unsafe_llm_output = (
        "Based on context, chest pain can indicate acute myocardial infarction. "
        "Please schedule an appointment with your primary care doctor next week."
    )
    with patch("app.core.generate_with_mode", return_value=unsafe_llm_output):
        result = pipeline.run(user_text="Chest pain")
        assert result["meta"]["fast_path"] is False
        assert result["meta"]["guardrail"]["is_emergency"] is True
        output = result["card"]["llm_output"]
        assert "112" in output
        assert "Emergency Department" in output
        # Contradictory routine appointment advice must be suppressed
        assert "schedule an appointment with your primary care doctor" not in output.lower()
        assert "Do not wait for a routine appointment or outpatient consultation" in output


def test_idempotent_guardrail_application():
    """Verify applying guardrail repeatedly produces clean, non-duplicated text."""
    guardrail = EmergencyGuardrail()
    query = "Chest pain"
    resp1, dec1 = guardrail.apply_guardrail(query, baseline_response="")
    assert dec1.is_emergency is True

    # Re-apply guardrail to already-guarded output
    resp2, dec2 = guardrail.apply_guardrail(query, baseline_response=resp1)
    assert resp2.count("### 🚨 Immediate Emergency Medical Guidance") == 1
    assert resp2.count("### ⚠️ Important Warning") == 1


# --- Group 6: Fault Tolerance and Fallback Behavior ---

def test_fallback_on_corrupted_config(mock_retriever):
    """Verify guardrail engages static fail-safe fallback when config path is invalid."""
    settings = Settings(
        EMERGENCY_GUARDRAIL_ENABLED=True,
        EMERGENCY_GUARDRAIL_CONFIG_PATH="nonexistent_config_file.json",
        EMERGENCY_GUARDRAIL_FAST_PATH=True,
    )
    pipeline = Pipeline(settings=settings, retriever=mock_retriever)
    # Primary config load failed, so fail-safe fallback must engage
    assert pipeline.guardrail is not None
    assert pipeline.guardrail.is_valid is False

    result = pipeline.run(user_text="Chest pain")
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert result["meta"]["guardrail"]["fallback_engaged"] is True
    assert "112" in result["card"]["llm_output"]
    assert "Emergency Department" in result["card"]["llm_output"]


# --- Group 7: Telemetry and Data Minimization ---

def test_telemetry_data_minimization(enabled_settings, mock_retriever):
    """Verify decision dictionary contains no raw patient query text or response text."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    result = pipeline.run(user_text="Crushing chest pain and difficulty breathing")
    guardrail_meta = result["meta"]["guardrail"]

    # Verify structured fields
    assert "is_emergency" in guardrail_meta
    assert "fired_rule_id" in guardrail_meta
    assert "category" in guardrail_meta
    assert "severity" in guardrail_meta
    assert "detection_latency_ms" in guardrail_meta

    # Verify NO raw patient text or complete medical response in telemetry dictionary
    assert "user_text" not in guardrail_meta
    assert "query" not in guardrail_meta
    assert "llm_output" not in guardrail_meta
    assert "Crushing chest pain and difficulty breathing" not in guardrail_meta.values()


# --- Group 8: Rollback Verification ---

def test_rollback_restoration(disabled_settings, mock_retriever):
    """Verify that toggling EMERGENCY_GUARDRAIL_ENABLED back to False completely restores legacy path."""
    pipeline = Pipeline(settings=disabled_settings, retriever=mock_retriever)
    assert pipeline.guardrail is None

    legacy_advice = "General health education response."
    with patch("app.core.generate_with_mode", return_value=legacy_advice):
        result = pipeline.run(user_text="Chest pain")
        assert "guardrail" not in result["meta"]
        assert result["card"]["llm_output"] == legacy_advice
        assert result["meta"]["mismatch_details"] == "Mismatch check not performed in this pipeline version."
