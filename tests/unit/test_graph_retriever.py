"""
Unit tests for MediScanAI Standalone Neo4j Graph Retriever (Phase 3.2).
Uses mocked Neo4j drivers and sessions; requires no live database or Docker daemon.
"""

from unittest.mock import MagicMock, patch
import pytest
from neo4j.exceptions import ClientError, ServiceUnavailable, AuthError, TransientError

from backend.core.config import Settings
from app.graph.retriever import (
    GraphRetriever,
    DrugGraphResult,
    DiseaseChunkProvenance,
    DiseaseGraphResult,
    GraphRetrievalResponse,
    normalize_name_variants,
    normalize_ingredient_name,
    normalize_symptoms,
    clamp_bound,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_driver_and_session():
    """Sets up a mock Neo4j driver, session, and transaction context manager."""
    driver = MagicMock()
    session = MagicMock()
    tx = MagicMock()

    driver.session.return_value = session
    session.__enter__.return_value = session
    session.begin_transaction.return_value.__enter__.return_value = tx

    return driver, session, tx


@pytest.fixture
def retriever_enabled(mock_driver_and_session):
    driver, session, tx = mock_driver_and_session
    settings = Settings(
        NEO4J_ENABLED=True,
        JWT_SECRET_KEY="test-secret-key-at-least-32-chars-long",
    )
    retriever = GraphRetriever(driver=driver, settings=settings, query_timeout_seconds=2.0)
    return retriever, driver, session, tx


@pytest.fixture
def retriever_disabled():
    settings = Settings(
        NEO4J_ENABLED=False,
        JWT_SECRET_KEY="test-secret-key-at-least-32-chars-long",
    )
    return GraphRetriever(settings=settings)


# ==============================================================================
# Helper Normalizer & Bound Tests
# ==============================================================================

class TestRetrieverHelpers:
    def test_normalize_name_variants(self):
        # Mixed whitespace and common casing
        variants = normalize_name_variants("  tylenol   cold  ")
        assert variants == ["tylenol cold", "TYLENOL COLD", "Tylenol Cold"]

        # Empty / whitespace-only
        assert normalize_name_variants("") == []
        assert normalize_name_variants("   ") == []
        assert normalize_name_variants(None) == []

    def test_normalize_ingredient_name(self):
        assert normalize_ingredient_name(" acetaminophen ") == "ACETAMINOPHEN"
        assert normalize_ingredient_name("acetylsalicylic  acid ") == "ACETYLSALICYLIC ACID"
        assert normalize_ingredient_name("") == ""
        assert normalize_ingredient_name(None) == ""

    def test_normalize_symptoms(self):
        raw = [" Fatigue ", "FATIGUE", "pain in   chest", "headache", ""]
        normalized = normalize_symptoms(raw)
        # Deduplication preserving order, lowercased, whitespace collapsed
        assert normalized == ["fatigue", "pain in chest", "headache"]

        # Empty
        assert normalize_symptoms([]) == []
        assert normalize_symptoms(None) == []

    def test_clamp_bound(self):
        assert clamp_bound(10, 1, 20, default=5) == 10
        assert clamp_bound(100, 1, 20, default=5) == 20
        assert clamp_bound(-5, 1, 20, default=5) == 1
        assert clamp_bound("invalid", 1, 20, default=5) == 5


# ==============================================================================
# GraphRetriever Unit Tests
# ==============================================================================

class TestGraphRetriever:

    def test_disabled_mode_zero_sessions(self, retriever_disabled):
        """When NEO4J_ENABLED=False, retriever immediately returns disabled status."""
        resp = retriever_disabled.find_drugs_by_name("Tylenol")
        assert resp.status == "disabled"
        assert resp.drugs == []
        assert resp.latency_ms == 0

        resp_dis = retriever_disabled.find_diseases_by_symptoms(["fever", "cough"])
        assert resp_dis.status == "disabled"
        assert resp_dis.diseases == []

    def test_find_drugs_by_name_success(self, retriever_enabled):
        """Verifies successful drug product retrieval by name and ingredient mapping."""
        retriever, driver, session, tx = retriever_enabled

        mock_record = {
            "source_id": 42,
            "brand_name": "Tylenol",
            "generic_name": "Acetaminophen",
            "indications_text": "Relieves minor aches and pains",
            "warnings_text": "Liver warning",
            "dosage_text": "Take 2 tablets every 6 hours",
            "adverse_reactions_text": "Rash, nausea",
            "active_ingredients": ["ACETAMINOPHEN"],
            "match_field": "brand_name",
        }
        tx.run.return_value = [mock_record]

        resp = retriever.find_drugs_by_name("Tylenol", limit=5)

        assert resp.status == "success"
        assert len(resp.drugs) == 1
        drug = resp.drugs[0]
        assert isinstance(drug, DrugGraphResult)
        assert drug.source_id == 42
        assert drug.brand_name == "Tylenol"
        assert drug.active_ingredients == ["ACETAMINOPHEN"]
        assert drug.match_field == "brand_name"
        assert drug.provenance == {"entity": "DrugProduct", "source_id": 42}

        # Verify query parameters
        call_args = tx.run.call_args
        params = call_args[0][1]
        assert "Tylenol" in params["variants"]
        assert params["limit"] == 5

    def test_find_drugs_by_ingredient_success(self, retriever_enabled):
        """Verifies lookup by normalized uppercase active ingredient."""
        retriever, driver, session, tx = retriever_enabled

        mock_record = {
            "source_id": 101,
            "brand_name": "Bayer Aspirin",
            "generic_name": "Aspirin",
            "indications_text": "Pain reliever",
            "warnings_text": "Reye's syndrome",
            "dosage_text": "Take 1 tablet",
            "adverse_reactions_text": "Upset stomach",
            "active_ingredients": ["ASPIRIN"],
            "match_field": "ingredient",
        }
        tx.run.return_value = [mock_record]

        resp = retriever.find_drugs_by_ingredient("aspirin", limit=3)

        assert resp.status == "success"
        assert len(resp.drugs) == 1
        assert resp.drugs[0].active_ingredients == ["ASPIRIN"]
        assert resp.drugs[0].match_field == "ingredient"

        call_args = tx.run.call_args
        params = call_args[0][1]
        assert params["ingredient_name"] == "ASPIRIN"
        assert params["limit"] == 3

    def test_drug_unusual_casing_behavior(self, retriever_enabled):
        """Tests exact casing preservation and empty return for unmatched variants."""
        retriever, driver, session, tx = retriever_enabled

        # When queried with exact mixed-case 'Mucinex DM', it is present in $variants
        tx.run.return_value = [{
            "source_id": 500,
            "brand_name": "Mucinex DM",
            "generic_name": "guaifenesin and dextromethorphan",
            "active_ingredients": ["GUAIFENESIN", "DEXTROMETHORPHAN HBR"],
            "match_field": "brand_name",
        }]
        resp = retriever.find_drugs_by_name("Mucinex DM")
        assert resp.status == "success"
        assert resp.drugs[0].brand_name == "Mucinex DM"

        # Unmatched query returning empty
        tx.run.return_value = []
        resp_empty = retriever.find_drugs_by_name("UnknownBrand XYZ")
        assert resp_empty.status == "empty"
        assert resp_empty.drugs == []

    def test_find_diseases_by_symptoms_success(self, retriever_enabled):
        """Verifies disease retrieval, symptom overlap ranking, and chunk provenance."""
        retriever, driver, session, tx = retriever_enabled

        mock_record = {
            "disease_name": "Sickle cell anemia",
            "overlap_count": 2,
            "matched_symptoms": ["fatigue", "pain"],
            "all_symptoms": ["fatigue", "pain", "swelling", "infections"],
            "chunks": [
                {"chunk_id": "chunk_2541", "source_id": 2541},
                {"chunk_id": "chunk_2542", "source_id": 2542},
            ],
        }
        tx.run.return_value = [mock_record]

        resp = retriever.find_diseases_by_symptoms(["pain", "fatigue"], limit=5, max_chunks_per_disease=3)

        assert resp.status == "success"
        assert len(resp.diseases) == 1
        disease = resp.diseases[0]
        assert isinstance(disease, DiseaseGraphResult)
        assert disease.disease_name == "Sickle cell anemia"
        assert disease.overlap_count == 2
        assert disease.matched_symptoms == ["fatigue", "pain"]
        assert len(disease.chunks) == 2

        chunk1 = disease.chunks[0]
        assert isinstance(chunk1, DiseaseChunkProvenance)
        assert chunk1.chunk_id == "chunk_2541"
        assert chunk1.source_id == 2541

    def test_disease_with_zero_chunks_no_null_records(self, retriever_enabled):
        """Verifies that diseases without chunks return an empty chunk list, not null records."""
        retriever, driver, session, tx = retriever_enabled

        mock_record = {
            "disease_name": "Rare Disease Without Chunks",
            "overlap_count": 1,
            "matched_symptoms": ["dizziness"],
            "all_symptoms": ["dizziness"],
            "chunks": [],  # Empty list from Cypher list comprehension
        }
        tx.run.return_value = [mock_record]

        resp = retriever.find_diseases_by_symptoms(["dizziness"])

        assert resp.status == "success"
        assert resp.diseases[0].chunks == []

    def test_deterministic_chunk_ordering(self, retriever_enabled):
        """Verifies chunk ordering by source_id ascending and paired provenance."""
        retriever, driver, session, tx = retriever_enabled

        mock_record = {
            "disease_name": "Diabetes",
            "overlap_count": 1,
            "matched_symptoms": ["fatigue"],
            "all_symptoms": ["fatigue", "thirst"],
            "chunks": [
                {"chunk_id": "chunk_10", "source_id": 10},
                {"chunk_id": "chunk_50", "source_id": 50},
            ],
        }
        tx.run.return_value = [mock_record]

        resp = retriever.find_diseases_by_symptoms(["fatigue"])
        chunks = resp.diseases[0].chunks
        assert [c.source_id for c in chunks] == [10, 50]
        assert [c.chunk_id for c in chunks] == ["chunk_10", "chunk_50"]

    def test_get_disease_neighborhood_success(self, retriever_enabled):
        """Verifies fetching disease neighborhood directly by name."""
        retriever, driver, session, tx = retriever_enabled

        mock_record = {
            "disease_name": "Sickle cell anemia",
            "all_symptoms": ["fatigue", "pain", "swelling"],
            "chunks": [{"chunk_id": "chunk_1", "source_id": 1}],
        }
        tx.run.return_value = [mock_record]

        resp = retriever.get_disease_neighborhood("Sickle cell anemia", max_chunks=2)
        assert resp.status == "success"
        assert len(resp.diseases) == 1
        d = resp.diseases[0]
        assert d.disease_name == "Sickle cell anemia"
        assert d.overlap_count == 0
        assert len(d.chunks) == 1
        assert d.chunks[0].chunk_id == "chunk_1"

    def test_empty_and_malformed_inputs(self, retriever_enabled):
        """Verifies empty strings, whitespace, nulls, and empty lists return empty without query."""
        retriever, driver, session, tx = retriever_enabled

        assert retriever.find_drugs_by_name("").status == "empty"
        assert retriever.find_drugs_by_name("    ").status == "empty"
        assert retriever.find_drugs_by_ingredient("").status == "empty"
        assert retriever.find_diseases_by_symptoms([]).status == "empty"
        assert retriever.find_diseases_by_symptoms(["   "]).status == "empty"
        assert retriever.get_disease_neighborhood("").status == "empty"

        # Session was never opened
        session.begin_transaction.assert_not_called()

    def test_limit_clamping_and_symptom_deduplication(self, retriever_enabled):
        """Verifies limit clamping and symptom list cap at 20."""
        retriever, driver, session, tx = retriever_enabled
        tx.run.return_value = []

        # Over-sized limit
        retriever.find_drugs_by_name("Aspirin", limit=100)
        call_params = tx.run.call_args[0][1]
        assert call_params["limit"] == 20

        # Under-sized limit
        retriever.find_drugs_by_name("Aspirin", limit=-5)
        call_params = tx.run.call_args[0][1]
        assert call_params["limit"] == 1

        # Symptom deduplication and cap
        symptom_list = [f"symptom_{i}" for i in range(30)] + ["symptom_0", "  symptom_1  "]
        retriever.find_diseases_by_symptoms(symptom_list, limit=10, max_chunks_per_disease=10)
        call_params_dis = tx.run.call_args[0][1]
        assert len(call_params_dis["normalized_symptoms"]) == 20
        assert call_params_dis["max_chunks"] == 5

    def test_connection_failure_resilience(self, retriever_enabled):
        """Verifies ServiceUnavailable is caught and mapped to error status."""
        retriever, driver, session, tx = retriever_enabled
        session.begin_transaction.side_effect = ServiceUnavailable("Database down")

        resp = retriever.find_drugs_by_name("Advil")
        assert resp.status == "error"
        assert resp.error_code == "DATABASE_UNAVAILABLE"
        assert "unreachable" in resp.error_message
        assert resp.drugs == []

    def test_query_timeout_resilience(self, retriever_enabled):
        """Verifies transaction timeout ClientError maps to timeout status."""
        retriever, driver, session, tx = retriever_enabled
        err = ClientError("The transaction has been terminated. TransactionTimedOut.")
        err.code = "Neo.ClientError.Transaction.TransactionTimedOut"
        session.begin_transaction.side_effect = err

        resp = retriever.find_drugs_by_name("Advil")
        assert resp.status == "timeout"
        assert resp.error_code == "QUERY_TIMEOUT"
        assert "transaction timeout" in resp.error_message.lower()

    def test_auth_error_resilience(self, retriever_enabled):
        """Verifies AuthError maps to error status with AUTHENTICATION_FAILED code."""
        retriever, driver, session, tx = retriever_enabled
        session.begin_transaction.side_effect = AuthError("Unauthorized")

        resp = retriever.find_drugs_by_name("Advil")
        assert resp.status == "error"
        assert resp.error_code == "AUTHENTICATION_FAILED"

    def test_unexpected_programming_error_propagates(self, retriever_enabled):
        """Verifies unexpected programming errors (e.g. TypeError) are not swallowed."""
        retriever, driver, session, tx = retriever_enabled
        # Mock tx.run returning an object whose iteration raises TypeError
        tx.run.side_effect = TypeError("Unexpected bug in caller code")

        with pytest.raises(TypeError, match="Unexpected bug"):
            retriever.find_drugs_by_name("Advil")

    def test_session_cleanup_guarantee(self, retriever_enabled):
        """Verifies session.close() is called on both successful and exceptional executions."""
        retriever, driver, session, tx = retriever_enabled

        # 1. Success case
        tx.run.return_value = []
        retriever.find_drugs_by_name("Tylenol")
        session.close.assert_called_once()

        # 2. Exceptional case
        session.close.reset_mock()
        session.begin_transaction.side_effect = ServiceUnavailable("Failed")
        retriever.find_drugs_by_name("Tylenol")
        session.close.assert_called_once()
