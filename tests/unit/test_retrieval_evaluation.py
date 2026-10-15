"""
Unit tests for MediScanAI Phase B: Retrieval Evaluation & Evidence Pooling Harness.
Validates metric mathematics, threshold mapping, missing gold handling, deduplication,
cross-channel rank preservation, latency telemetry, safe review merging, and failure resilience.

Execution constraints:
- Must run without live Neo4j, network calls, or LLM calls.
- Off-limits directory entity_resolution/ is never accessed.
"""

import json
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from evaluation.retrieval.schemas import RetrievedItem, PooledEvidence, CaseEvaluationResult, EvaluationSummary
from evaluation.retrieval.metrics import (
    is_relevant,
    deduplicate_ordered,
    compute_recall_at_k,
    compute_precision_at_k,
    compute_reciprocal_rank,
    compute_graph_added_coverage,
    compute_latency_percentiles,
)
from evaluation.retrieval.pool_evidence import (
    normalize_disease_chunk_id,
    parse_baseline_retrieval_tuple,
    pool_evidence_for_case,
    export_pooled_evidence_to_csv,
)


class TestMetricsCalculation:
    """Tests deterministic retrieval metrics with hand-crafted fixtures."""

    def test_relevance_threshold_mapping(self):
        # Primary threshold: grade >= 2
        assert is_relevant(3, threshold=2) is True
        assert is_relevant(2, threshold=2) is True
        assert is_relevant(1, threshold=2) is False
        assert is_relevant(0, threshold=2) is False
        assert is_relevant(None, threshold=2) is False

        # Strict threshold: grade == 3
        assert is_relevant(3, threshold=3) is True
        assert is_relevant(2, threshold=3) is False

    def test_recall_at_k(self):
        gold = {"drug_10", "drug_20", "drug_30"}
        retrieved = ["drug_10", "drug_99", "drug_20", "drug_88", "drug_77"]

        # Top 1: 1 hit out of 3 = 1/3
        assert pytest.approx(compute_recall_at_k(retrieved, gold, k=1), 0.001) == 1.0 / 3.0
        # Top 3: 2 hits out of 3 = 2/3
        assert pytest.approx(compute_recall_at_k(retrieved, gold, k=3), 0.001) == 2.0 / 3.0
        # Top 5: 2 hits out of 3 = 2/3
        assert pytest.approx(compute_recall_at_k(retrieved, gold, k=5), 0.001) == 2.0 / 3.0

    def test_recall_at_k_ineligible_when_gold_empty(self):
        # Unanswerable query with 0 relevant gold items
        retrieved = ["drug_10", "drug_20"]
        assert compute_recall_at_k(retrieved, set(), k=5) is None

    def test_precision_at_k(self):
        gold = {"drug_10", "drug_20"}
        retrieved = ["drug_10", "drug_99", "drug_20"]

        # Top 1: 1 hit / 1 = 1.0
        assert compute_precision_at_k(retrieved, gold, k=1) == 1.0
        # Top 3: 2 hits / 3 = 0.6667
        assert pytest.approx(compute_precision_at_k(retrieved, gold, k=3), 0.001) == 2.0 / 3.0
        # Top 5 with fewer than 5 results: 2 hits / 5 = 0.4 (denominator remains K)
        assert compute_precision_at_k(retrieved, gold, k=5) == 2.0 / 5.0

    def test_reciprocal_rank(self):
        gold = {"drug_20"}
        retrieved_rank1 = ["drug_20", "drug_10"]
        retrieved_rank2 = ["drug_99", "drug_20", "drug_10"]
        retrieved_miss = ["drug_1", "drug_2"]

        assert compute_reciprocal_rank(retrieved_rank1, gold, k=5) == 1.0
        assert compute_reciprocal_rank(retrieved_rank2, gold, k=5) == 0.5
        assert compute_reciprocal_rank(retrieved_miss, gold, k=5) == 0.0
        # Ineligible when no gold relevant
        assert compute_reciprocal_rank(retrieved_rank1, set(), k=5) is None

    def test_graph_added_coverage_calculation(self):
        gold = {"drug_1", "drug_2", "drug_3", "drug_4"}
        base = ["drug_1", "drug_2"]
        graph = ["drug_2", "drug_3", "drug_unresolved", "drug_99"]
        unresolved = {"drug_unresolved"}

        cov = compute_graph_added_coverage(
            baseline_ids=base,
            graph_ids=graph,
            gold_relevant_ids=gold,
            unresolved_graph_ids=unresolved,
        )

        assert cov["baseline_count"] == 2
        assert cov["graph_count"] == 3  # drug_2, drug_3, drug_99 (unresolved excluded)
        assert cov["unresolved_graph_count"] == 1
        assert cov["overlap_count"] == 1  # drug_2
        assert cov["graph_only_count"] == 2  # drug_3, drug_99
        assert cov["relevant_graph_added_count"] == 1  # drug_3 is in gold
        # Coverage delta: 1 / 4 = 0.25
        assert pytest.approx(cov["graph_added_coverage_delta"], 0.001) == 0.25
        # Redundancy rate: 1 overlap / 3 valid graph items = 1/3
        assert pytest.approx(cov["graph_redundancy_rate"], 0.001) == 1.0 / 3.0


class TestTelemetryAndLatency:
    """Tests latency percentiles and small sample safety."""

    def test_empty_latency_handling(self):
        stats = compute_latency_percentiles([])
        assert stats["sample_count"] == 0
        assert stats["stability_note"] == "zero_samples"
        assert stats["p50_ms"] is None

    def test_small_sample_flagging(self):
        latencies = [10, 20, 30, 40, 50]  # count = 5 < 20
        stats = compute_latency_percentiles(latencies)
        assert stats["sample_count"] == 5
        assert stats["min_ms"] == 10
        assert stats["max_ms"] == 50
        assert stats["p50_ms"] == 30
        assert stats["stability_note"] == "unstable_small_sample"

    def test_large_sample_percentiles(self):
        latencies = list(range(1, 101))  # 1 to 100 ms (count = 100 >= 20)
        stats = compute_latency_percentiles(latencies)
        assert stats["sample_count"] == 100
        assert stats["p50_ms"] == 50
        assert stats["p95_ms"] == 95
        assert stats["p99_ms"] == 99
        assert stats["stability_note"] == "stable_sample"


class TestEvidencePoolingAndDeduplication:
    """Tests cross-channel deduplication, rank preservation, and review merge."""

    def test_normalize_chunk_id(self):
        assert normalize_disease_chunk_id("chunk_1") == "disease_chunk_1"
        assert normalize_disease_chunk_id("disease_chunk_501") == "disease_chunk_501"
        assert normalize_disease_chunk_id("chunk_2501") == "disease_chunk_2501"

    def test_cross_channel_pooling_and_independent_ranks(self):
        b1 = RetrievedItem(evidence_id="drug_10", evidence_type="drug_product", source_record_id=10, channel="baseline", rank=1)
        b2 = RetrievedItem(evidence_id="drug_20", evidence_type="drug_product", source_record_id=20, channel="baseline", rank=2)

        # Graph returns drug_20 (rank 1) and drug_30 (rank 2)
        g1 = RetrievedItem(evidence_id="drug_20", evidence_type="drug_product", source_record_id=20, channel="graph", rank=1)
        g2 = RetrievedItem(evidence_id="drug_30", evidence_type="drug_product", source_record_id=30, channel="graph", rank=2)

        pooled, stats = pool_evidence_for_case(
            case_id="MED-BENCH-001",
            query="Lipitor",
            query_category="drug_brand_lookup",
            baseline_items=[b1, b2],
            graph_items=[g1, g2],
            existing_reviews={},
        )

        assert stats["baseline_count"] == 2
        assert stats["graph_count"] == 2
        assert stats["pooled_count"] == 3  # drug_10, drug_20, drug_30
        assert stats["overlap_count"] == 1  # drug_20
        assert stats["graph_only_count"] == 1  # drug_30

        # Verify rank preservation
        item_20 = next(p for p in pooled if p.evidence_id == "drug_20")
        assert item_20.retrieval_channels == ["baseline", "graph"]
        assert item_20.baseline_rank == 2
        assert item_20.graph_rank == 1

        item_10 = next(p for p in pooled if p.evidence_id == "drug_10")
        assert item_10.retrieval_channels == ["baseline"]
        assert item_10.baseline_rank == 1
        assert item_10.graph_rank is None

        item_30 = next(p for p in pooled if p.evidence_id == "drug_30")
        assert item_30.retrieval_channels == ["graph"]
        assert item_30.baseline_rank is None
        assert item_30.graph_rank == 2

    def test_safe_merge_with_prior_review_data(self):
        b1 = RetrievedItem(evidence_id="drug_53548", evidence_type="drug_product", source_record_id=53548, channel="baseline", rank=1)
        prior_reviews = {
            ("MED-BENCH-001", "drug_53548"): {
                "proposed_grade": "3",
                "reviewed_grade": "3",
                "reviewer_id": "ai_annotator_preliminary",
                "reviewed_at": "2026-10-14T09:48:00Z",
                "judgment_rationale": "Exact brand match.",
                "adjudication_notes": "Preliminary annotation confirmed.",
                "judgment_status": "preliminary_reviewed",
            }
        }

        pooled, stats = pool_evidence_for_case(
            case_id="MED-BENCH-001",
            query="Lipitor",
            query_category="drug_brand_lookup",
            baseline_items=[b1],
            graph_items=[],
            existing_reviews=prior_reviews,
        )

        assert len(pooled) == 1
        p = pooled[0]
        assert p.reviewed_grade == 3
        assert p.reviewer_id == "ai_annotator_preliminary"
        assert p.judgment_rationale == "Exact brand match."

    def test_newly_discovered_item_remains_unreviewed(self):
        b_new = RetrievedItem(evidence_id="drug_9999", evidence_type="drug_product", source_record_id=9999, channel="baseline", rank=1)
        pooled, stats = pool_evidence_for_case(
            case_id="MED-BENCH-001",
            query="Lipitor",
            query_category="drug_brand_lookup",
            baseline_items=[b_new],
            graph_items=[],
            existing_reviews={},
        )
        assert len(pooled) == 1
        assert pooled[0].reviewed_grade is None
        assert pooled[0].judgment_status == "unreviewed_pooled_candidate"

    def test_csv_export_format(self, tmp_path):
        item = PooledEvidence(
            case_id="MED-BENCH-001",
            query="Lipitor",
            query_category="drug_brand_lookup",
            evidence_id="drug_53548",
            evidence_type="drug_product",
            source_record_id=53548,
            retrieval_channels=["baseline", "graph"],
            baseline_rank=1,
            graph_rank=2,
            source_excerpt="Brand: Lipitor",
            proposed_grade=3,
            reviewed_grade=3,
            judgment_status="preliminary_reviewed",
            reviewer_id="ai_annotator_preliminary",
            reviewed_at="2026-10-14T09:48:00Z",
            judgment_rationale="Exact match",
            adjudication_notes="Confirmed",
        )
        out_csv = tmp_path / "pooled_test.csv"
        export_pooled_evidence_to_csv([item], out_csv)

        assert out_csv.exists()
        with open(out_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            row = next(reader)

        assert len(header) == 17
        assert row[0] == "MED-BENCH-001"
        assert row[3] == "drug_53548"
        assert row[6] == "baseline;graph"
        assert row[7] == "1"
        assert row[8] == "2"


class TestEvaluationRunnerContracts:
    """Verifies runner contracts, empty gold handling, and Metformin case presence."""

    def test_empty_gold_produces_not_evaluable_status(self, tmp_path):
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        # Initialize runner with empty gold
        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=Path("evaluation/benchmark"),
            output_dir=tmp_path / "empty_gold_run",
        )
        # Verify that gold_judgments is indeed empty
        assert len(runner.gold_judgments) == 0

        # Create sample case
        sample_case = {
            "case_id": "MED-BENCH-001",
            "query": "Lipitor",
            "query_category": "drug_brand_lookup",
            "expected_evidence_types": ["drug_product"],
        }
        res = runner.evaluate_case(sample_case)

        # Must report not_evaluable_no_reviewed_gold_labels, not 0.0 scores
        assert res.metrics["eligibility"] == "not_evaluable_no_reviewed_gold_labels"
        assert res.metrics["recall_at_k"] is None
        assert res.metrics["precision_at_k"] is None
        assert res.metrics["baseline_mrr"] is None
        assert res.metrics["graph_mrr"] is None
        assert res.metrics["pooled_mrr"] is None

    def test_metformin_case_present_in_benchmark_queries(self):
        from evaluation.retrieval.run_retrieval_evaluation import load_candidate_queries

        queries = load_candidate_queries(Path("evaluation/benchmark"))
        metformin_case = next((q for q in queries if q["case_id"] == "MED-BENCH-036"), None)
        assert metformin_case is not None
        assert metformin_case["query"] == "Metformin"
        assert metformin_case["query_category"] == "ambiguous_queries"

    def test_lisinopril_case_contains_both_candidates(self):
        from evaluation.retrieval.run_retrieval_evaluation import load_candidate_queries

        queries = load_candidate_queries(Path("evaluation/benchmark"))
        lisinopril_case = next((q for q in queries if q["case_id"] == "MED-BENCH-015"), None)
        assert lisinopril_case is not None
        assert "drug_923" in lisinopril_case["candidate_gold_evidence_ids"]
        assert "drug_473" in lisinopril_case["candidate_gold_evidence_ids"]

    def test_baseline_mrr_independent_of_graph_candidates(self, tmp_path):
        """Proves that graph-only candidates do not distort baseline MRR and no synthetic MRR is emitted."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="both",
            top_k=5,
            benchmark_dir=Path("evaluation/benchmark"),
            output_dir=tmp_path / "mrr_test",
        )
        # Mock reviewed gold judgments: drug_20 is relevant
        runner.gold_judgments = {
            "TEST-001": {
                "has_reviewed_judgments": True,
                "relevant_ids": {"drug_20"},
                "all_reviewed_ids": {"drug_20", "drug_10"},
            }
        }

        # Mock baseline and graph execution
        runner.execute_baseline = lambda query, types: (
            [
                RetrievedItem(evidence_id="drug_10", evidence_type="drug_product", source_record_id=10, channel="baseline", rank=1),
                RetrievedItem(evidence_id="drug_20", evidence_type="drug_product", source_record_id=20, channel="baseline", rank=2),
            ],
            10,
            None,
        )
        # Graph returns 3 graph-only candidates
        runner.execute_graph = lambda query, types, cat: (
            [
                RetrievedItem(evidence_id="drug_30", evidence_type="drug_product", source_record_id=30, channel="graph", rank=1),
                RetrievedItem(evidence_id="drug_40", evidence_type="drug_product", source_record_id=40, channel="graph", rank=2),
                RetrievedItem(evidence_id="drug_50", evidence_type="drug_product", source_record_id=50, channel="graph", rank=3),
            ],
            5,
            None,
        )

        res = runner.evaluate_case({
            "case_id": "TEST-001",
            "query": "Test Drug",
            "query_category": "drug_brand_lookup",
            "expected_evidence_types": ["drug_product"],
        })

        # Baseline MRR should be exactly 1/2 = 0.5 (drug_20 at baseline rank 2)
        assert res.metrics["baseline_mrr"] == 0.5
        # Prohibited: synthetic graph MRR or pooled MRR must be None
        assert res.metrics["graph_mrr"] is None
        assert res.metrics["pooled_mrr"] is None
        # Graph candidates must be preserved as separate measurements
        assert res.graph_count == 3
        assert res.graph_only_count == 3
        assert res.overlap_count == 0

    def test_four_eligibility_states(self, tmp_path):
        """Verifies the 4 distinct ground-truth eligibility states."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=Path("evaluation/benchmark"),
            output_dir=tmp_path / "elig_test",
        )
        runner.execute_baseline = lambda query, types: (
            [RetrievedItem(evidence_id="drug_10", evidence_type="drug_product", source_record_id=10, channel="baseline", rank=1)],
            10,
            None,
        )

        # State 1: not_evaluable_no_reviewed_gold_labels
        runner.gold_judgments = {}
        r1 = runner.evaluate_case({"case_id": "C-1", "query": "Q1", "query_category": "cat1"})
        assert r1.metrics["eligibility"] == "not_evaluable_no_reviewed_gold_labels"

        # State 2: eligible_reviewed_gold (has relevant gold evidence)
        runner.gold_judgments = {
            "C-2": {"has_reviewed_judgments": True, "relevant_ids": {"drug_10"}, "all_reviewed_ids": {"drug_10"}}
        }
        r2 = runner.evaluate_case({"case_id": "C-2", "query": "Q2", "query_category": "cat1"})
        assert r2.metrics["eligibility"] == "eligible_reviewed_gold"
        assert r2.metrics["recall_at_k"] == 1.0
        assert r2.metrics["baseline_mrr"] == 1.0

        # State 3: eligible_negative_control (reviewed with 0 relevant evidence AND designated negative control)
        runner.gold_judgments = {
            "C-3": {"has_reviewed_judgments": True, "relevant_ids": set(), "all_reviewed_ids": {"drug_99"}}
        }
        r3 = runner.evaluate_case({
            "case_id": "C-3",
            "query": "unanswerable query",
            "query_category": "insufficient_evidence_unanswerable",
            "expected_evidence_types": ["none"],
        })
        assert r3.metrics["eligibility"] == "eligible_negative_control"
        assert r3.metrics["recall_at_k"] is None  # Ineligible for recall
        assert r3.metrics["baseline_mrr"] is None  # Ineligible for MRR
        assert r3.metrics["false_positive_count_at_k"] == 1
        assert r3.metrics["rejection_accuracy"] == 0.0  # Retrieved 1 item -> did not reject

        # State 4: excluded_no_relevant_gold_evidence (reviewed with 0 relevant evidence but not a negative control)
        runner.gold_judgments = {
            "C-4": {"has_reviewed_judgments": True, "relevant_ids": set(), "all_reviewed_ids": {"drug_99"}}
        }
        r4 = runner.evaluate_case({
            "case_id": "C-4",
            "query": "drug query",
            "query_category": "drug_brand_lookup",
        })
        assert r4.metrics["eligibility"] == "excluded_no_relevant_gold_evidence"
        assert r4.metrics["recall_at_k"] is None
        assert r4.metrics["baseline_mrr"] is None

    def test_git_metadata_and_benchmark_version(self):
        from evaluation.retrieval.run_retrieval_evaluation import get_git_metadata, get_benchmark_version

        git_meta = get_git_metadata()
        assert "git_branch" in git_meta
        assert "git_commit" in git_meta
        assert "is_dirty" in git_meta
        assert git_meta["is_dirty"] in (True, False, None)

        # Benchmark version from actual benchmark directory
        ver = get_benchmark_version(Path("evaluation/benchmark"))
        assert ver == "1.0.0"

    def test_git_metadata_fallbacks_and_dirty_detection(self):
        """
        Validates get_git_metadata() behavior across Phase B.2.3 tri-state semantics:
        1. Successful Git commands with a clean working tree -> is_dirty is False.
        2. Successful Git commands with tracked modifications -> is_dirty is True.
        3. Successful Git commands with untracked files -> is_dirty is True.
        4. Git executable unavailable and no usable .git metadata -> is_dirty is None.
        5. Git executable unavailable but filesystem metadata allows branch/commit recovery -> is_dirty is None.
        6. Git status command fails while branch/commit are available -> is_dirty is None.
        """
        from evaluation.retrieval.run_retrieval_evaluation import get_git_metadata

        # Helper mock for missing git filesystem
        def fake_no_git_path(p):
            m = MagicMock()
            m.exists.return_value = False
            return m

        # 1. Successful Git commands with a clean working tree -> is_dirty is False
        with patch("subprocess.run") as mock_sub:
            def side_effect_clean(cmd, *args, **kwargs):
                if "--abbrev-ref" in cmd:
                    return MagicMock(returncode=0, stdout="main\n")
                elif "rev-parse" in cmd:
                    return MagicMock(returncode=0, stdout="c0ffee\n")
                elif "status" in cmd:
                    return MagicMock(returncode=0, stdout="")
                return MagicMock(returncode=1, stdout="")

            mock_sub.side_effect = side_effect_clean
            meta = get_git_metadata()
            assert meta["git_branch"] == "main"
            assert meta["git_commit"] == "c0ffee"
            assert meta["is_dirty"] is False

        # 2. Successful Git commands with tracked modifications -> is_dirty is True
        with patch("subprocess.run") as mock_sub:
            def side_effect_dirty(cmd, *args, **kwargs):
                if "--abbrev-ref" in cmd:
                    return MagicMock(returncode=0, stdout="main\n")
                elif "rev-parse" in cmd:
                    return MagicMock(returncode=0, stdout="c0ffee\n")
                elif "status" in cmd:
                    return MagicMock(returncode=0, stdout=" M app/retriever.py\n")
                return MagicMock(returncode=1, stdout="")

            mock_sub.side_effect = side_effect_dirty
            meta = get_git_metadata()
            assert meta["is_dirty"] is True

        # 3. Successful Git commands with untracked files -> is_dirty is True
        with patch("subprocess.run") as mock_sub:
            def side_effect_untracked(cmd, *args, **kwargs):
                if "--abbrev-ref" in cmd:
                    return MagicMock(returncode=0, stdout="main\n")
                elif "rev-parse" in cmd:
                    return MagicMock(returncode=0, stdout="c0ffee\n")
                elif "status" in cmd:
                    return MagicMock(returncode=0, stdout="?? evaluation/results/new_run.json\n")
                return MagicMock(returncode=1, stdout="")

            mock_sub.side_effect = side_effect_untracked
            meta = get_git_metadata()
            assert meta["is_dirty"] is True

        # 4. Git executable unavailable and no usable .git metadata -> is_dirty is None
        with patch("subprocess.run", side_effect=FileNotFoundError("No git binary")):
            with patch("evaluation.retrieval.run_retrieval_evaluation.Path", side_effect=fake_no_git_path):
                meta = get_git_metadata()
                assert meta["git_branch"] == "unknown"
                assert meta["git_commit"] == "unavailable"
                assert meta["is_dirty"] is None

        # 5. Git executable unavailable but filesystem metadata allows branch/commit recovery -> is_dirty is None
        mock_head = MagicMock()
        mock_head.exists.return_value = True
        mock_head.read_text.return_value = "ref: refs/heads/feature-branch\n"

        mock_ref = MagicMock()
        mock_ref.exists.return_value = True
        mock_ref.read_text.return_value = "11223344556677889900aabbccddeeff11223344\n"

        def fake_git_path(p):
            if str(p) == ".git/HEAD":
                return mock_head
            if str(p) == ".git/refs/heads/feature-branch":
                return mock_ref
            return fake_no_git_path(p)

        with patch("subprocess.run", side_effect=FileNotFoundError("No git binary")):
            with patch("evaluation.retrieval.run_retrieval_evaluation.Path", side_effect=fake_git_path):
                meta = get_git_metadata()
                assert meta["git_branch"] == "feature-branch"
                assert meta["git_commit"] == "11223344556677889900aabbccddeeff11223344"
                assert meta["is_dirty"] is None

        # 6. Git status command fails while branch/commit are available -> is_dirty is None
        with patch("subprocess.run") as mock_sub:
            def side_effect_status_fail(cmd, *args, **kwargs):
                if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
                    return MagicMock(returncode=0, stdout="feat/retrieval-evaluation\n")
                elif cmd == ["git", "rev-parse", "HEAD"]:
                    return MagicMock(returncode=0, stdout="a6b5e40d92f7b92ae17a62755bb1953b30ca7385\n")
                elif cmd == ["git", "status", "--porcelain"]:
                    return MagicMock(returncode=128, stdout="", stderr="fatal: error running status")
                return MagicMock(returncode=1, stdout="")

            mock_sub.side_effect = side_effect_status_fail
            meta = get_git_metadata()
            assert meta["git_branch"] == "feat/retrieval-evaluation"
            assert meta["git_commit"] == "a6b5e40d92f7b92ae17a62755bb1953b30ca7385"
            assert meta["is_dirty"] is None

    def test_metadata_json_serializes_null_dirty_state(self):
        """
        Validates scenario 7: metadata JSON serializes the unknown state as JSON null,
        not false or a fabricated value.
        """
        from evaluation.retrieval.schemas import EvaluationSummary

        summary = EvaluationSummary(
            run_id="test_run_123",
            mode="baseline",
            timestamp="2026-10-14T19:00:00Z",
            git_branch="feat/test",
            git_commit="abcdef123456",
            is_dirty=None,
        )

        d = summary.to_dict()
        assert d["is_dirty"] is None

        json_str = json.dumps(d)
        assert '"is_dirty": null' in json_str

        parsed = json.loads(json_str)
        assert parsed["is_dirty"] is None
        assert parsed["is_dirty"] is not False
        assert parsed["is_dirty"] != "unknown"

    def test_benchmark_version_fallbacks(self, tmp_path):
        """
        Validates get_benchmark_version() fallback behavior:
        - Valid benchmark_metadata.json returns string version.
        - Missing file returns 'unknown'.
        - Malformed JSON returns 'unknown'.
        - Missing or invalid version fields return 'unknown'.
        - Unreadable file returns 'unknown'.
        """
        from evaluation.retrieval.run_retrieval_evaluation import get_benchmark_version

        # 1. Valid metadata file
        valid_dir = tmp_path / "valid_bench"
        valid_dir.mkdir()
        (valid_dir / "benchmark_metadata.json").write_text(
            json.dumps({"benchmark_version": "1.0.0", "dataset_name": "mediscan_eval"}),
            encoding="utf-8"
        )
        assert get_benchmark_version(valid_dir) == "1.0.0"

        # 2. Missing metadata file
        empty_dir = tmp_path / "empty_bench"
        empty_dir.mkdir()
        assert get_benchmark_version(empty_dir) == "unknown"

        # 3. Malformed JSON
        malformed_dir = tmp_path / "malformed_bench"
        malformed_dir.mkdir()
        (malformed_dir / "benchmark_metadata.json").write_text(
            "{ malformed json : [ missing braces",
            encoding="utf-8"
        )
        assert get_benchmark_version(malformed_dir) == "unknown"

        # 4. Missing version field
        no_ver_dir = tmp_path / "no_ver_bench"
        no_ver_dir.mkdir()
        (no_ver_dir / "benchmark_metadata.json").write_text(
            json.dumps({"dataset_name": "mediscan_eval"}),
            encoding="utf-8"
        )
        assert get_benchmark_version(no_ver_dir) == "unknown"

        # 5. Invalid version fields: empty string, whitespace, non-string, null
        for invalid_val in ["", "   ", None, 123, ["1.0.0"], {"nested": "1.0.0"}]:
            inv_dir = tmp_path / f"inv_{type(invalid_val).__name__}_{hash(str(invalid_val)) % 1000}"
            inv_dir.mkdir()
            (inv_dir / "benchmark_metadata.json").write_text(
                json.dumps({"benchmark_version": invalid_val}),
                encoding="utf-8"
            )
            assert get_benchmark_version(inv_dir) == "unknown"

        # 6. Non-dict root JSON (e.g. list)
        list_dir = tmp_path / "list_bench"
        list_dir.mkdir()
        (list_dir / "benchmark_metadata.json").write_text(
            json.dumps([{"benchmark_version": "1.0.0"}]),
            encoding="utf-8"
        )
        assert get_benchmark_version(list_dir) == "unknown"

        # 7. Unreadable file (simulated OS error)
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            assert get_benchmark_version(valid_dir) == "unknown"

    def test_negative_control_tightened_schema_validation(self, tmp_path):
        """
        Validates tightened negative-control contract:
        - Formally designated negative control (query_category='insufficient_evidence_unanswerable'
          AND expected_evidence_types=['none']) with 0 relevant gold items -> eligible_negative_control.
        - Arbitrary category tokens (e.g. 'negative_control') -> excluded_no_relevant_gold_evidence.
        - Correct category but non-empty or missing expected_evidence_types -> excluded_no_relevant_gold_evidence.
        - Undeclared 'is_negative_control' field alone does not grant negative control status.
        - Reviewed 0-relevant evidence without valid designation -> excluded_no_relevant_gold_evidence.
        - Unreviewed negative control -> not_evaluable_no_reviewed_gold_labels.
        """
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=Path("evaluation/benchmark"),
            output_dir=tmp_path / "neg_tight_test",
        )
        runner.execute_baseline = lambda query, types: (
            [RetrievedItem(evidence_id="drug_10", evidence_type="drug_product", source_record_id=10, channel="baseline", rank=1)],
            10,
            None,
        )

        # Case A: Formally designated, human-reviewed negative control
        runner.gold_judgments = {
            "NC-1": {"has_reviewed_judgments": True, "relevant_ids": set(), "all_reviewed_ids": {"drug_99"}}
        }
        res_a = runner.evaluate_case({
            "case_id": "NC-1",
            "query": "What is the recommended dose of FakeDrugXYZ?",
            "query_category": "insufficient_evidence_unanswerable",
            "expected_evidence_types": ["none"],
        })
        assert res_a.metrics["eligibility"] == "eligible_negative_control"
        assert res_a.metrics["recall_at_k"] is None
        assert res_a.metrics["precision_at_k"] is None
        assert res_a.metrics["baseline_mrr"] is None
        assert res_a.metrics["rejection_accuracy"] == 0.0
        assert res_a.metrics["false_positive_count_at_k"] == 1

        # Case B: Arbitrary/legacy category token 'negative_control' NOT in schema
        runner.gold_judgments = {
            "NC-2": {"has_reviewed_judgments": True, "relevant_ids": set(), "all_reviewed_ids": {"drug_99"}}
        }
        res_b = runner.evaluate_case({
            "case_id": "NC-2",
            "query": "Unrecognized token query",
            "query_category": "negative_control",  # Not valid category under schema
            "expected_evidence_types": ["none"],
        })
        assert res_b.metrics["eligibility"] == "excluded_no_relevant_gold_evidence"
        assert res_b.metrics["rejection_accuracy"] is None

        # Case C: Proper category, but expected_evidence_types is NOT ['none']
        runner.gold_judgments = {
            "NC-3": {"has_reviewed_judgments": True, "relevant_ids": set(), "all_reviewed_ids": {"drug_99"}}
        }
        res_c = runner.evaluate_case({
            "case_id": "NC-3",
            "query": "Unanswerable query with drug type",
            "query_category": "insufficient_evidence_unanswerable",
            "expected_evidence_types": ["drug_product"],  # Not ["none"]
        })
        assert res_c.metrics["eligibility"] == "excluded_no_relevant_gold_evidence"

        # Case D: Undeclared 'is_negative_control': True on non-designated query
        runner.gold_judgments = {
            "NC-4": {"has_reviewed_judgments": True, "relevant_ids": set(), "all_reviewed_ids": {"drug_99"}}
        }
        res_d = runner.evaluate_case({
            "case_id": "NC-4",
            "query": "Aspirin brand query with zero relevant",
            "query_category": "drug_brand_lookup",
            "is_negative_control": True,  # Undeclared field in schema
            "expected_evidence_types": ["drug_product"],
        })
        assert res_d.metrics["eligibility"] == "excluded_no_relevant_gold_evidence"

        # Case E: Reviewed zero-relevant evidence without negative control designation
        runner.gold_judgments = {
            "NC-5": {"has_reviewed_judgments": True, "relevant_ids": set(), "all_reviewed_ids": {"drug_99"}}
        }
        res_e = runner.evaluate_case({
            "case_id": "NC-5",
            "query": "Normal clinical query with zero relevant",
            "query_category": "clinical_contraindication",
            "expected_evidence_types": ["contraindication"],
        })
        assert res_e.metrics["eligibility"] == "excluded_no_relevant_gold_evidence"

        # Case F: Unreviewed negative control case (no reviewed gold records)
        runner.gold_judgments = {}
        res_f = runner.evaluate_case({
            "case_id": "NC-6",
            "query": "Unreviewed negative control",
            "query_category": "insufficient_evidence_unanswerable",
            "expected_evidence_types": ["none"],
        })
        assert res_f.metrics["eligibility"] == "not_evaluable_no_reviewed_gold_labels"
        assert res_f.metrics["rejection_accuracy"] is None

    def test_mixed_reviewed_and_unreviewed_gold_loading(self, tmp_path):
        """
        Validates load_gold_judgments strictly separates human-reviewed labels
        from preliminary or unreviewed annotations.
        """
        from evaluation.retrieval.run_retrieval_evaluation import load_gold_judgments

        gold_records = [
            # Case 1: Mixed reviewed and preliminary
            {"case_id": "C-1", "evidence_id": "drug_10", "relevance_grade": 3, "judgment_status": "human_reviewed"},
            {"case_id": "C-1", "evidence_id": "drug_20", "relevance_grade": 1, "judgment_status": "human_reviewed"},
            {"case_id": "C-1", "evidence_id": "drug_30", "relevance_grade": 3, "judgment_status": "preliminary_ai_annotated"},
            # Case 2: Only unreviewed / preliminary
            {"case_id": "C-2", "evidence_id": "drug_40", "relevance_grade": 3, "judgment_status": "preliminary_ai_annotated"},
            {"case_id": "C-2", "evidence_id": "drug_50", "relevance_grade": 2, "judgment_status": "unreviewed"},
            # Case 3: Reviewed negative control (0 items relevant, grade 0)
            {"case_id": "C-3", "evidence_id": "drug_60", "relevance_grade": 0, "judgment_status": "human_reviewed"},
        ]
        gold_file = tmp_path / "gold_judgments.jsonl"
        with open(gold_file, "w", encoding="utf-8") as f:
            for rec in gold_records:
                f.write(json.dumps(rec) + "\n")

        gold_by_case = load_gold_judgments(tmp_path)

        # C-1: Has reviewed judgments, drug_10 is relevant, drug_20 is not relevant (< 2), drug_30 ignored
        assert "C-1" in gold_by_case
        assert gold_by_case["C-1"]["has_reviewed_judgments"] is True
        assert gold_by_case["C-1"]["relevant_ids"] == {"drug_10"}
        assert gold_by_case["C-1"]["all_reviewed_ids"] == {"drug_10", "drug_20"}

        # C-2: Has NO human-reviewed judgments -> must not appear in gold_by_case
        assert "C-2" not in gold_by_case

        # C-3: Reviewed with 0 relevant evidence
        assert "C-3" in gold_by_case
        assert gold_by_case["C-3"]["has_reviewed_judgments"] is True
        assert gold_by_case["C-3"]["relevant_ids"] == set()
        assert gold_by_case["C-3"]["all_reviewed_ids"] == {"drug_60"}


class TestDualTrackEvaluationAdapter:
    """
    Tests for MediScanAI Phase B.3: Isolated Evidence-Verified Evaluation Adapter.
    Verifies isolation between official gold and AI-assisted evidence-verified tracks,
    provenance validation, negative control contract, and output isolation.
    """

    PHASE_A3_DATASET = Path("evaluation/benchmark/evidence_adjudication/phase_a_3/evidence_verified_judgments.jsonl")
    BENCHMARK_DIR = Path("evaluation/benchmark")
    GOLD_FILE = Path("evaluation/benchmark/gold_judgments.jsonl")

    def test_default_invocation_loads_only_official_gold(self, tmp_path):
        """1. Default invocation still loads only official gold judgments."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "default_run",
        )
        assert runner.evaluation_track == "official_human_gold"
        assert runner.evidence_judgments_path is None
        assert runner.evidence_audit_counts is None
        # Default loads official gold file which is empty
        assert len(runner.gold_judgments) == 0

    def test_empty_official_gold_remains_not_evaluable(self, tmp_path):
        """2. Empty official gold remains non-evaluable as before."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "empty_official",
        )
        case = {
            "case_id": "MED-BENCH-001",
            "query": "Lipitor",
            "query_category": "drug_brand_lookup",
            "expected_evidence_types": ["drug_product"],
        }
        res = runner.evaluate_case(case)
        assert res.metrics["eligibility"] == "not_evaluable_no_reviewed_gold_labels"
        assert res.metrics["recall_at_k"] is None
        assert res.metrics["precision_at_k"] is None
        assert res.metrics["baseline_mrr"] is None

    def test_explicit_research_track_loads_phase_a3_dataset(self, tmp_path):
        """3. Explicit research-track invocation loads the Phase A.3 dataset."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "research_run",
            evidence_judgments_path=self.PHASE_A3_DATASET,
        )
        assert runner.evaluation_track == "ai_assisted_evidence_verified"
        assert runner.evidence_judgments_path == self.PHASE_A3_DATASET
        assert len(runner.gold_judgments) == 50
        assert runner.evidence_audit_counts is not None
        assert runner.evidence_audit_counts["total_records"] == 62
        assert runner.evidence_audit_counts["negative_control_count"] == 5
        assert runner.evidence_audit_counts["verified_count"] == 55
        assert runner.evidence_audit_counts["grade_changed_count"] == 2
        assert runner.evidence_audit_counts["unresolved_count"] == 0

    def test_research_track_labels_use_evidence_based_grade(self, tmp_path):
        """4. Research-track labels use evidence_based_grade."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "grade_test",
            evidence_judgments_path=self.PHASE_A3_DATASET,
        )
        # Check MED-BENCH-001: drug_53548 has evidence_based_grade 3
        bench_1 = runner.gold_judgments["MED-BENCH-001"]
        assert "drug_53548" in bench_1["relevant_ids"]
        assert bench_1["grades"]["drug_53548"] == 3

    def test_preliminary_grades_not_used_for_scoring(self, tmp_path):
        """5. Preliminary grades are not used for scoring (downgrades are strictly non-relevant)."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "downgrade_test",
            evidence_judgments_path=self.PHASE_A3_DATASET,
        )
        # In Phase A.3, MED-BENCH-037 (disease_chunk_501) preliminary grade was 2,
        # but evidence_based_grade was downgraded to 1.
        # Under primary threshold (grade >= 2), grade 1 is NOT relevant.
        bench_37 = runner.gold_judgments["MED-BENCH-037"]
        assert "disease_chunk_501" not in bench_37["relevant_ids"]
        assert bench_37["grades"].get("disease_chunk_501") == 1

        # Also MED-BENCH-039 (disease_chunk_89) preliminary grade was 2, downgraded to 1
        bench_39 = runner.gold_judgments["MED-BENCH-039"]
        assert "disease_chunk_89" not in bench_39["relevant_ids"]
        assert bench_39["grades"].get("disease_chunk_89") == 1

        # Evaluate case 37 when disease_chunk_501 is retrieved: should NOT count as relevant hit
        runner.execute_baseline = lambda q, t: (
            [RetrievedItem(evidence_id="disease_chunk_501", evidence_type="disease_chunk", source_record_id=501, channel="baseline", rank=1)],
            10,
            None,
        )
        res = runner.evaluate_case({
            "case_id": "MED-BENCH-037",
            "query": "Type 2 diabetes mellitus overview",
            "query_category": "disease_overview",
            "expected_evidence_types": ["disease_chunk"],
        })
        # Since disease_chunk_501 was downgraded to grade 1, it is not relevant.
        # Only disease_chunk_248 (grade 3) is in relevant_gold.
        # Therefore, retrieving disease_chunk_501 yields 0 hits (recall=0.0, precision=0.0).
        # If preliminary grade (2) were mistakenly used, recall would be 0.5 or 1.0.
        assert res.metrics["eligibility"] == "eligible_evidence_verified"
        assert res.metrics["recall_at_k"] == 0.0
        assert res.metrics["precision_at_k"] == 0.0
        assert res.metrics["baseline_mrr"] == 0.0

    def test_invalid_provenance_rejected(self, tmp_path):
        """6. Invalid provenance is rejected (human_reviewed=True or invalid adjudicator_type)."""
        from evaluation.retrieval.run_retrieval_evaluation import load_evidence_verified_judgments

        # Case A: human_reviewed is True
        bad_rec_1 = {
            "case_id": "MED-BENCH-001",
            "evidence_id": "drug_53548",
            "human_reviewed": True,  # Invalid for AI-assisted track
            "adjudicator_type": "ai_assisted_external_evidence",
            "evidence_based_grade": 3,
            "judgment_status": "evidence_verified",
        }
        f1 = tmp_path / "bad_prov_1.jsonl"
        f1.write_text(json.dumps(bad_rec_1) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid provenance: human_reviewed must be False"):
            load_evidence_verified_judgments(f1)

        # Case B: invalid adjudicator_type
        bad_rec_2 = {
            "case_id": "MED-BENCH-001",
            "evidence_id": "drug_53548",
            "human_reviewed": False,
            "adjudicator_type": "human_clinician",  # Invalid
            "evidence_based_grade": 3,
            "judgment_status": "evidence_verified",
        }
        f2 = tmp_path / "bad_prov_2.jsonl"
        f2.write_text(json.dumps(bad_rec_2) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid adjudicator_type"):
            load_evidence_verified_judgments(f2)

    def test_duplicate_and_missing_ids_handling(self, tmp_path):
        """7. Duplicate, missing IDs, or contradictory records produce clear validation errors."""
        from evaluation.retrieval.run_retrieval_evaluation import load_evidence_verified_judgments

        base_rec = {
            "case_id": "MED-BENCH-001",
            "evidence_id": "drug_53548",
            "human_reviewed": False,
            "adjudicator_type": "ai_assisted_external_evidence",
            "evidence_based_grade": 3,
            "judgment_status": "evidence_verified",
        }

        # Missing case_id
        bad_missing_cid = dict(base_rec, case_id="")
        f_cid = tmp_path / "missing_cid.jsonl"
        f_cid.write_text(json.dumps(bad_missing_cid) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing required case_id"):
            load_evidence_verified_judgments(f_cid)

        # Missing evidence_id
        bad_missing_eid = dict(base_rec, evidence_id="")
        f_eid = tmp_path / "missing_eid.jsonl"
        f_eid.write_text(json.dumps(bad_missing_eid) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing required case_id or evidence_id"):
            load_evidence_verified_judgments(f_eid)

        # Contradictory duplicate
        dup_conflict = dict(base_rec, evidence_based_grade=1)
        f_dup = tmp_path / "dup_conflict.jsonl"
        f_dup.write_text(json.dumps(base_rec) + "\n" + json.dumps(dup_conflict) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="contradictory duplicate judgment"):
            load_evidence_verified_judgments(f_dup)

        # Invalid grade (out of range {0, 1, 2, 3})
        bad_grade = dict(base_rec, evidence_based_grade=5)
        f_grade = tmp_path / "bad_grade.jsonl"
        f_grade.write_text(json.dumps(bad_grade) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid evidence_based_grade"):
            load_evidence_verified_judgments(f_grade)

        # Unknown judgment status
        bad_status = dict(base_rec, judgment_status="fabricated_status")
        f_stat = tmp_path / "bad_status.jsonl"
        f_stat.write_text(json.dumps(bad_status) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="unrecognized judgment_status"):
            load_evidence_verified_judgments(f_stat)

        # Identical duplicate (allowed: idempotently deduplicated)
        f_ident = tmp_path / "ident_dup.jsonl"
        f_ident.write_text(json.dumps(base_rec) + "\n" + json.dumps(base_rec) + "\n", encoding="utf-8")
        judgments, stats = load_evidence_verified_judgments(f_ident)
        assert len(judgments["MED-BENCH-001"]["relevant_ids"]) == 1

    def test_missing_research_input_fails_without_fallback(self):
        """8. Missing research input fails clearly without falling back to gold."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        non_existent = Path("evaluation/benchmark/non_existent_file.jsonl")
        with pytest.raises(FileNotFoundError, match="Evidence judgments file not found"):
            EvaluationRunner(
                mode="baseline",
                benchmark_dir=self.BENCHMARK_DIR,
                evidence_judgments_path=non_existent,
            )

    def test_negative_controls_not_synthetic_retrieved_documents(self, tmp_path):
        """9. Negative controls do not become synthetic retrieved documents."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "neg_control_test",
            evidence_judgments_path=self.PHASE_A3_DATASET,
        )
        nc_case = runner.gold_judgments["MED-BENCH-041"]
        # 'none' is in all_reviewed_ids, but NOT in relevant_ids
        assert nc_case["all_reviewed_ids"] == {"none"}
        assert nc_case["relevant_ids"] == set()

        # Evaluate negative control when baseline returns nothing (correct rejection)
        runner.execute_baseline = lambda q, t: ([], 10, None)
        res_empty = runner.evaluate_case({
            "case_id": "MED-BENCH-041",
            "query": "What is the recommended pediatric dose of ChronoLithium?",
            "query_category": "insufficient_evidence_unanswerable",
            "expected_evidence_types": ["none"],
        })
        assert res_empty.metrics["eligibility"] == "eligible_negative_control"
        assert res_empty.metrics["rejection_accuracy"] == 1.0
        assert res_empty.metrics["false_positive_count_at_k"] == 0
        assert res_empty.metrics["recall_at_k"] is None
        assert res_empty.metrics["precision_at_k"] is None

        # Evaluate negative control when baseline returns a hallucinated item (false positive)
        runner.execute_baseline = lambda q, t: (
            [RetrievedItem(evidence_id="drug_999", evidence_type="drug_product", source_record_id=999, channel="baseline", rank=1)],
            10,
            None,
        )
        res_fp = runner.evaluate_case({
            "case_id": "MED-BENCH-041",
            "query": "What is the recommended pediatric dose of ChronoLithium?",
            "query_category": "insufficient_evidence_unanswerable",
            "expected_evidence_types": ["none"],
        })
        assert res_fp.metrics["eligibility"] == "eligible_negative_control"
        assert res_fp.metrics["rejection_accuracy"] == 0.0
        assert res_fp.metrics["false_positive_count_at_k"] == 1
        assert res_fp.metrics["recall_at_k"] is None

    def test_unresolved_evidence_excluded_from_metrics(self, tmp_path):
        """10. Unresolved / insufficient evidence is excluded according to existing metric contract."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner, load_evidence_verified_judgments

        # Record with unresolved status
        unresolved_rec = {
            "case_id": "MED-BENCH-001",
            "evidence_id": "drug_53548",
            "human_reviewed": False,
            "adjudicator_type": "ai_assisted_external_evidence",
            "evidence_based_grade": 0,
            "judgment_status": "insufficient_source_evidence",
        }
        f_unres = tmp_path / "unresolved.jsonl"
        f_unres.write_text(json.dumps(unresolved_rec) + "\n", encoding="utf-8")

        judgments, stats = load_evidence_verified_judgments(f_unres)
        assert stats["unresolved_count"] == 1
        assert stats["excluded_count"] == 1
        assert judgments["MED-BENCH-001"]["is_unresolved"] is True
        assert len(judgments["MED-BENCH-001"]["relevant_ids"]) == 0

        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "unres_run",
            evidence_judgments_path=f_unres,
        )
        res = runner.evaluate_case({
            "case_id": "MED-BENCH-001",
            "query": "Lipitor",
            "query_category": "drug_brand_lookup",
            "expected_evidence_types": ["drug_product"],
        })
        assert res.metrics["eligibility"] == "excluded_unresolved_evidence"
        assert res.metrics["recall_at_k"] is None
        assert res.metrics["precision_at_k"] is None
        assert res.metrics["baseline_mrr"] is None

    def test_graph_mrr_and_pooled_mrr_remain_unavailable(self, tmp_path):
        """11. Graph MRR and pooled MRR remain unavailable (None) where ranking is undefined."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        runner = EvaluationRunner(
            mode="both",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=tmp_path / "both_mrr_test",
            evidence_judgments_path=self.PHASE_A3_DATASET,
        )
        runner.execute_baseline = lambda q, t: (
            [RetrievedItem(evidence_id="drug_53548", evidence_type="drug_product", source_record_id=53548, channel="baseline", rank=1)],
            10,
            None,
        )
        runner.execute_graph = lambda q, t, c: (
            [RetrievedItem(evidence_id="drug_53548", evidence_type="drug_product", source_record_id=53548, channel="graph", rank=1)],
            5,
            None,
        )
        res = runner.evaluate_case({
            "case_id": "MED-BENCH-001",
            "query": "Lipitor",
            "query_category": "drug_brand_lookup",
            "expected_evidence_types": ["drug_product"],
        })
        assert res.metrics["eligibility"] == "eligible_evidence_verified"
        assert res.metrics["baseline_mrr"] == 1.0
        assert res.metrics["graph_mrr"] is None
        assert res.metrics["pooled_mrr"] is None

    def test_metadata_and_report_identify_research_track(self, tmp_path):
        """12. Metadata and report labels identify the research track."""
        from evaluation.retrieval.run_retrieval_evaluation import EvaluationRunner

        run_out = tmp_path / "eval_evidence_verified_test"
        runner = EvaluationRunner(
            mode="baseline",
            top_k=5,
            benchmark_dir=self.BENCHMARK_DIR,
            output_dir=run_out,
            evidence_judgments_path=self.PHASE_A3_DATASET,
        )
        runner._retrievers_initialized = True
        runner.execute_baseline = lambda q, t: ([], 10, None)

        summary = runner.run_benchmark(case_filter=["MED-BENCH-001"])

        assert summary.evaluation_track == "ai_assisted_evidence_verified"
        assert summary.judgments_path == str(self.PHASE_A3_DATASET)
        assert "AI-Assisted Evidence-Verified Evaluation" in summary.track_disclaimer

        # Check serialized JSON
        summary_file = run_out / "summary.json"
        assert summary_file.exists()
        summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
        assert summary_data["evaluation_track"] == "ai_assisted_evidence_verified"
        assert "AI-Assisted" in summary_data["track_disclaimer"]

        # Check README.md
        readme_file = run_out / "README.md"
        assert readme_file.exists()
        readme_text = readme_file.read_text(encoding="utf-8")
        assert "AI-Assisted Evidence-Verified Evaluation — Not Human-Adjudicated Gold" in readme_text

        # Check CSV
        csv_file = run_out / "summary.csv"
        assert csv_file.exists()
        csv_text = csv_file.read_text(encoding="utf-8")
        assert "ai_assisted_evidence_verified" in csv_text

    def test_gold_file_remains_zero_bytes(self):
        """14. The official gold file remains strictly zero bytes."""
        assert self.GOLD_FILE.exists()
        assert self.GOLD_FILE.stat().st_size == 0

