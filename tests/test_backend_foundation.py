# tests/test_backend_foundation.py
import sys
import os
import unittest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.config import Settings, get_settings
from backend.db.session import engine, SessionLocal, get_db, check_db_connection
from backend.models.user import User
from backend.main import app


class TestBackendFoundation(unittest.TestCase):
    """
    Automated test suite for Phase 1 Backend Foundation & PostgreSQL Database.
    Tests are fast, deterministic, and do not load heavy ML models.
    """

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_configuration_loading(self):
        """Verify centralized settings load with valid types and defaults."""
        settings = get_settings()
        self.assertIsInstance(settings, Settings)
        self.assertIn("postgresql", settings.DATABASE_URL)
        self.assertIsInstance(settings.DB_POOL_SIZE, int)
        self.assertGreater(settings.DB_POOL_SIZE, 0)
        self.assertIsInstance(settings.CORS_ORIGINS, list)
        self.assertIn("*", settings.CORS_ORIGINS)

    def test_02_database_connectivity(self):
        """Verify PostgreSQL connection and lightweight ping check."""
        is_connected = check_db_connection()
        self.assertTrue(is_connected, "PostgreSQL database should be reachable and accept connections.")

    def test_03_session_generator_lifecycle(self):
        """Verify get_db() dependency yields an active session and closes properly."""
        db_gen = get_db()
        session = next(db_gen)
        self.assertTrue(session.is_active)
        result = session.execute(text("SELECT 1")).scalar()
        self.assertEqual(result, 1)
        
        # Closing generator
        try:
            next(db_gen)
        except StopIteration:
            pass

    def test_04_user_model_crud_and_constraints(self):
        """Verify User model creation, schema defaults, and unique email constraints."""
        test_email = "test_foundation_user@mediscan.ai"
        
        # Clean up if existing
        existing = self.db.execute(select(User).where(User.email == test_email)).scalar_one_or_none()
        if existing:
            self.db.delete(existing)
            self.db.commit()

        # 1. Insert new user
        user = User(
            email=test_email,
            password_hash="placeholder_hash_phase2",
            is_active=True,
            is_superuser=False
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, test_email)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

        # 2. Test unique email constraint
        duplicate_user = User(
            email=test_email,
            password_hash="another_hash"
        )
        self.db.add(duplicate_user)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        # 3. Clean up
        user_to_delete = self.db.execute(select(User).where(User.email == test_email)).scalar_one_or_none()
        if user_to_delete:
            self.db.delete(user_to_delete)
            self.db.commit()

    def test_05_health_endpoints(self):
        """Verify GET / and GET /api/health endpoints."""
        # Root endpoint
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        data_root = res_root.json()
        self.assertEqual(data_root.get("status"), "running")
        self.assertEqual(data_root.get("app"), "MediScanAI")

        # Health endpoint
        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)
        data_health = res_health.json()
        self.assertEqual(data_health.get("status"), "healthy")
        self.assertEqual(data_health.get("database"), "connected")


if __name__ == "__main__":
    unittest.main()
