# tests/database/test_database_sqlite.py
import pytest
from sqlalchemy.exc import IntegrityError
from backend.models.user import User
from backend.models.analysis import Analysis
from backend.models.audit import AuditLog
from backend.core.security import hash_password


class TestDatabaseLayerSQLite:
    """Database model and transaction tests on isolated SQLite engine."""

    def test_user_creation_and_unique_email_constraint(self, db_session):
        u1 = User(
            email="unique_user@mediscan.ai",
            full_name="Unique User",
            password_hash=hash_password("Pass123!"),
            is_active=True
        )
        db_session.add(u1)
        db_session.commit()

        # Duplicate email must raise IntegrityError
        u2 = User(
            email="unique_user@mediscan.ai",
            full_name="Duplicate User",
            password_hash=hash_password("Pass123!"),
            is_active=True
        )
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_analysis_cascade_deletion(self, db_session):
        user = User(
            email="cascade_user@mediscan.ai",
            full_name="Cascade User",
            password_hash=hash_password("Pass123!"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        analysis = Analysis(
            user_id=user.id,
            modality="text",
            status="completed",
            verdict="Test verdict",
            summary_card={"data": "test"},
            processing_duration_ms=100
        )
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)
        analysis_id = analysis.id

        # Deleting the user should cascade delete their analyses
        db_session.delete(user)
        db_session.commit()

        check = db_session.query(Analysis).filter(Analysis.id == analysis_id).first()
        assert check is None

    def test_audit_log_user_nullable_on_delete(self, db_session):
        user = User(
            email="audit_user@mediscan.ai",
            full_name="Audit User",
            password_hash=hash_password("Pass123!"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        audit = AuditLog(
            user_id=user.id,
            event_type="TEST_EVENT",
            ip_address="127.0.0.1",
            metadata_json={"action": "test"}
        )
        db_session.add(audit)
        db_session.commit()
        db_session.refresh(audit)
        audit_id = audit.id

        # Delete user -> audit record remains with user_id set to NULL or preserved
        db_session.delete(user)
        db_session.commit()

        check_audit = db_session.query(AuditLog).filter(AuditLog.id == audit_id).first()
        assert check_audit is not None
