#!/usr/bin/env python3
"""
Phase 1.2.d.2 — Multimodal Emergency Detection and Production Startup Test Suite
Verifies:
1. Clean-process import and startup without pytest compatibility shim.
2. Image-only emergency detection and pre-generation fast-path.
3. Combined text + OCR emergency precedence and negation handling.
4. OCR exception resilience: independent emergency text preserved; image-only unreadable fallback.
5. Zero regressions in legacy disabled mode.
"""

import sys
import os
import subprocess
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.core.config import Settings
from app.core import Pipeline
from app.guardrail import EmergencyGuardrail, MANDATORY_HEADER, MANDATORY_TEXT


@pytest.fixture
def enabled_settings():
    return Settings(
        EMERGENCY_GUARDRAIL_ENABLED=True,
        EMERGENCY_GUARDRAIL_CONFIG_PATH="app/guardrail_config.json",
        EMERGENCY_GUARDRAIL_FAST_PATH=True,
    )


@pytest.fixture
def disabled_settings():
    return Settings(
        EMERGENCY_GUARDRAIL_ENABLED=False,
        EMERGENCY_GUARDRAIL_CONFIG_PATH="app/guardrail_config.json",
        EMERGENCY_GUARDRAIL_FAST_PATH=True,
    )


@pytest.fixture
def mock_retriever():
    ret = MagicMock()
    ret.search_specific.return_value = []
    return ret


# --- Section 1: Startup & Dependency Behavior ---

def test_clean_process_import_without_shim():
    """Verify backend.main can be imported in a completely fresh Python subprocess without conftest."""
    python_bin = sys.executable
    cmd = [python_bin, "-c", "import backend.main; print('IMPORT_OK')"]
    proc = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    assert proc.returncode == 0, f"Import failed with stderr: {proc.stderr}"
    assert "IMPORT_OK" in proc.stdout


def test_startup_without_pytest_shim():
    """Verify backend app instance initializes cleanly without langchain.docstore in sys.modules."""
    assert "langchain.docstore" not in sys.modules
    from backend.main import app
    assert app is not None
    assert app.title == "MediScanAI"


# --- Section 2: Multimodal Emergency Detection (Image-Only & Combined) ---

def test_image_only_chest_pain_emergency_fast_path(enabled_settings, mock_retriever):
    """Verify image-only request with OCR chest pain triggers emergency fast-path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["Acute crushing chest pain", "radiating to left arm"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        result = pipeline.run(user_text="", image_path="tests/mock_chest_pain.jpg")

    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-01-CARDIOVASCULAR-CHEST-PAIN"
    assert result["meta"]["ocr_status"] == "SUCCESS"
    llm_out = result["card"]["llm_output"]
    assert "112" in llm_out and "911" in llm_out
    assert MANDATORY_HEADER in llm_out
    # Retrieval and LLM must be avoided
    assert mock_retriever.search_specific.call_count == 0


def test_image_only_severe_respiratory_distress_fast_path(enabled_settings, mock_retriever):
    """Verify image-only request with severe dyspnea triggers emergency fast-path."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["Severe shortness of breath", "gasping for air and cyanosis"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        result = pipeline.run(user_text=None, image_path="tests/mock_dyspnea.jpg")

    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-02-RESPIRATORY-DISTRESS"
    assert mock_retriever.search_specific.call_count == 0


def test_combined_emergency_in_ocr_only(enabled_settings, mock_retriever):
    """Verify emergency signal present only in OCR text escalates even when user text is benign."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["Discharge note: sudden weakness on one side of face with slurred speech"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        result = pipeline.run(user_text="Can you summarize this discharge paper for me?", image_path="tests/mock_stroke.jpg")

    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-03-NEUROLOGICAL-STROKE"
    assert mock_retriever.search_specific.call_count == 0


def test_combined_emergency_in_user_text_only(enabled_settings, mock_retriever):
    """Verify emergency signal present in user text escalates when OCR contains routine label."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["Paracetamol 500mg tablets", "Batch 12345"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        result = pipeline.run(user_text="I took this pill but now have crushing chest pain and shortness of breath", image_path="tests/mock_pack.jpg")

    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-01-CARDIOVASCULAR-CHEST-PAIN"
    assert mock_retriever.search_specific.call_count == 0


def test_ocr_negated_symptoms_no_false_emergency(enabled_settings, mock_retriever):
    """Verify negated emergency symptom in OCR does not trigger false emergency."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["Clinical triage note:", "patient denies chest pain and without shortness of breath"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        with patch("app.core.generate_with_mode", return_value="Assessment: Viral URI."):
            result = pipeline.run(user_text="What does this report say?", image_path="tests/mock_negation.jpg")

    assert result["meta"]["fast_path"] is False
    assert result["meta"]["guardrail"]["is_emergency"] is False
    assert result["card"]["llm_output"] == "Assessment: Viral URI."


def test_ocr_historical_symptoms_no_false_emergency(enabled_settings, mock_retriever):
    """Verify historical mentions in OCR text do not trigger acute emergency triage."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["Past medical history: heart attack 10 years ago in 2014"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        with patch("app.core.generate_with_mode", return_value="Past cardiac history noted."):
            result = pipeline.run(user_text="Dietary advice for healthy aging", image_path="tests/mock_history.jpg")

    assert result["meta"]["fast_path"] is False
    assert result["meta"]["guardrail"]["is_emergency"] is False


def test_routine_medicine_packaging_no_false_emergency(enabled_settings, mock_retriever):
    """Verify routine medication packaging does not trigger emergency false alarms."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["LIPITOR 20mg", "Atorvastatin Calcium Tablets", "Pfizer Labs"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        with patch("app.core.generate_with_mode", return_value="Lipitor information."):
            result = pipeline.run(user_text="Dosage schedule?", image_path="tests/mock_lipitor.jpg")

    assert result["meta"]["fast_path"] is False
    assert result["meta"]["guardrail"]["is_emergency"] is False


# --- Section 3: OCR Failure & Unreadable Fallback Handling ---

def test_empty_ocr_result_image_only(enabled_settings, mock_retriever):
    """Verify image-only request with empty OCR returns safe guidance without hallucination."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": []}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        result = pipeline.run(user_text="", image_path="tests/blank_image.jpg")

    assert result["meta"]["fast_path"] is False
    assert result["meta"]["ocr_status"] == "EMPTY"
    llm_out = result["card"]["llm_output"]
    assert "No Text Detected in Image" in llm_out
    assert "112" in llm_out and "911" in llm_out
    assert MANDATORY_HEADER in llm_out


def test_ocr_exception_with_urgent_user_text(enabled_settings, mock_retriever):
    """Verify OCR failure cannot suppress an independent emergency signal in user text."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)

    with patch("app.core.extract_text_from_image", side_effect=RuntimeError("PaddleOCR runtime fault")):
        result = pipeline.run(user_text="Crushing chest pain and difficulty breathing", image_path="tests/corrupt.jpg")

    # Emergency fast-path MUST engage despite OCR failure
    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert result["meta"]["guardrail"]["fired_rule_id"] == "RULE-01-CARDIOVASCULAR-CHEST-PAIN"
    assert result["meta"]["ocr_status"] == "FAILED"
    assert result["meta"]["ocr_error_type"] == "RuntimeError"
    assert "112" in result["card"]["llm_output"]


def test_ocr_exception_image_only_safe_fallback(enabled_settings, mock_retriever):
    """Verify image-only request with OCR exception returns safe unreadable message."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)

    with patch("app.core.extract_text_from_image", side_effect=Exception("Corrupt image bytes")):
        result = pipeline.run(user_text=None, image_path="tests/corrupt.jpg")

    assert result["meta"]["fast_path"] is False
    assert result["meta"]["ocr_status"] == "FAILED"
    assert result["meta"]["ocr_error_type"] == "Exception"
    llm_out = result["card"]["llm_output"]
    assert "Image Could Not Be Interpreted" in llm_out
    assert "112" in llm_out and "911" in llm_out
    assert MANDATORY_HEADER in llm_out


def test_retrieval_failure_after_emergency_signal(enabled_settings):
    """Verify emergency fast-path succeeds even if retrieval database is completely broken."""
    broken_retriever = MagicMock()
    broken_retriever.search_specific.side_effect = ConnectionError("Neo4j / FAISS unavailable")
    pipeline = Pipeline(settings=enabled_settings, retriever=broken_retriever)

    ocr_mock_output = {"texts": ["Severe chest pain"]}
    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        result = pipeline.run(user_text="", image_path="tests/emergency.jpg")

    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True
    assert broken_retriever.search_specific.call_count == 0


def test_llm_unavailable_after_emergency_signal(enabled_settings, mock_retriever):
    """Verify emergency fast-path succeeds even if Ollama / local LLM is down."""
    pipeline = Pipeline(settings=enabled_settings, retriever=mock_retriever)
    ocr_mock_output = {"texts": ["Crushing chest pain radiating to jaw"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        with patch("app.core.generate_with_mode", side_effect=ConnectionRefusedError("Ollama down")):
            result = pipeline.run(user_text="", image_path="tests/emergency.jpg")

    assert result["meta"]["fast_path"] is True
    assert result["meta"]["guardrail"]["is_emergency"] is True


def test_feature_flag_disabled_multimodal_legacy_behavior(disabled_settings, mock_retriever):
    """Verify that when disabled, pipeline runs normal legacy generation even with image."""
    pipeline = Pipeline(settings=disabled_settings, retriever=mock_retriever)
    assert pipeline.guardrail is None
    ocr_mock_output = {"texts": ["Chest pain"]}

    with patch("app.core.extract_text_from_image", return_value=ocr_mock_output):
        with patch("app.core.generate_with_mode", return_value="Legacy routine response."):
            result = pipeline.run(user_text="Mild discomfort", image_path="tests/image.jpg")

    assert "guardrail" not in result["meta"]
    assert result["card"]["llm_output"] == "Legacy routine response."
    assert result["card"]["ocr_text"] == "Chest pain"
