"""
Tests for Judge Transport Configurations and Fingerprinting (Phase 3 Prerequisite).
"""

import pytest
from evaluation.e2e.judge_factory import (
    get_judge_fingerprint,
    create_judge_llm,
)


def test_judge_fingerprint_distinctness():
    """openai_v1 and native_ollama produce distinct fingerprints and hashes."""
    fp_v1 = get_judge_fingerprint("openai_v1")
    fp_native = get_judge_fingerprint("native_ollama")

    assert fp_v1["endpoint_type"] == "openai_v1"
    assert fp_native["endpoint_type"] == "native_ollama"

    assert fp_v1["fingerprint_sha256"] != fp_native["fingerprint_sha256"]

    # Verify effective options match empirical probe
    assert fp_v1["effective_options"]["num_ctx"] == 8192
    assert fp_v1["effective_options"]["seed"] is None
    assert fp_v1["effective_options"]["format"] is None

    assert fp_native["effective_options"]["num_ctx"] == 12288
    assert fp_native["effective_options"]["seed"] == 42
    assert fp_native["effective_options"]["format"] == "json"


def test_create_judge_llm_factory():
    """Factory creates instances for both transport modes."""
    llm_v1, fp_v1 = create_judge_llm("openai_v1")
    assert llm_v1 is not None
    assert fp_v1["endpoint_type"] == "openai_v1"

    llm_native, fp_native = create_judge_llm("native_ollama")
    assert llm_native is not None
    assert fp_native["endpoint_type"] == "native_ollama"
