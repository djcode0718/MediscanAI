# tests/api/test_analyses_api.py
import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock
from backend.models.analysis import Analysis
from backend.core.concurrency import slot_manager
from app.llm import OllamaError


class TestAnalysesAPI:
    """API tests for /api/analyze and /api/analyses endpoints with strict ownership and reliability."""

    def test_create_analysis_success_text_only(self, client, auth_headers, mock_pipeline):
        res = client.post(
            "/api/analyze",
            data={"text": "Patient has persistent dry cough"},
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert "card" in data
        assert "analysis_id" in data
        assert "timings" in data
        assert "total_duration_ms" in data["timings"]
        assert slot_manager.active_slots == 0

    def test_create_analysis_unauthenticated_rejected(self, client, mock_pipeline):
        res = client.post(
            "/api/analyze",
            data={"text": "Symptom query"}
        )
        assert res.status_code == 401

    def test_create_analysis_concurrency_saturation_503(self, client, auth_headers, mock_pipeline):
        """When analysis slots are saturated, endpoint returns 503 with Retry-After header."""
        # Manually occupy all available slots
        slot_manager.try_acquire()
        slot_manager.try_acquire()
        assert slot_manager.available_slots == 0

        res = client.post(
            "/api/analyze",
            data={"text": "Concurrent burst query"},
            headers=auth_headers
        )
        assert res.status_code == 503
        assert "maximum concurrent clinical analyses" in res.json()["detail"]
        assert "retry-after" in res.headers

        # Release manual slots
        slot_manager.release()
        slot_manager.release()
        assert slot_manager.available_slots == 2

    def test_create_analysis_ollama_failure_returns_503(self, client, auth_headers):
        """When Ollama fails, endpoint returns 503 and releases concurrency slot."""
        mock_pipeline_fail = MagicMock()
        mock_pipeline_fail.run.side_effect = OllamaError("Ollama service down", is_unavailable=True)

        with patch("backend.main.get_pipeline", return_value=mock_pipeline_fail):
            res = client.post(
                "/api/analyze",
                data={"text": "Query during Ollama outage"},
                headers=auth_headers
            )
            assert res.status_code == 503
            assert "temporarily unavailable" in res.json()["detail"]
            assert slot_manager.active_slots == 0

    def test_create_analysis_pipeline_crash_returns_500_and_releases_slot(self, client, auth_headers, db_session, test_user):
        """When pipeline crashes with unexpected exception, returns 500, releases slot, and stores no record."""
        mock_pipeline_crash = MagicMock()
        mock_pipeline_crash.run.side_effect = RuntimeError("Simulated segmentation/memory crash")

        with patch("backend.main.get_pipeline", return_value=mock_pipeline_crash):
            res = client.post(
                "/api/analyze",
                data={"text": "Crash test query"},
                headers=auth_headers
            )
            assert res.status_code == 500
            assert slot_manager.active_slots == 0

            # Verify no Analysis record was created
            analyses = db_session.query(Analysis).filter(Analysis.user_id == test_user.id).all()
            assert len(analyses) == 0

    def test_analyses_history_and_strict_ownership_isolation(self, client, auth_headers, db_session, test_user):
        # Create Analysis for User A (test_user)
        analysis_a = Analysis(
            user_id=test_user.id,
            modality="text",
            status="completed",
            verdict="Suitable medication",
            summary_card={"llm_output": "Verdict details"},
            processing_duration_ms=250
        )
        db_session.add(analysis_a)
        db_session.commit()
        db_session.refresh(analysis_a)

        # 1. User A lists history -> contains analysis_a
        res_list = client.get("/api/analyses", headers=auth_headers)
        assert res_list.status_code == 200
        items = res_list.json()["items"]
        assert len(items) >= 1
        assert items[0]["id"] == analysis_a.id

        # 2. User A gets single analysis_a -> 200
        res_get = client.get(f"/api/analyses/{analysis_a.id}", headers=auth_headers)
        assert res_get.status_code == 200
        assert res_get.json()["id"] == analysis_a.id

        # 3. Another User B attempts to access analysis_a -> must return 404 (ownership isolation)
        from backend.core.security import create_access_token
        token_b = create_access_token(99999)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Mock User B existing in DB
        from backend.models.user import User
        from backend.core.security import hash_password
        user_b = User(id=99999, email="user_b@mediscan.ai", password_hash=hash_password("Pass123!"), is_active=True)
        db_session.add(user_b)
        db_session.commit()

        res_get_by_b = client.get(f"/api/analyses/{analysis_a.id}", headers=headers_b)
        assert res_get_by_b.status_code == 404

        # 4. User B attempts to delete analysis_a -> must return 404
        res_del_by_b = client.delete(f"/api/analyses/{analysis_a.id}", headers=headers_b)
        assert res_del_by_b.status_code == 404

        # 5. User A deletes own analysis_a -> 200
        res_del_by_a = client.delete(f"/api/analyses/{analysis_a.id}", headers=auth_headers)
        assert res_del_by_a.status_code == 200

        # Verify deleted in DB
        check = db_session.query(Analysis).filter(Analysis.id == analysis_a.id).first()
        assert check is None
