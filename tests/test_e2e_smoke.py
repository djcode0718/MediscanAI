# tests/test_e2e_smoke.py
"""
Phase 5 End-to-End Smoke Test
Covers the real application API lifecycle using deterministic mocked AI dependencies:
health -> register -> login -> me -> authenticated analysis -> history -> detail -> delete -> verify deleted
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock


def test_full_api_lifecycle_smoke(client: TestClient, mock_pipeline: MagicMock):
    """
    Verifies the complete sequential user lifecycle and API contract:
    1. Health check & Request ID propagation
    2. User registration
    3. User login & JWT issuance
    4. Authenticated identity resolution (/me)
    5. Authenticated clinical analysis execution & persistence
    6. Analysis history listing
    7. Analysis detail retrieval & ownership verification
    8. Analysis deletion
    9. Analysis 404 verification after deletion
    """
    custom_request_id = "smoke-test-req-9999"

    # 1. Health Check
    health_resp = client.get("/api/health", headers={"X-Request-ID": custom_request_id})
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "alive"
    # Preserves incoming X-Request-ID
    assert health_resp.headers.get("X-Request-ID") == custom_request_id

    # 2. Registration
    reg_payload = {
        "email": "smoke_user@mediscan.ai",
        "password": "SecurePassword123!",
        "full_name": "Smoke Test User"
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["user"]["email"] == reg_payload["email"]
    assert "access_token" in reg_data
    assert "password_hash" not in reg_data["user"]
    assert "X-Request-ID" in reg_resp.headers

    # 3. Login
    login_resp = client.post(
        "/api/auth/login",
        json={"email": reg_payload["email"], "password": reg_payload["password"]}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    token = login_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 4. Identity Check (/me)
    me_resp = client.get("/api/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == reg_payload["email"]
    assert me_data["is_active"] is True

    # 5. Authenticated Clinical Analysis Execution & Persistence
    analyze_resp = client.post(
        "/api/analyze",
        data={"text": "I have a sore throat and mild fever."},
        headers=auth_headers
    )
    assert analyze_resp.status_code == 200
    analysis_data = analyze_resp.json()
    assert "card" in analysis_data
    assert "meta" in analysis_data
    assert "analysis_id" in analysis_data
    analysis_id = analysis_data["analysis_id"]
    assert analysis_id is not None

    # 6. Analysis History Listing
    history_resp = client.get("/api/analyses", headers=auth_headers)
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert "items" in history_data
    assert history_data["total"] >= 1
    item_ids = [item["id"] for item in history_data["items"]]
    assert analysis_id in item_ids

    # 7. Analysis Detail Retrieval & Ownership Verification
    detail_resp = client.get(f"/api/analyses/{analysis_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == analysis_id
    assert detail_data["modality"] == "text"
    assert "summary_card" in detail_data
    assert "llm_output" in detail_data["summary_card"]

    # 8. Analysis Deletion
    del_resp = client.delete(f"/api/analyses/{analysis_id}", headers=auth_headers)
    assert del_resp.status_code in (200, 204)

    # 9. Verify Deleted Analysis Returns 404
    post_del_resp = client.get(f"/api/analyses/{analysis_id}", headers=auth_headers)
    assert post_del_resp.status_code == 404
