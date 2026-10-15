"""
Unit tests for MediScanAI Phase A Ground-Truth Retrieval Benchmark.
Validates benchmark schema, structural invariants, source resolution,
deterministic generation, and the strict separation between unreviewed candidates
and human-reviewed gold judgments.

Execution constraints:
- No live Neo4j required.
- No network or LLM API calls.
- Off-limits directory entity_resolution/ is never accessed.
"""

import json
import csv
import re
from pathlib import Path
import pytest
import jsonschema

BENCHMARK_DIR = Path("evaluation/benchmark")
DATA_DIR = Path("data")

@pytest.fixture(scope="module")
def benchmark_schema():
    schema_path = BENCHMARK_DIR / "benchmark_schema.json"
    assert schema_path.exists(), f"Schema file missing at {schema_path}"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def benchmark_metadata():
    meta_path = BENCHMARK_DIR / "benchmark_metadata.json"
    assert meta_path.exists(), f"Metadata file missing at {meta_path}"
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def candidate_queries():
    queries_path = BENCHMARK_DIR / "candidate_queries.jsonl"
    assert queries_path.exists(), f"Candidate queries missing at {queries_path}"
    queries = []
    with open(queries_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    return queries

@pytest.fixture(scope="module")
def candidate_judgments():
    judg_path = BENCHMARK_DIR / "candidate_judgments.jsonl"
    assert judg_path.exists(), f"Candidate judgments missing at {judg_path}"
    judgments = []
    with open(judg_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                judgments.append(json.loads(line))
    return judgments

@pytest.fixture(scope="module")
def gold_judgments():
    gold_path = BENCHMARK_DIR / "gold_judgments.jsonl"
    assert gold_path.exists(), f"Gold judgments file missing at {gold_path}"
    records = []
    with open(gold_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


class TestBenchmarkArtifactsExistence:
    """Verifies that all required Phase A benchmark deliverables exist."""

    def test_all_benchmark_deliverables_exist(self):
        required_files = [
            BENCHMARK_DIR / "README.md",
            BENCHMARK_DIR / "candidate_queries.jsonl",
            BENCHMARK_DIR / "candidate_judgments.jsonl",
            BENCHMARK_DIR / "gold_judgments.jsonl",
            BENCHMARK_DIR / "review_template.csv",
            BENCHMARK_DIR / "benchmark_schema.json",
            BENCHMARK_DIR / "benchmark_metadata.json",
            BENCHMARK_DIR / "judgment_guidelines.md",
            BENCHMARK_DIR / "metric_contract.md",
            BENCHMARK_DIR / "build_benchmark.py",
        ]
        for p in required_files:
            assert p.exists() and p.is_file(), f"Required benchmark artifact missing: {p}"


class TestCandidateQueriesIntegrity:
    """Validates structural integrity, uniqueness, and schema of candidate queries."""

    def test_query_count_and_case_id_uniqueness(self, candidate_queries):
        assert 40 <= len(candidate_queries) <= 60, f"Expected 40-60 queries, got {len(candidate_queries)}"
        
        seen_case_ids = set()
        for q in candidate_queries:
            cid = q["case_id"]
            assert re.match(r"^MED-BENCH-\d{3}$", cid), f"Invalid case_id pattern: {cid}"
            assert cid not in seen_case_ids, f"Duplicate case_id found: {cid}"
            seen_case_ids.add(cid)

    def test_candidate_query_schema_conformance(self, candidate_queries, benchmark_schema):
        query_validator = jsonschema.Draft7Validator(benchmark_schema["definitions"]["CandidateQuery"])
        for q in candidate_queries:
            errors = list(query_validator.iter_errors(q))
            assert not errors, f"Query {q.get('case_id')} failed schema: {[e.message for e in errors]}"

    def test_category_distribution(self, candidate_queries, benchmark_metadata):
        expected_categories = {
            "drug_brand_lookup",
            "drug_generic_lookup",
            "active_ingredient_lookup",
            "brand_generic_ingredient_relationship",
            "single_symptom_disease_retrieval",
            "multi_symptom_disease_retrieval",
            "synonym_wording_variants",
            "ambiguous_queries",
            "insufficient_evidence_unanswerable",
            "graph_relevant",
            "graph_neutral"
        }
        actual_categories = {q["query_category"] for q in candidate_queries}
        assert actual_categories == expected_categories, f"Category mismatch: {actual_categories ^ expected_categories}"

        # Cross-check category counts against metadata
        meta_counts = benchmark_metadata["counts"]["queries_by_category"]
        for cat in expected_categories:
            actual_count = sum(1 for q in candidate_queries if q["query_category"] == cat)
            assert meta_counts[cat] == actual_count, f"Count mismatch for category {cat}: {meta_counts[cat]} vs {actual_count}"


class TestCandidateJudgmentsIntegrity:
    """Validates candidate evidence judgments, composite key uniqueness, and grade bounds."""

    def test_composite_evidence_identity_uniqueness(self, candidate_judgments):
        seen_keys = set()
        for j in candidate_judgments:
            key = (j["case_id"], j["evidence_id"])
            assert key not in seen_keys, f"Duplicate judgment composite key: {key}"
            seen_keys.add(key)

    def test_judgment_schema_conformance(self, candidate_judgments, benchmark_schema):
        judgment_validator = jsonschema.Draft7Validator(benchmark_schema["definitions"]["EvidenceJudgment"])
        for j in candidate_judgments:
            errors = list(judgment_validator.iter_errors(j))
            assert not errors, f"Judgment {j.get('case_id')}-{j.get('evidence_id')} failed schema: {[e.message for e in errors]}"

    def test_relevance_grade_bounds(self, candidate_judgments):
        for j in candidate_judgments:
            grade = j["relevance_grade"]
            assert isinstance(grade, int), f"Grade must be integer, got {type(grade)}"
            assert 0 <= grade <= 3, f"Grade {grade} out of range [0, 3] in case {j['case_id']}"


class TestVerificationBoundarySeparation:
    """Guarantees candidate judgments cannot be confused with human-reviewed gold judgments."""

    def test_candidate_judgments_marked_unverified(self, candidate_judgments):
        for j in candidate_judgments:
            assert j["judgment_status"] == "unverified_candidate", f"Candidate not marked unverified: {j}"
            assert j["reviewer_id"] is None, f"Candidate has unexpected reviewer_id: {j['reviewer_id']}"
            assert j["reviewed_at"] is None, f"Candidate has unexpected reviewed_at: {j['reviewed_at']}"

    def test_gold_judgments_separation_and_initial_state(self, gold_judgments, benchmark_metadata):
        # In Phase A, gold_judgments.jsonl must strictly reflect 0 human-reviewed rows
        assert len(gold_judgments) == 0, "Phase A gold_judgments.jsonl must contain 0 unreviewed rows."
        assert benchmark_metadata["counts"]["total_reviewed_gold_judgments"] == 0
        assert benchmark_metadata["labeling_status"] == "provisional_unverified_candidates"

    def test_gold_judgments_enforce_human_review_properties_if_populated(self, benchmark_schema):
        # If any record were in gold_judgments, it must have human_reviewed status
        judgment_validator = jsonschema.Draft7Validator(benchmark_schema["definitions"]["EvidenceJudgment"])
        sample_gold = {
            "case_id": "MED-BENCH-001",
            "query": "Lipitor",
            "query_category": "drug_brand_lookup",
            "evidence_id": "drug_53548",
            "evidence_type": "drug_product",
            "source_record_id": 53548,
            "relevance_grade": 3,
            "evidence_excerpt": "Brand: Lipitor",
            "judgment_status": "human_reviewed",
            "reviewer_id": "REV-01",
            "reviewed_at": "2026-10-14T10:00:00Z",
            "judgment_rationale": "Verified brand match."
        }
        errors = list(judgment_validator.iter_errors(sample_gold))
        assert not errors


class TestSourceResolution:
    """Verifies that evidence judgments point to real, existing source records."""

    def test_drug_records_resolve_to_source_file(self, candidate_judgments):
        # Load drug index ids
        drug_ids = set()
        with open(DATA_DIR / "drugs_faiss_data.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                drug_ids.add(r["id"])

        for j in candidate_judgments:
            if j["evidence_type"] == "drug_product":
                did = j["source_record_id"]
                assert did in drug_ids, f"Drug source ID {did} does not exist in data/drugs_faiss_data.jsonl"
                assert j["evidence_id"] == f"drug_{did}"

    def test_disease_records_resolve_to_source_file(self, candidate_judgments):
        disease_chunks = set()
        with open(DATA_DIR / "diseases_faiss_data.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                chunk = r.get("chunk", {})
                disease_chunks.add(chunk.get("id"))

        for j in candidate_judgments:
            if j["evidence_type"] == "disease_chunk":
                cid = j["evidence_id"].replace("disease_chunk_", "chunk_")
                assert cid in disease_chunks, f"Disease chunk {cid} does not exist in data/diseases_faiss_data.jsonl"

    def test_irregular_record_2305_cinzan_is_present(self, candidate_judgments):
        cinzan_judgments = [j for j in candidate_judgments if j["source_record_id"] == 2305]
        assert len(cinzan_judgments) > 0, "Record 2305 (Cinzan) missing from candidate judgments"
        for j in cinzan_judgments:
            assert "Cinzan" in j["evidence_excerpt"]
            assert j["evidence_id"] == "drug_2305"


class TestReviewTemplateAndMetadataConsistency:
    """Verifies tabular review template formatting and count agreement."""

    def test_review_template_headers_and_row_count(self, candidate_judgments):
        template_path = BENCHMARK_DIR / "review_template.csv"
        with open(template_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        expected_headers = [
            "case_id",
            "query",
            "query_category",
            "evidence_id",
            "evidence_type",
            "source_record_id",
            "proposed_grade",
            "reviewed_grade",
            "reviewer_id",
            "reviewed_at",
            "judgment_rationale",
            "adjudication_notes"
        ]
        assert headers == expected_headers
        assert len(rows) == len(candidate_judgments), f"Row count {len(rows)} != {len(candidate_judgments)}"

        # Validate permitted grade values, non-empty candidate fields, and boundary separation
        permitted_reviewed_grades = {"", "0", "1", "2", "3"}
        for row in rows:
            case_id = row[0]
            evidence_id = row[3]
            proposed_grade = row[6]
            reviewed_grade = row[7]
            reviewer_id = row[8]
            reviewed_at = row[9]
            adjudication_notes = row[11]

            assert proposed_grade in {"0", "1", "2", "3"}, f"Invalid proposed grade {proposed_grade} in {case_id}"
            assert reviewed_grade in permitted_reviewed_grades, f"Invalid reviewed grade '{reviewed_grade}' in {case_id}-{evidence_id}"

            # Verify that preliminary AI annotations do not masquerade as verified human gold reviewers
            if reviewer_id:
                assert "ai_" in reviewer_id or "preliminary" in reviewer_id or "rev_" in reviewer_id.lower(), \
                    f"Unexpected reviewer_id format: {reviewer_id}"

            # Clinical cases must remain flagged and ungraded if not reviewed by a human medical professional
            if "disease_chunk" in evidence_id:
                assert reviewed_grade == "", f"Clinical case {case_id}-{evidence_id} must remain ungraded pending qualified medical review"
                assert "FLAGGED" in adjudication_notes, f"Clinical case {case_id}-{evidence_id} missing FLAGGED note"

    def test_metadata_counts_match_files(self, candidate_queries, candidate_judgments, gold_judgments, benchmark_metadata):
        counts = benchmark_metadata["counts"]
        assert counts["total_candidate_queries"] == len(candidate_queries)
        assert counts["total_candidate_judgments"] == len(candidate_judgments)
        assert counts["total_reviewed_gold_judgments"] == len(gold_judgments)
