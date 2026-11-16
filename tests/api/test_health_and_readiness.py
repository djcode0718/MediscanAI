# tests/api/test_health_and_readiness.py
import pytest
from unittest.mock import patch


class TestHealthAndReadinessAPI:
    """API tests for /api/health (liveness) and /api/ready (readiness)."""

    def test_root_ping(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "running"

    def test_health_liveness_probe(self, client):
        """Verify liveness probe returns 200 quickly without checking downstream DB or LLM."""
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert data["app"] == "MediScanAI"

    def test_readiness_probe_when_all_ready(self, client):
        """Verify readiness returns 200 when DB, models, and Ollama are reachable in offline mode."""
        with patch("backend.main.settings.LLM_MODE", "offline"):
            with patch("backend.main.check_db_connection", return_value=True):
                with patch("backend.main.pipeline_instance", object()):
                    with patch("backend.main.transcriber_instance", object()):
                        with patch("backend.main.ocr_prewarmed", True):
                            with patch("backend.main.startup_complete", True):
                                with patch("backend.main.check_ollama_status", return_value=True):
                                    res = client.get("/api/ready")
                                    assert res.status_code == 200
                                    data = res.json()
                                    assert data["status"] == "ready"
                                    assert data["components"]["database"] == "connected"
                                    assert data["components"]["models_loaded"] == "ready"
                                    assert data["components"]["ocr_prewarmed"] == "ready"
                                    assert data["components"]["ollama_service"] == "available"

    def test_readiness_probe_when_database_down(self, client):
        """Verify readiness returns 503 when database is unreachable."""
        with patch("backend.main.check_db_connection", return_value=False):
            with patch("backend.main.pipeline_instance", object()):
                with patch("backend.main.transcriber_instance", object()):
                    with patch("backend.main.ocr_prewarmed", True):
                        with patch("backend.main.startup_complete", True):
                            with patch("backend.main.check_ollama_status", return_value=True):
                                res = client.get("/api/ready")
                                assert res.status_code == 503
                                data = res.json()["detail"]
                                assert data["status"] == "not_ready"
                                assert data["components"]["database"] == "disconnected"

    def test_readiness_probe_when_ollama_down(self, client):
        """Verify readiness returns 503 when Ollama is unavailable in offline mode."""
        with patch("backend.main.settings.LLM_MODE", "offline"):
            with patch("backend.main.check_db_connection", return_value=True):
                with patch("backend.main.pipeline_instance", object()):
                    with patch("backend.main.transcriber_instance", object()):
                        with patch("backend.main.ocr_prewarmed", True):
                            with patch("backend.main.startup_complete", True):
                                with patch("backend.main.check_ollama_status", return_value=False):
                                    res = client.get("/api/ready")
                                    assert res.status_code == 503
                                    data = res.json()["detail"]
                                    assert data["status"] == "not_ready"
                                    assert data["components"]["ollama_service"] == "unavailable"

    def test_readiness_probe_when_online_mode_without_ollama(self, client):
        """Verify readiness returns 200 when LLM_MODE is online even if Ollama is unavailable."""
        with patch("backend.main.settings.LLM_MODE", "online"):
            with patch("backend.main.check_db_connection", return_value=True):
                with patch("backend.main.pipeline_instance", object()):
                    with patch("backend.main.transcriber_instance", object()):
                        with patch("backend.main.ocr_prewarmed", True):
                            with patch("backend.main.startup_complete", True):
                                with patch("backend.main.check_ollama_status", return_value=False):
                                    res = client.get("/api/ready")
                                    assert res.status_code == 200
                                    data = res.json()
                                    assert data["status"] == "ready"
                                    assert data["components"]["ollama_service"] == "not_required"
                                    assert data["components"]["ocr_prewarmed"] == "ready"

    def test_readiness_probe_when_ocr_prewarm_failed(self, client):
        """Verify readiness returns 503 when PaddleOCR pre-warm failed or is pending."""
        with patch("backend.main.check_db_connection", return_value=True):
            with patch("backend.main.pipeline_instance", object()):
                with patch("backend.main.transcriber_instance", object()):
                    with patch("backend.main.ocr_prewarmed", False):
                        with patch("backend.main.startup_complete", False):
                            with patch("backend.main.startup_failure_reason", "Synthetic OCR inference timed out"):
                                res = client.get("/api/ready")
                                assert res.status_code == 503
                                data = res.json()["detail"]
                                assert data["status"] == "not_ready"
                                assert data["components"]["ocr_prewarmed"] == "failed_or_pending"
                                assert "startup_error" in data
                                assert "Synthetic OCR inference" in data["startup_error"]

    def test_analyze_rejected_when_startup_incomplete(self, client, auth_headers):
        """Verify /api/analyze immediately returns 503 if models are not pre-warmed."""
        with patch("backend.main.ocr_prewarmed", False):
            with patch("backend.main.startup_complete", False):
                with patch("backend.main.startup_failure_reason", "Prewarm incomplete"):
                    res = client.post("/api/analyze", data={"text": "Headache"}, headers=auth_headers)
                    assert res.status_code == 503
                    assert "initializing" in res.json()["detail"].lower()
