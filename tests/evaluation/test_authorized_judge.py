"""
Tests for Authorized Judge Model Enforcement (Phase 3B).
Verifies that only 'llama3.1:8b' can be initialized as an authoritative judge,
and that any unauthorized model is strictly rejected with UnauthorizedJudgeError.
"""

import pytest
from evaluation.e2e.judge_factory import (
    AUTHORIZED_JUDGE_MODEL,
    UnauthorizedJudgeError,
    create_judge_llm,
    get_judge_fingerprint,
)


def test_authorized_judge_model_constant():
    assert AUTHORIZED_JUDGE_MODEL == "llama3.1:8b"


def test_authorized_judge_allowed_default():
    # llama3.1:8b should succeed without error
    cfg = {"model": "llama3.1:8b", "temperature": 0.0, "seed": 42, "num_ctx": 12288, "format": "json"}
    fp_v1 = get_judge_fingerprint("openai_v1", cfg)
    assert fp_v1["model_name"] == "llama3.1:8b"

    fp_native = get_judge_fingerprint("native_ollama", cfg)
    assert fp_native["model_name"] == "llama3.1:8b"


@pytest.mark.parametrize(
    "unauthorized_model",
    [
        "qwen2.5:3b",
        "mistral:latest",
        "llama3:8b",
        "gpt-4o",
        "claude-3-5-sonnet",
        "mediscan-custom:latest",
    ],
)
def test_unauthorized_judge_rejected_in_fingerprint(unauthorized_model):
    cfg = {"model": unauthorized_model, "temperature": 0.0, "seed": 42, "num_ctx": 12288, "format": "json"}
    with pytest.raises(UnauthorizedJudgeError, match="unauthorized"):
        get_judge_fingerprint("openai_v1", cfg)

    with pytest.raises(UnauthorizedJudgeError, match="unauthorized"):
        get_judge_fingerprint("native_ollama", cfg)


@pytest.mark.parametrize(
    "unauthorized_model",
    [
        "qwen2.5:3b",
        "mistral:latest",
    ],
)
def test_unauthorized_judge_rejected_in_create_llm(unauthorized_model):
    cfg = {"model": unauthorized_model, "temperature": 0.0, "seed": 42, "num_ctx": 12288, "format": "json"}
    with pytest.raises(UnauthorizedJudgeError, match="unauthorized"):
        create_judge_llm(endpoint_type="openai_v1", judge_config=cfg)

    with pytest.raises(UnauthorizedJudgeError, match="unauthorized"):
        create_judge_llm(endpoint_type="native_ollama", judge_config=cfg)


def test_explicit_diagnostic_override_flag():
    # If explicitly flagged as non-authoritative diagnostic, it should be allowed to run
    cfg = {"model": "qwen2.5:3b", "temperature": 0.0, "seed": 42, "num_ctx": 12288, "format": "json"}
    fp = get_judge_fingerprint("openai_v1", cfg, allow_non_authoritative=True)
    assert fp["model_name"] == "qwen2.5:3b"
