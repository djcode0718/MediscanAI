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
        """Verify readiness returns 200 when DB, models, and Ollama are reachable."""
        with patch("backend.main.check_db_connection", return_value=True):
            with patch("backend.main.pipeline_instance", object()):
                with patch("backend.main.transcriber_instance", object()):
                    with patch("backend.main.check_ollama_status", return_value=True):
                        res = client.get("/api/ready")
                        assert res.status_code == 200
                        data = res.json()
                        assert data["status"] == "ready"
                        assert data["components"]["database"] == "connected"
                        assert data["components"]["models_loaded"] == "ready"
                        assert data["components"]["ollama_service"] == "available"

    def test_readiness_probe_when_database_down(self, client):
        """Verify readiness returns 503 when database is unreachable."""
        with patch("backend.main.check_db_connection", return_value=False):
            with patch("backend.main.pipeline_instance", object()):
                with patch("backend.main.transcriber_instance", object()):
                    with patch("backend.main.check_ollama_status", return_value=True):
                        res = client.get("/api/ready")
                        assert res.status_code == 503
                        data = res.json()["detail"]
                        assert data["status"] == "not_ready"
                        assert data["components"]["database"] == "disconnected"

    def test_readiness_probe_when_ollama_down(self, client):
        """Verify readiness returns 503 when Ollama is unavailable."""
        with patch("backend.main.check_db_connection", return_value=True):
            with patch("backend.main.pipeline_instance", object()):
                with patch("backend.main.transcriber_instance", object()):
                    with patch("backend.main.check_ollama_status", return_value=False):
                        res = client.get("/api/ready")
                        assert res.status_code == 503
                        data = res.json()["detail"]
                        assert data["status"] == "not_ready"
                        assert data["components"]["ollama_service"] == "unavailable"
