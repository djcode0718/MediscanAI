"""
Unit tests for Step 2: Settings Flags & Pipeline Threading.
Verifies defaults preserve legacy behaviour, validation constraints,
and threading through Pipeline.settings -> GenerationParams without module globals.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.core.config import Settings
from app.core import Pipeline
from app.llm import GenerationParams


def test_settings_hygiene_defaults():
    s = Settings(JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!")
    assert s.EVIDENCE_FORMAT == "legacy"
    assert s.PROMPT_VERSION == "legacy"
    assert s.GEN_TEMPERATURE is None
    assert s.GEN_SEED is None
    assert s.OLLAMA_NUM_CTX is None
    assert s.OLLAMA_NUM_PREDICT is None
    assert s.EVIDENCE_MAX_ITEMS_PER_CHANNEL == 3
    assert s.EVIDENCE_DRUG_FIELDS == "brand_name,generic_name,active_ingredients,indications"
    assert s.EVIDENCE_FIELD_CAPS["indications"] == 700
    assert s.EVIDENCE_FIELD_CAPS["warnings"] == 300
    assert s.EVIDENCE_FIELD_CAPS["dosage"] == 300
    assert s.EVIDENCE_FIELD_CAPS["adverse_reactions"] == 300
    assert s.EVIDENCE_FIELD_CAPS["symptoms"] == 12


def test_settings_validation_constraints():
    with pytest.raises(ValueError, match="EVIDENCE_FORMAT"):
        Settings(
            JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
            EVIDENCE_FORMAT="invalid_format"
        )

    with pytest.raises(ValueError, match="PROMPT_VERSION"):
        Settings(
            JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
            PROMPT_VERSION="v99"
        )

    s_v4 = Settings(
        JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
        PROMPT_VERSION="v4"
    )
    assert s_v4.PROMPT_VERSION == "v4"


def test_settings_field_caps_string_parser():
    s = Settings(
        JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
        EVIDENCE_FIELD_CAPS="indications=800,warnings=400,dosage=250"
    )
    assert s.EVIDENCE_FIELD_CAPS["indications"] == 800
    assert s.EVIDENCE_FIELD_CAPS["warnings"] == 400
    assert s.EVIDENCE_FIELD_CAPS["dosage"] == 250


@patch("app.core.generate_with_mode_meta")
def test_pipeline_threads_settings_into_generation_params(mock_gen):
    mock_gen.return_value = ("Answer", {"model": "llama3.1:8b", "eval_count": 20})

    s = Settings(
        JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
        GEN_TEMPERATURE=0.0,
        GEN_SEED=42,
        OLLAMA_NUM_CTX=8192,
        OLLAMA_NUM_PREDICT=700,
    )
    pipeline = Pipeline(settings=s)

    mock_retriever = MagicMock()
    mock_retriever.search_specific.return_value = []
    pipeline.retriever = mock_retriever

    res = pipeline.run("test query", return_trace=True)
    trace = res["trace"]
    eff_settings = trace["effective_settings"]

    assert eff_settings["params"]["temperature"] == 0.0
    assert eff_settings["params"]["seed"] == 42
    assert eff_settings["params"]["num_ctx"] == 8192
    assert eff_settings["params"]["num_predict"] == 700


@patch("app.core.generate_with_mode_meta")
def test_pipeline_explicit_params_override_settings(mock_gen):
    mock_gen.return_value = ("Answer", {"model": "llama3.1:8b", "eval_count": 20})

    s = Settings(
        JWT_SECRET_KEY="test_secret_for_unit_tests_only_32_bytes_long!!",
        GEN_TEMPERATURE=0.7,
        GEN_SEED=99,
    )
    pipeline = Pipeline(settings=s)

    mock_retriever = MagicMock()
    mock_retriever.search_specific.return_value = []
    pipeline.retriever = mock_retriever

    explicit = GenerationParams(temperature=0.0, seed=42)
    res = pipeline.run("test query", gen_params=explicit, return_trace=True)
    trace = res["trace"]
    eff_settings = trace["effective_settings"]

    assert eff_settings["params"]["temperature"] == 0.0
    assert eff_settings["params"]["seed"] == 42
