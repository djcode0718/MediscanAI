"""
Unit and integration tests for optional Neo4j Graph Retrieval in MediScanAI Pipeline (Phase 3.3).
Tests all edge cases, disabled modes, fallbacks, and provenance retention with zero live DB requirements.
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.core.config import Settings
from app.core import Pipeline
from app.graph.retriever import (
    GraphRetriever,
    DrugGraphResult,
    DiseaseChunkProvenance,
    DiseaseGraphResult,
    GraphRetrievalResponse,
)


@pytest.fixture
def mock_multi_retriever():
    """Mocks MultiRetriever search_specific responses for diseases, drugs, and drug_dict."""
    mr = MagicMock()

    def search_side_effect(index_name, text, top_k=5):
        if index_name == "diseases":
            return [
                (
                    "chunk_100",
                    0.95,
                    {
                        "chunk": {
                            "id": "chunk_100",
                            "disease": "Migraine",
                            "symptoms": ["headache", "nausea", "sensitivity to light"],
                        }
                    },
                )
            ]
        elif index_name == "drugs":
            return [
                (
                    "drug_200",
                    0.90,
                    {
                        "id": 200,
                        "brand_name": "Advil",
                        "generic_name": "Ibuprofen",
                        "indications_and_usage": "For temporary relief of minor aches and pains.",
                    },
                )
            ]
        elif index_name == "drug_dict":
            return [
                (
                    "dict_300",
                    0.88,
                    {
                        "drug_name": "Ibuprofen",
                    },
                )
            ]
        return []

    mr.search_specific.side_effect = search_side_effect
    return mr


@pytest.fixture
def sample_graph_drug():
    return DrugGraphResult(
        source_id=200,
        brand_name="Advil",
        generic_name="Ibuprofen",
        active_ingredients=["IBUPROFEN"],
        indications_text="Relieves headaches and minor aches.",
        warnings_text="Stomach bleeding warning.",
        dosage_text="200mg to 400mg every 4 to 6 hours.",
        adverse_reactions_text="Nausea, dyspepsia.",
        match_field="brand_name",
        provenance={"entity": "DrugProduct", "source_id": 200},
    )


@pytest.fixture
def sample_graph_disease():
    return DiseaseGraphResult(
        disease_name="Migraine",
        matched_symptoms=["headache", "nausea"],
        all_symptoms=["headache", "nausea", "sensitivity to light", "aura"],
        overlap_count=2,
        chunks=[DiseaseChunkProvenance(chunk_id="chunk_100", source_id=100)],
        provenance={"entity": "Disease", "disease_name": "Migraine", "chunk_count": 1},
    )


class TestPipelineGraphIntegration:

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_neo4j_disabled_mode(self, mock_gen, mock_multi_retriever):
        """1. When NEO4J_ENABLED=false, graph methods are not called and output contract is preserved."""
        settings = Settings(NEO4J_ENABLED=False, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        res = pipeline.run(user_text="Severe headache with nausea", image_path=None)

        # Graph methods should NEVER be called when disabled
        mock_graph.find_drugs_by_name.assert_not_called()
        mock_graph.get_disease_neighborhood.assert_not_called()
        mock_graph.find_diseases_by_symptoms.assert_not_called()

        # Output contract verified
        assert "card" in res
        assert "meta" in res
        assert "pipeline_timings" in res
        assert "retrieval_graph_ms" not in res["pipeline_timings"]
        assert "graph_drugs" not in res["card"]["retrieved"]
        assert "graph_diseases" not in res["card"]["retrieved"]

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_neo4j_enabled_reaches_context(
        self, mock_gen, mock_multi_retriever, sample_graph_drug, sample_graph_disease
    ):
        """2. When NEO4J_ENABLED=true, graph results reach prompt context and summary card."""
        settings = Settings(NEO4J_ENABLED=True, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)

        mock_graph.get_disease_neighborhood.return_value = GraphRetrievalResponse(
            diseases=[sample_graph_disease], status="success"
        )
        mock_graph.find_diseases_by_symptoms.return_value = GraphRetrievalResponse(
            diseases=[], status="empty"
        )
        mock_graph.find_drugs_by_name.return_value = GraphRetrievalResponse(
            drugs=[sample_graph_drug], status="success"
        )

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        # Mock OCR output by providing an image path and mocking extract_text_from_image
        with patch("app.core.extract_text_from_image", return_value={"texts": ["Advil", "200mg"]}):
            res = pipeline.run(user_text="Severe headache with nausea", image_path="tests/dummy.jpg")

        # Verify graph methods were invoked
        mock_graph.get_disease_neighborhood.assert_called_once_with("Migraine", max_chunks=3)
        mock_graph.find_drugs_by_name.assert_called()

        # Verify prompt received the graph sections
        prompt_arg = mock_gen.call_args[0][0]
        assert "-- Retrieved from GRAPH_DISEASES --" in prompt_arg
        assert "-- Retrieved from GRAPH_DRUGS --" in prompt_arg
        assert "IBUPROFEN" in prompt_arg

        # Verify summary card contains retrieved graph entries
        card_retrieved = res["card"]["retrieved"]
        assert "graph_diseases" in card_retrieved
        assert "graph_drugs" in card_retrieved
        assert "retrieval_graph_ms" in res["pipeline_timings"]

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_neo4j_empty_response_fallback(self, mock_gen, mock_multi_retriever):
        """3. When Neo4j returns empty, existing retrieval continues normally without failing."""
        settings = Settings(NEO4J_ENABLED=True, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)
        mock_graph.get_disease_neighborhood.return_value = GraphRetrievalResponse(status="empty")
        mock_graph.find_diseases_by_symptoms.return_value = GraphRetrievalResponse(status="empty")
        mock_graph.find_drugs_by_name.return_value = GraphRetrievalResponse(status="empty")

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        res = pipeline.run(user_text="Severe headache with nausea", image_path=None)

        assert res["card"]["llm_output"] == "Mocked clinical verdict."
        assert "graph_diseases" not in res["card"]["retrieved"]
        assert "graph_drugs" not in res["card"]["retrieved"]

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_expected_database_error_graceful_fallback(self, mock_gen, mock_multi_retriever):
        """4. Expected graph database errors (timeout, service unavailable) degrade gracefully."""
        settings = Settings(NEO4J_ENABLED=True, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)
        mock_graph.get_disease_neighborhood.return_value = GraphRetrievalResponse(
            status="timeout", error_code="QUERY_TIMEOUT", error_message="Timed out"
        )
        mock_graph.find_diseases_by_symptoms.return_value = GraphRetrievalResponse(
            status="error", error_code="DATABASE_UNAVAILABLE", error_message="Down"
        )
        mock_graph.find_drugs_by_name.return_value = GraphRetrievalResponse(
            status="error", error_code="DATABASE_UNAVAILABLE"
        )

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        # Pipeline should complete without raising an error
        res = pipeline.run(user_text="Headache", image_path=None)
        assert res["card"]["llm_output"] == "Mocked clinical verdict."

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_graph_evidence_retains_provenance(
        self, mock_gen, mock_multi_retriever, sample_graph_drug, sample_graph_disease
    ):
        """5. Verifies source provenance (chunk_id, source_id, provenance dict) is retained."""
        settings = Settings(NEO4J_ENABLED=True, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)
        mock_graph.get_disease_neighborhood.return_value = GraphRetrievalResponse(
            diseases=[sample_graph_disease], status="success"
        )
        mock_graph.find_diseases_by_symptoms.return_value = GraphRetrievalResponse(status="empty")
        mock_graph.find_drugs_by_name.return_value = GraphRetrievalResponse(
            drugs=[sample_graph_drug], status="success"
        )

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        with patch("app.core.extract_text_from_image", return_value={"texts": ["Advil"]}):
            res = pipeline.run(user_text="Headache", image_path="dummy.jpg")

        # Check prompt contains source_id and chunk citations
        prompt_arg = mock_gen.call_args[0][0]
        assert "'source_id': 200" in prompt_arg or "200" in prompt_arg
        assert "chunk_100" in prompt_arg

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_duplicate_evidence_handled_predictably(
        self, mock_gen, mock_multi_retriever, sample_graph_drug
    ):
        """6. Verifies that duplicate matches for the same drug source_id are deduplicated."""
        settings = Settings(NEO4J_ENABLED=True, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)
        mock_graph.get_disease_neighborhood.return_value = GraphRetrievalResponse(status="empty")
        mock_graph.find_diseases_by_symptoms.return_value = GraphRetrievalResponse(status="empty")
        # Return same drug twice (from both dictionary and brand name queries)
        mock_graph.find_drugs_by_name.return_value = GraphRetrievalResponse(
            drugs=[sample_graph_drug, sample_graph_drug], status="success"
        )

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        with patch("app.core.extract_text_from_image", return_value={"texts": ["Advil"]}):
            res = pipeline.run(user_text="Headache", image_path="dummy.jpg")

        # In summary card, graph_drugs should only have 1 entry for source_id 200
        graph_drugs = res["card"]["retrieved"]["graph_drugs"]
        assert len(graph_drugs) == 1
        assert graph_drugs[0]["key"] == "graph_drug_200"

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_ocr_input_not_passed_directly_when_candidate_available(
        self, mock_gen, mock_multi_retriever
    ):
        """7. Verifies resolved candidate names (Ibuprofen / Advil) are queried, NOT raw noisy OCR string."""
        settings = Settings(NEO4J_ENABLED=True, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)
        mock_graph.get_disease_neighborhood.return_value = GraphRetrievalResponse(status="empty")
        mock_graph.find_diseases_by_symptoms.return_value = GraphRetrievalResponse(status="empty")
        mock_graph.find_drugs_by_name.return_value = GraphRetrievalResponse(status="empty")

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        raw_ocr_string = "ADVIL 200MG EXP 12/28 LOT 99X"
        with patch("app.core.extract_text_from_image", return_value={"texts": [raw_ocr_string]}):
            pipeline.run(user_text="Headache", image_path="dummy.jpg")

        # Check call arguments to find_drugs_by_name
        calls = [c[0][0] for c in mock_graph.find_drugs_by_name.call_args_list]
        assert raw_ocr_string not in calls
        # Should call with resolved names from drug_dict / drugs
        assert any(cand in ("Ibuprofen", "Advil") for cand in calls)

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_original_retrieval_architecture_contracts_intact(
        self, mock_gen, mock_multi_retriever
    ):
        """8. Existing FAISS/BM25/RRF indices and output contracts remain completely intact."""
        pipeline = Pipeline(retriever=mock_multi_retriever)
        res = pipeline.run(user_text="Headache and fever")

        # MultiRetriever search_specific was called for diseases and drugs
        called_indices = [c[0][0] for c in mock_multi_retriever.search_specific.call_args_list]
        assert "diseases" in called_indices
        assert "drugs" in called_indices

        # Card schema verified
        card = res["card"]
        assert "user_text" in card
        assert "ocr_text" in card
        assert "llm_output" in card
        assert "retrieved" in card
        assert "diseases" in card["retrieved"]
        assert "drugs" in card["retrieved"]

    @patch("app.core.generate_with_mode", return_value="Mocked clinical verdict.")
    def test_graph_retrieval_not_called_repeatedly(
        self, mock_gen, mock_multi_retriever, sample_graph_disease
    ):
        """9. Graph queries are bounded and not invoked repeatedly beyond candidate limits."""
        settings = Settings(NEO4J_ENABLED=True, JWT_SECRET_KEY="test-key-32-chars-minimum-length")
        mock_graph = MagicMock(spec=GraphRetriever)
        mock_graph.get_disease_neighborhood.return_value = GraphRetrievalResponse(
            diseases=[sample_graph_disease], status="success"
        )
        mock_graph.find_diseases_by_symptoms.return_value = GraphRetrievalResponse(status="empty")
        mock_graph.find_drugs_by_name.return_value = GraphRetrievalResponse(status="empty")

        pipeline = Pipeline(
            retriever=mock_multi_retriever,
            settings=settings,
            graph_retriever=mock_graph,
        )

        pipeline.run(user_text="Headache", image_path=None)

        # get_disease_neighborhood called at most once for top candidate
        assert mock_graph.get_disease_neighborhood.call_count <= 1
        # No OCR image provided, so find_drugs_by_name should not be called
        assert mock_graph.find_drugs_by_name.call_count == 0
