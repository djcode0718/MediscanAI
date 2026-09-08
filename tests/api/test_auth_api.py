# tests/api/test_auth_api.py
import pytest
import jwt
import time
from backend.core.config import settings
from backend.core.security import create_access_token


class TestAuthAPI:
    """API-level tests for authentication, JWT lifecycle, and RBAC authorization."""

    def test_registration_valid_user(self, client):
        payload = {
            "email": "new_patient@mediscan.ai",
            "password": "ValidPassword123!",
            "full_name": "New Patient"
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["user"]["email"] == "new_patient@mediscan.ai"
        assert data["user"]["full_name"] == "New Patient"
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]

    def test_registration_duplicate_email(self, client, test_user):
        payload = {
            "email": test_user.email,
            "password": "AnotherPassword123!",
            "full_name": "Duplicate User"
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 400
        assert "already registered" in res.json()["detail"]

    def test_registration_malformed_email(self, client):
        payload = {
            "email": "invalid-email-format",
            "password": "ValidPassword123!",
            "full_name": "Bad Email"
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 422

    def test_registration_short_password(self, client):
        payload = {
            "email": "short_pass@mediscan.ai",
            "password": "123",
            "full_name": "Short Pass"
        }
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 422

    def test_login_valid_credentials(self, client, test_user):
        payload = {
            "email": test_user.email,
            "password": "Password123!"
        }
        res = client.post("/api/auth/login", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email

    def test_login_invalid_password(self, client, test_user):
        payload = {
            "email": test_user.email,
            "password": "WrongPassword123!"
        }
        res = client.post("/api/auth/login", json=payload)
        assert res.status_code == 401
        assert "Invalid email or password" in res.json()["detail"]

    def test_login_inactive_user(self, client, db_session, test_user):
        test_user.is_active = False
        db_session.commit()

        payload = {
            "email": test_user.email,
            "password": "Password123!"
        }
        res = client.post("/api/auth/login", json=payload)
        assert res.status_code == 400
        assert "Inactive user account" in res.json()["detail"]

    def test_current_user_me_valid_token(self, client, test_user, auth_headers):
        res = client.get("/api/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    def test_current_user_me_missing_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_current_user_me_expired_token(self, client, test_user):
        # Create expired token
        expired_payload = {
            "sub": str(test_user.id),
            "exp": time.time() - 3600
        }
        token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()

    def test_current_user_me_forged_token(self, client, test_user):
        # Create token with wrong secret
        token = jwt.encode({"sub": str(test_user.id), "exp": time.time() + 3600}, "forged-secret", algorithm="HS256")
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
