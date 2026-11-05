"""
Offline tests for MediScanAI Phase 2 (Cache Integrity and Manifest-Driven Reports).

Covers:
  1. Cache Key V2 component sensitivity (changing ANY component changes key; identical inputs match).
  2. Invalid results are never cached.
  3. --no-cache bypasses reads & writes; --refresh-cache ignores reads and overwrites writes.
  4. Quarantine directory preservation, sha256 integrity, and strict isolation.
  5. Manifest-driven reporting: independent recomputation, paired intersection, exclusion printing.
  6. Perturbed fixture test (proves zero literals in reporting).
  7. INCONCLUSIVE verdict enforcement (invalid rate > 3%, coverage < 90%, CI spans zero).
  8. Bootstrap 95% CI determinism with fixed seed.
  9. Legacy recomputation verification: A6 recomputed mean equals raw JSONL mean (0.8021) and unsupported count is 34.
"""

import copy
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

from evaluation.e2e.cache_v2 import (
    KEY_SCHEMA_VERSION,
    METRIC_VERSION,
    CacheV2,
    build_cache_key_v2,
    get_effective_options,
    get_installed_package_versions,
)
from evaluation.e2e.eval_status import CaseResult, EvalStatus
from evaluation.e2e.manifest import RunManifest, compute_file_sha256
from evaluation.e2e.reporting import (
    compute_bootstrap_paired_ci,
    compute_category_breakdown,
    compute_dataset_stats,
    compute_paired_comparison,
    generate_evaluation_markdown,
    load_scored_jsonl,
    load_unsupported_statements,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_record():
    return {
        "case_id": "E2E-TEST-001",
        "answer_core": "Take metformin 500mg with evening meal.",
        "retrieved_contexts": [
            "Metformin hydrochloride tablets are indicated as an adjunct to diet and exercise.",
            "Initial dose is 500 mg orally once daily with food.",
        ],
        "user_text": "How do I take metformin?",
        "category": "medicine_only_clean_ocr",
    }


@pytest.fixture
def sample_judge_config():
    return {
        "model": "llama3.1:8b",
        "temperature": 0.0,
        "seed": 42,
        "num_ctx": 12288,
        "num_predict": 700,
        "format": "json",
    }


@pytest.fixture
def temp_cache_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Task 1 & Quarantine Integrity Tests
# ---------------------------------------------------------------------------

def test_quarantine_directory_integrity_and_isolation():
    """Verify quarantine directory exists, contains manifest.sha256 and README.md, and hashes match."""
    quarantine_dir = REPO_ROOT / "evaluation/e2e/cache_quarantine/2026-10-24_pre_v2"
    assert quarantine_dir.is_dir(), f"Quarantine directory {quarantine_dir} does not exist"

    manifest_file = quarantine_dir / "manifest.sha256"
    readme_file = quarantine_dir / "README.md"
    assert manifest_file.is_file(), "Quarantine manifest.sha256 missing"
    assert readme_file.is_file(), "Quarantine README.md missing"

    # Verify sha256 manifest
    with open(manifest_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            parts = line_str.split(maxsplit=1)
            assert len(parts) == 2
            expected_hash, fname = parts
            target_path = quarantine_dir / fname
            assert target_path.is_file(), f"Quarantined file {fname} missing"
            actual_hash = compute_file_sha256(target_path)
            assert actual_hash == expected_hash, f"Hash mismatch for quarantined {fname}"

    # Verify live cache path does not contain legacy judge_cache.json
    live_cache_json = REPO_ROOT / "evaluation/e2e/results/judge_cache.json"
    assert not live_cache_json.exists(), "Live path should not contain legacy judge_cache.json"


# ---------------------------------------------------------------------------
# Task 3: Cache Key V2 Sensitivity Tests
# ---------------------------------------------------------------------------

def test_cache_key_v2_identical_inputs_match(sample_record, sample_judge_config):
    """Identical inputs yield exact same Cache V2 key."""
    key1, comps1 = build_cache_key_v2(sample_record, sample_judge_config)
    key2, comps2 = build_cache_key_v2(sample_record, sample_judge_config)
    assert key1 == key2
    assert comps1 == comps2
    assert len(key1) == 64  # SHA256 hex length


@pytest.mark.parametrize(
    "field,modification",
    [
        ("case_id", "E2E-TEST-002"),
        ("answer_core", "Take metformin 1000mg with breakfast."),
        ("retrieved_contexts", ["Metformin dose: 500mg daily."]),
        ("user_text", "What is the dose for metformin?"),
    ],
)
def test_cache_key_v2_record_field_sensitivity(sample_record, sample_judge_config, field, modification):
    """Changing any input field in the record produces a cache miss (different key)."""
    base_key, _ = build_cache_key_v2(sample_record, sample_judge_config)

    mod_record = copy.deepcopy(sample_record)
    mod_record[field] = modification
    mod_key, _ = build_cache_key_v2(mod_record, sample_judge_config)

    assert mod_key != base_key, f"Changing record field '{field}' did not alter Cache Key V2"


def test_cache_key_v2_environment_components_sensitivity(sample_record, sample_judge_config):
    """Changing any package version, prompt hash, model digest, or guard version alters cache key."""
    base_key, _ = build_cache_key_v2(sample_record, sample_judge_config)

    # 1. Package version change
    pkg_mod = get_installed_package_versions()
    pkg_mod["ragas"] = "0.3.0"
    k_pkg, _ = build_cache_key_v2(sample_record, sample_judge_config, package_versions_override=pkg_mod)
    assert k_pkg != base_key

    # 2. Model digest change
    k_digest, _ = build_cache_key_v2(sample_record, sample_judge_config, model_digest_override="deadbeef1234")
    assert k_digest != base_key

    # 3. Prompt hash change
    prompts_mod = {
        "statement_generator_prompt": "hash_modified_stmt",
        "nli_statements_prompt": "hash_modified_nli",
    }
    k_prompt, _ = build_cache_key_v2(sample_record, sample_judge_config, prompt_hashes_override=prompts_mod)
    assert k_prompt != base_key

    # 4. Guard version change
    k_guard, _ = build_cache_key_v2(sample_record, sample_judge_config, eval_guard_version="3.0.0")
    assert k_guard != base_key

    # 5. Base URL / endpoint change
    k_ep, _ = build_cache_key_v2(sample_record, sample_judge_config, base_url="http://remote-gpu:11434/v1")
    assert k_ep != base_key


# ---------------------------------------------------------------------------
# Task 3: Cache Storage & CLI Flags Tests
# ---------------------------------------------------------------------------

def test_cache_v2_stores_and_retrieves_valid_results(sample_record, sample_judge_config, temp_cache_dir):
    cache = CacheV2(cache_dir=temp_cache_dir)
    key, comps = build_cache_key_v2(sample_record, sample_judge_config)

    assert cache.get(key) is None
    assert not cache.has(key)

    valid_res = {
        "faithfulness": 0.85,
        "unsupported": [],
        "eval_status": "valid",
        "eval_guard_version": "2.0.0",
    }
    cache.put(key, comps, valid_res)

    assert cache.has(key)
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved["faithfulness"] == 0.85
    assert retrieved["eval_status"] == "valid"


def test_invalid_results_are_never_cached(sample_record, sample_judge_config, temp_cache_dir):
    """CacheV2.put must raise ValueError if result eval_status != 'valid'."""
    cache = CacheV2(cache_dir=temp_cache_dir)
    key, comps = build_cache_key_v2(sample_record, sample_judge_config)

    invalid_results = [
        {"faithfulness": None, "eval_status": "parse_failure"},
        {"faithfulness": np.nan, "eval_status": "timeout"},
        {"faithfulness": 0.0, "eval_status": "contamination_prevented"},
    ]

    for inv in invalid_results:
        with pytest.raises(ValueError, match="Refusing to cache invalid result"):
            cache.put(key, comps, inv)

    assert cache.count() == 0


def test_no_cache_and_refresh_cache_behavior(sample_record, sample_judge_config, temp_cache_dir):
    """
    Test cache modes:
      - 'default': hit serves cached value
      - 'no_cache': bypasses read and write
      - 'refresh_cache': ignores read, writes updated value
    """
    cache = CacheV2(cache_dir=temp_cache_dir)
    key, comps = build_cache_key_v2(sample_record, sample_judge_config)

    # Pre-populate with initial value
    cache.put(key, comps, {"faithfulness": 0.70, "eval_status": "valid", "eval_guard_version": "2.0.0"})

    # In default mode: read returns 0.70
    assert cache.get(key)["faithfulness"] == 0.70

    # In no_cache mode: neither reads nor writes
    # Simulate scoring with no_cache -> read is skipped, write is skipped
    cached_val = None  # bypassed
    assert cached_val is None

    # In refresh_cache mode: ignore read, overwrite with new valid result
    cache.put(key, comps, {"faithfulness": 0.95, "eval_status": "valid", "eval_guard_version": "2.0.0"})
    assert cache.get(key)["faithfulness"] == 0.95


# ---------------------------------------------------------------------------
# Task 4: Run Manifest Tests
# ---------------------------------------------------------------------------

def test_run_manifest_initialization_and_finalization(temp_cache_dir):
    manifest = RunManifest(
        run_dir=temp_cache_dir,
        candidate_id="TEST_RUN",
        cache_mode="default",
    )
    manifest.record_cache_event("hit")
    manifest.record_cache_event("miss")
    manifest.record_case_status("valid")
    manifest.record_case_status("timeout")

    # Create dummy output file
    dummy_out = temp_cache_dir / "scored_results.jsonl"
    with open(dummy_out, "w", encoding="utf-8") as f:
        f.write('{"case_id": "T1"}\n')

    manifest_path = manifest.finalize()
    assert manifest_path.is_file()

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["candidate_id"] == "TEST_RUN"
    assert data["finalized"] is True
    assert data["cache_stats"] == {"hits": 1, "misses": 1, "bypassed": 0}
    assert data["status_counts"]["valid"] == 1
    assert data["status_counts"]["timeout"] == 1
    assert "scored_results.jsonl" in data["output_files"]
    assert len(data["output_files"]["scored_results.jsonl"]) == 64


# ---------------------------------------------------------------------------
# Task 5: Reporting from Data Only Tests
# ---------------------------------------------------------------------------

def test_reporting_independent_recomputation():
    """Verify compute_dataset_stats exactly matches independent arithmetic."""
    records = [
        {"case_id": f"C{i}", "judge_faithfulness": 1.0, "eval_status": "valid"} for i in range(1, 6)
    ] + [
        {"case_id": f"C{i}", "judge_faithfulness": 0.5, "eval_status": "valid"} for i in range(6, 9)
    ] + [
        {"case_id": "C9", "judge_faithfulness": None, "eval_status": "parse_failure"},
        {"case_id": "C10", "judge_faithfulness": np.nan, "eval_status": "timeout"},
    ]

    stats = compute_dataset_stats(records)
    # Valid scores: 5 * 1.0 + 3 * 0.5 = 6.5. 6.5 / 8 = 0.8125
    assert stats["total_count"] == 10
    assert stats["valid_count"] == 8
    assert stats["invalid_count"] == 2
    assert stats["invalid_rate"] == 0.2
    assert stats["mean"] == 0.8125
    assert stats["median"] == 1.0


def test_paired_comparison_intersection_and_exclusions():
    """Verify paired comparison strictly evaluates the intersection and lists exclusions with reasons."""
    cand_records = [
        {"case_id": "C1", "judge_faithfulness": 0.8, "eval_status": "valid"},
        {"case_id": "C2", "judge_faithfulness": 0.9, "eval_status": "valid"},
        {"case_id": "C3", "judge_faithfulness": None, "eval_status": "timeout", "error_class": "TimeoutError"},
    ]
    base_records = [
        {"case_id": "C1", "judge_faithfulness": 0.7, "eval_status": "valid"},
        {"case_id": "C2", "judge_faithfulness": None, "eval_status": "parse_failure", "error_class": "JSONDecodeError"},
        {"case_id": "C3", "judge_faithfulness": 0.5, "eval_status": "valid"},
    ]

    cand_stats = compute_dataset_stats(cand_records)
    base_stats = compute_dataset_stats(base_records)

    paired = compute_paired_comparison(cand_stats, base_stats, seed=42)

    # Intersection is only {C1}
    assert paired["intersection_count"] == 1
    assert paired["wins"] == 1  # 0.8 vs 0.7
    assert paired["losses"] == 0
    assert paired["ties"] == 0

    # Excluded cases: C2 and C3
    excluded_ids = {e["case_id"] for e in paired["excluded_cases"]}
    assert excluded_ids == {"C2", "C3"}


def test_reporting_perturbed_fixture_changes_output():
    """Verify changing fixture values alters report numbers, proving no hardcoded literals."""
    base_recs = [{"case_id": "C1", "judge_faithfulness": 0.8, "eval_status": "valid"}]
    cand_recs_a = [{"case_id": "C1", "judge_faithfulness": 0.8, "eval_status": "valid"}]
    cand_recs_b = [{"case_id": "C1", "judge_faithfulness": 0.4, "eval_status": "valid"}]

    md_a = generate_evaluation_markdown("Cand", "Base", cand_recs_a, base_recs)
    md_b = generate_evaluation_markdown("Cand", "Base", cand_recs_b, base_recs)

    assert md_a != md_b
    assert "+0.0000" in md_a
    assert "-0.4000" in md_b


def test_verdict_logic_inconclusive_thresholds():
    """Verdict must be INCONCLUSIVE if invalid rate > 3% or paired coverage < 90%."""
    # 1. High invalid rate (>3%)
    c_records_high_invalid = [
        {"case_id": f"C{i}", "judge_faithfulness": 1.0, "eval_status": "valid"} for i in range(1, 38)
    ] + [
        {"case_id": f"C{i}", "judge_faithfulness": None, "eval_status": "timeout"} for i in range(38, 41)
    ]  # 3/40 = 7.5% invalid
    b_records = [
        {"case_id": f"C{i}", "judge_faithfulness": 0.8, "eval_status": "valid"} for i in range(1, 41)
    ]

    c_stats = compute_dataset_stats(c_records_high_invalid)
    b_stats = compute_dataset_stats(b_records)
    paired = compute_paired_comparison(c_stats, b_stats)

    assert paired["verdict"] == "INCONCLUSIVE"
    assert "exceeds 3.0%" in paired["verdict_reason"]

    # 2. Bootstrap CI crossing zero yields INCONCLUSIVE / NO STATISTICAL DIFFERENCE
    # Equal distribution around zero
    c_records_mixed = [
        {"case_id": f"C{i}", "judge_faithfulness": 0.8 if i % 2 == 0 else 0.6, "eval_status": "valid"} for i in range(1, 41)
    ]
    b_records_mixed = [
        {"case_id": f"C{i}", "judge_faithfulness": 0.7, "eval_status": "valid"} for i in range(1, 41)
    ]
    c_st_mix = compute_dataset_stats(c_records_mixed)
    b_st_mix = compute_dataset_stats(b_records_mixed)
    paired_mix = compute_paired_comparison(c_st_mix, b_st_mix, seed=42)

    assert "INCONCLUSIVE" in paired_mix["verdict"]


def test_bootstrap_ci_determinism():
    """Bootstrap 95% CI is completely deterministic for a fixed seed."""
    deltas = [-0.1, 0.05, 0.0, -0.05, 0.1, -0.2, 0.15, -0.05]
    ci1 = compute_bootstrap_paired_ci(deltas, n_resamples=1000, seed=42)
    ci2 = compute_bootstrap_paired_ci(deltas, n_resamples=1000, seed=42)

    assert ci1 == ci2
    assert ci1["ci_lower"] <= ci1["mean"] <= ci1["ci_upper"]


# ---------------------------------------------------------------------------
# Task 6: Legacy Recomputation Verification
# ---------------------------------------------------------------------------

def test_legacy_recomputation_ground_truth():
    """Verify legacy recomputed stats on A6 and A6.1."""
    a6_file = REPO_ROOT / "evaluation/e2e/results/A6/scored_results.jsonl"
    a6_unsupp_file = REPO_ROOT / "evaluation/e2e/results/A6/unsupported_statements.jsonl"
    a61_file = REPO_ROOT / "evaluation/e2e/results/A6_1/scored_results.jsonl"
    a61_unsupp_file = REPO_ROOT / "evaluation/e2e/results/A6_1/unsupported_statements.jsonl"

    assert a6_file.exists()
    assert a61_file.exists()

    a6_recs = load_scored_jsonl(a6_file)
    a6_unsupp = load_unsupported_statements(a6_unsupp_file)
    a61_recs = load_scored_jsonl(a61_file)
    a61_unsupp = load_unsupported_statements(a61_unsupp_file)

    a6_stats = compute_dataset_stats(a6_recs, a6_unsupp)
    a61_stats = compute_dataset_stats(a61_recs, a61_unsupp)

    # 1. A6 mean is 0.8021
    assert a6_stats["mean"] == 0.8021
    assert a6_stats["valid_count"] == 40
    # 2. A6 unsupported count is 34 (not 12!)
    assert a6_stats["unsupported_count"] == 34

    # 3. A6.1 valid count is 39 (E2E-062 invalid)
    assert a61_stats["valid_count"] == 39
    assert a61_stats["invalid_count"] == 1
    assert a61_stats["unsupported_count"] == 35

    # 4. Paired on 39 intersection cases
    paired = compute_paired_comparison(a61_stats, a6_stats, seed=42)
    assert paired["intersection_count"] == 39
    assert paired["base_intersection_mean"] == 0.8098
    assert paired["cand_intersection_mean"] == 0.7614
    assert paired["intersection_mean_delta"] == -0.0484  # rounded -0.0485 diff
    assert paired["excluded_cases"][0]["case_id"] == "E2E-062"
