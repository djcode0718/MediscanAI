# tests/test_auth.py
import sys
import os
import unittest
from datetime import timedelta
import jwt
from sqlalchemy import select
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.config import get_settings
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.db.session import SessionLocal
from backend.models.user import User
from backend.main import app

settings = get_settings()


class TestAuthSuite(unittest.TestCase):
    """
    Automated test suite for Phase 2 Authentication & Authorization.
    Tests registration, password hashing, login, JWT issuance/validation,
    protected endpoints, and role-based access control.
    """

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.test_emails = [
            "auth_user_test1@mediscan.ai",
            "auth_user_test2@mediscan.ai",
            "auth_user_inactive@mediscan.ai",
            "auth_user_superuser@mediscan.ai",
        ]
        # Clean up test users
        for email in self.test_emails:
            user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user:
                self.db.delete(user)
        self.db.commit()

    def tearDown(self):
        for email in self.test_emails:
            user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user:
                self.db.delete(user)
        self.db.commit()
        self.db.close()

    def test_01_security_password_hashing(self):
        """Test bcrypt password hashing and verification."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        self.assertNotEqual(password, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword123!", hashed))

    def test_02_jwt_token_generation_and_decoding(self):
        """Test JWT creation, claim decoding, and expiry verification."""
        sub = "test-subject-123"
        token = create_access_token(sub, expires_delta=timedelta(minutes=15))
        self.assertIsInstance(token, str)

        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), sub)
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)

        # Expired token test
        expired_token = create_access_token(sub, expires_delta=timedelta(minutes=-5))
        expired_payload = decode_access_token(expired_token)
        self.assertIsNone(expired_payload, "Expired token should return None")

        # Invalid secret test
        foreign_token = jwt.encode(
            {"sub": sub},
            "completely_different_signing_secret_key",
            algorithm="HS256",
        )
        foreign_payload = decode_access_token(foreign_token)
        self.assertIsNone(foreign_payload, "Token signed with wrong key should return None")

    def test_03_registration_flow_and_validation(self):
        """Test POST /api/auth/register endpoint validation and database persistence."""
        email = "auth_user_test1@mediscan.ai"
        password = "ValidPassword123!"
        full_name = "Jane Healthcare"

        # 1. Successful registration
        res = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["email"], email)
        self.assertEqual(data["user"]["full_name"], full_name)
        self.assertTrue(data["user"]["is_active"])
        self.assertFalse(data["user"]["is_superuser"])
        self.assertNotIn("password", data["user"])
        self.assertNotIn("password_hash", data["user"])

        # Verify DB entry
        user_in_db = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        self.assertIsNotNone(user_in_db)
        self.assertTrue(verify_password(password, user_in_db.password_hash))

        # 2. Duplicate registration attempt
        res_dup = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        self.assertEqual(res_dup.status_code, 400)
        self.assertIn("already registered", res_dup.json()["detail"].lower())

        # 3. Invalid email format
        res_inv_email = self.client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": password, "full_name": full_name},
        )
        self.assertEqual(res_inv_email.status_code, 422)

        # 4. Short password (< 8 chars)
        res_short_pwd = self.client.post(
            "/api/auth/register",
            json={"email": "auth_user_test2@mediscan.ai", "password": "short", "full_name": full_name},
        )
        self.assertEqual(res_short_pwd.status_code, 422)

    def test_04_login_flow(self):
        """Test POST /api/auth/login endpoint success and security failure responses."""
        email = "auth_user_test1@mediscan.ai"
        password = "ValidPassword123!"

        # Register user first
        self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Test User"},
        )

        # 1. Successful login
        res = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["email"], email)

        # 2. Wrong password (generic 401)
        res_wrong_pwd = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPassword123!"},
        )
        self.assertEqual(res_wrong_pwd.status_code, 401)
        self.assertEqual(res_wrong_pwd.json()["detail"], "Invalid email or password")

        # 3. Unknown email (generic 401 to prevent enumeration)
        res_unknown_user = self.client.post(
            "/api/auth/login",
            json={"email": "nonexistent@mediscan.ai", "password": password},
        )
        self.assertEqual(res_unknown_user.status_code, 401)
        self.assertEqual(res_unknown_user.json()["detail"], "Invalid email or password")

        # 4. Inactive user login
        inactive_user = User(
            email="auth_user_inactive@mediscan.ai",
            password_hash=hash_password("Password123!"),
            is_active=False,
        )
        self.db.add(inactive_user)
        self.db.commit()

        res_inactive = self.client.post(
            "/api/auth/login",
            json={"email": "auth_user_inactive@mediscan.ai", "password": "Password123!"},
        )
        self.assertEqual(res_inactive.status_code, 400)
        self.assertIn("inactive", res_inactive.json()["detail"].lower())

    def test_05_me_endpoint_and_token_authentication(self):
        """Test GET /api/auth/me authentication, header validation, and token lifetime checks."""
        email = "auth_user_test1@mediscan.ai"
        password = "ValidPassword123!"

        reg_res = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Test User"},
        )
        token = reg_res.json()["access_token"]

        # 1. Valid token
        res = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["email"], email)

        # 2. Missing authorization header
        res_no_auth = self.client.get("/api/auth/me")
        self.assertEqual(res_no_auth.status_code, 401)

        # 3. Malformed authorization header
        res_bad_auth = self.client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.structure"},
        )
        self.assertEqual(res_bad_auth.status_code, 401)

        # 4. Expired token
        user_in_db = self.db.execute(select(User).where(User.email == email)).scalar_one()
        expired_token = create_access_token(
            str(user_in_db.id),
            expires_delta=timedelta(minutes=-10),
        )
        res_expired = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(res_expired.status_code, 401)

    def test_06_analyze_endpoint_protection(self):
        """Verify that POST /api/analyze requires authentication and rejects unauthenticated requests."""
        # 1. Request without token is rejected with 401
        res_unauth = self.client.post(
            "/api/analyze",
            data={"text": "Patient has headache and fever"},
        )
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Request with invalid token is rejected with 401
        res_invalid_token = self.client.post(
            "/api/analyze",
            data={"text": "Patient has headache and fever"},
            headers={"Authorization": "Bearer not_a_real_token"},
        )
        self.assertEqual(res_invalid_token.status_code, 401)

    def test_07_rbac_and_active_user_dependencies(self):
        """Verify RBAC role checks (get_current_active_user, require_superuser)."""
        from backend.api.deps import get_current_active_user, require_superuser
        from fastapi import HTTPException

        # Regular active user
        reg_user = User(
            email="auth_user_test1@mediscan.ai",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
        )
        active_res = get_current_active_user(reg_user)
        self.assertEqual(active_res.email, reg_user.email)

        # Non-active user raises 403
        inactive_user = User(
            email="auth_user_inactive@mediscan.ai",
            password_hash="hash",
            is_active=False,
            is_superuser=False,
        )
        with self.assertRaises(HTTPException) as cm_inactive:
            get_current_active_user(inactive_user)
        self.assertEqual(cm_inactive.exception.status_code, 403)

        # Superuser check on regular user raises 403
        with self.assertRaises(HTTPException) as cm_super:
            require_superuser(reg_user)
        self.assertEqual(cm_super.exception.status_code, 403)

        # Superuser check on superuser passes
        super_user = User(
            email="auth_user_superuser@mediscan.ai",
            password_hash="hash",
            is_active=True,
            is_superuser=True,
        )
        super_res = require_superuser(super_user)
        self.assertEqual(super_res.email, super_user.email)


if __name__ == "__main__":
    unittest.main()
