# tests/database/test_database_postgres.py
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from backend.db.session import SessionLocal, engine
from backend.models.user import User
from backend.models.analysis import Analysis
from backend.models.audit import AuditLog
from backend.core.security import hash_password


class TestDatabaseLayerPostgreSQL:
    """Integration tests executing against the local PostgreSQL instance."""

    def setup_method(self):
        self.db = SessionLocal()
        self.test_email = "pg_test_unique@mediscan.ai"
        # Cleanup any leftover test records
        existing = self.db.execute(select(User).where(User.email == self.test_email)).scalar_one_or_none()
        if existing:
            self.db.delete(existing)
            self.db.commit()

    def teardown_method(self):
        existing = self.db.execute(select(User).where(User.email == self.test_email)).scalar_one_or_none()
        if existing:
            self.db.delete(existing)
            self.db.commit()
        self.db.close()

    def test_postgres_connectivity_and_version(self):
        """Verify real PostgreSQL engine connection and query execution."""
        with engine.connect() as conn:
            res = conn.execute(text("SELECT version()")).scalar()
            assert "PostgreSQL" in res

    def test_postgres_json_storage_and_query(self):
        """Verify JSON column serialization and deserialization in PostgreSQL."""
        user = User(
            email=self.test_email,
            full_name="Postgres Test User",
            password_hash=hash_password("Password123!"),
            is_active=True
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        complex_card = {
            "user_text": "Sample symptom text with special chars & <tags>",
            "retrievals": {
                "diseases": [("pharyngitis", 0.985, {"disease": "Pharyngitis", "symptoms": ["sore throat"]})]
            },
            "llm_output": "Detailed clinical markdown text with formatting."
        }

        analysis = Analysis(
            user_id=user.id,
            modality="multimodal",
            status="completed",
            verdict="Suitable Medication",
            summary_card=complex_card,
            processing_duration_ms=520
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Retrieve and verify structured JSON dictionary integrity
        persisted = self.db.execute(select(Analysis).where(Analysis.id == analysis.id)).scalar_one()
        assert persisted.summary_card["user_text"] == complex_card["user_text"]
        assert persisted.summary_card["retrievals"]["diseases"][0][0] == "pharyngitis"
        assert persisted.summary_card["llm_output"] == complex_card["llm_output"]

    def test_postgres_transaction_rollback_on_integrity_violation(self):
        """Verify PostgreSQL transaction rollback on unique constraint violation."""
        u1 = User(email=self.test_email, password_hash=hash_password("P1!"), full_name="User 1")
        self.db.add(u1)
        self.db.commit()

        u2 = User(email=self.test_email, password_hash=hash_password("P2!"), full_name="User 2")
        self.db.add(u2)

        with pytest.raises(IntegrityError):
            self.db.commit()

        self.db.rollback()
        # Ensure session remains usable after rollback
        count = self.db.execute(select(User).where(User.email == self.test_email)).scalars().all()
        assert len(count) == 1
