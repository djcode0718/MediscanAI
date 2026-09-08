# tests/test_analysis_persistence.py
import sys
import os
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import select

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.core.security import create_access_token, hash_password
from backend.db.session import SessionLocal
from backend.models.user import User
from backend.models.analysis import Analysis
from backend.models.audit import AuditLog
from backend.core.audit import record_audit_event


class TestAnalysisPersistence(unittest.TestCase):
    """
    Automated test suite for Phase 3:
    - Data-minimized Analysis persistence
    - Strict user ownership enforcement on history & deletion
    - Transaction-safe, privacy-conscious audit logging
    """

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        self.user_a_email = "phase3_user_a@mediscan.ai"
        self.user_b_email = "phase3_user_b@mediscan.ai"
        self.audit_reg_email = "phase3_audit_reg@mediscan.ai"
        self.all_test_emails = [self.user_a_email, self.user_b_email, self.audit_reg_email]

        # Cleanup existing test users
        for email in self.all_test_emails:
            u = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if u:
                self.db.delete(u)
        self.db.commit()

        # Create User A
        self.user_a = User(
            email=self.user_a_email,
            full_name="User Alpha",
            password_hash=hash_password("Password123!"),
            is_active=True
        )
        # Create User B
        self.user_b = User(
            email=self.user_b_email,
            full_name="User Beta",
            password_hash=hash_password("Password123!"),
            is_active=True
        )
        self.db.add_all([self.user_a, self.user_b])
        self.db.commit()
        self.db.refresh(self.user_a)
        self.db.refresh(self.user_b)

        self.token_a = create_access_token(self.user_a.id)
        self.token_b = create_access_token(self.user_b.id)
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}
        self.headers_b = {"Authorization": f"Bearer {self.token_b}"}

    def tearDown(self):
        for email in self.all_test_emails:
            u = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if u:
                self.db.delete(u)
        self.db.commit()
        self.db.close()

    def test_01_analysis_persistence_and_schema_minimization(self):
        """Verify that analysis records persist structured outputs without raw audio/image blobs."""
        mock_summary_card = {
            "user_text": "Patient has dry cough",
            "ocr_text": "MUCOLEM 10mg",
            "llm_output": "Based on the information provided, the medicine is suitable.\n\n### Suggested Alternatives\n* Menthol\n\n### ⚠️ Important Warning\nConsult a doctor."
        }

        analysis = Analysis(
            user_id=self.user_a.id,
            modality="multimodal",
            status="completed",
            verdict="Based on the information provided, the medicine is suitable.",
            summary_card=mock_summary_card,
            processing_duration_ms=450
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Query from DB
        persisted = self.db.execute(select(Analysis).where(Analysis.id == analysis.id)).scalar_one()
        self.assertEqual(persisted.user_id, self.user_a.id)
        self.assertEqual(persisted.modality, "multimodal")
        self.assertEqual(persisted.status, "completed")
        self.assertIn("suitable", persisted.verdict)
        self.assertEqual(persisted.processing_duration_ms, 450)
        self.assertIsNotNone(persisted.created_at)

        # Verify no raw binary columns exist on Analysis model
        table_columns = [col.name for col in Analysis.__table__.columns]
        self.assertNotIn("raw_image", table_columns)
        self.assertNotIn("raw_audio", table_columns)
        self.assertNotIn("image_binary", table_columns)
        self.assertNotIn("audio_binary", table_columns)

    def test_02_strict_ownership_and_access_control(self):
        """Verify that User A cannot view or delete User B's analyses."""
        # 1. Insert analysis for User A
        analysis_a = Analysis(
            user_id=self.user_a.id,
            modality="text",
            status="completed",
            verdict="Verdict for User A",
            summary_card={"llm_output": "Verdict A"},
            processing_duration_ms=200
        )
        # 2. Insert analysis for User B
        analysis_b = Analysis(
            user_id=self.user_b.id,
            modality="image",
            status="completed",
            verdict="Verdict for User B",
            summary_card={"llm_output": "Verdict B"},
            processing_duration_ms=300
        )
        self.db.add_all([analysis_a, analysis_b])
        self.db.commit()
        self.db.refresh(analysis_a)
        self.db.refresh(analysis_b)

        # 3. User A lists analyses -> must ONLY receive analysis_a
        res_list_a = self.client.get("/api/analyses", headers=self.headers_a)
        self.assertEqual(res_list_a.status_code, 200)
        data_list_a = res_list_a.json()
        self.assertEqual(data_list_a["total"], 1)
        self.assertEqual(data_list_a["items"][0]["id"], analysis_a.id)
        self.assertEqual(data_list_a["items"][0]["verdict"], "Verdict for User A")

        # 4. User A tries to get analysis_b details -> must return 404
        res_get_b_by_a = self.client.get(f"/api/analyses/{analysis_b.id}", headers=self.headers_a)
        self.assertEqual(res_get_b_by_a.status_code, 404)

        # 5. User A tries to delete analysis_b -> must return 404
        res_del_b_by_a = self.client.delete(f"/api/analyses/{analysis_b.id}", headers=self.headers_a)
        self.assertEqual(res_del_b_by_a.status_code, 404)

        # 6. User A deletes own analysis_a -> must return 200
        res_del_a = self.client.delete(f"/api/analyses/{analysis_a.id}", headers=self.headers_a)
        self.assertEqual(res_del_a.status_code, 200)

        # Verify deletion in DB
        check_a = self.db.execute(select(Analysis).where(Analysis.id == analysis_a.id)).scalar_one_or_none()
        self.assertIsNone(check_a)

    def test_03_transaction_safe_and_privacy_conscious_audit_logging(self):
        """Verify audit logging lifecycle, data privacy filters, and transaction safety."""
        # 1. Register a user -> should create AUTH_REGISTER event
        test_email = "phase3_audit_reg@mediscan.ai"
        reg_res = self.client.post(
            "/api/auth/register",
            json={"email": test_email, "password": "Password123!", "full_name": "Audit Test"}
        )
        self.assertEqual(reg_res.status_code, 201)
        new_user_id = reg_res.json()["user"]["id"]

        # 2. Login -> should create AUTH_LOGIN_SUCCESS event
        login_res = self.client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "Password123!"}
        )
        self.assertEqual(login_res.status_code, 200)

        # 3. Bad Login -> should create AUTH_LOGIN_FAILURE event
        bad_login_res = self.client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "WrongPassword!"}
        )
        self.assertEqual(bad_login_res.status_code, 401)

        # 4. Check AuditLog table records
        audit_records = self.db.execute(
            select(AuditLog).where(AuditLog.user_id == new_user_id)
        ).scalars().all()

        event_types = [r.event_type for r in audit_records]
        self.assertIn("AUTH_REGISTER", event_types)
        self.assertIn("AUTH_LOGIN_SUCCESS", event_types)
        self.assertIn("AUTH_LOGIN_FAILURE", event_types)

        # 5. Verify no sensitive fields (passwords, tokens) in metadata
        for r in audit_records:
            if r.metadata_json:
                self.assertNotIn("password", r.metadata_json)
                self.assertNotIn("token", r.metadata_json)
                self.assertNotIn("access_token", r.metadata_json)

        # 6. Test transaction safety of record_audit_event (does not raise exception on failure)
        # Attempt recording with invalid data or mock without crashing
        try:
            record_audit_event(
                event_type="TEST_ISOLATED_EVENT",
                user_id=new_user_id,
                metadata={"password": "SecretPasswordShouldBeFiltered", "modality": "text"}
            )
            filtered_record = self.db.execute(
                select(AuditLog).where(
                    AuditLog.event_type == "TEST_ISOLATED_EVENT",
                    AuditLog.user_id == new_user_id
                )
            ).scalars().first()
            self.assertIsNotNone(filtered_record)
            self.assertNotIn("password", filtered_record.metadata_json)
            self.assertEqual(filtered_record.metadata_json.get("modality"), "text")
        except Exception as e:
            self.fail(f"record_audit_event should never raise an exception: {e}")

        # Cleanup
        u = self.db.execute(select(User).where(User.id == new_user_id)).scalar_one_or_none()
        if u:
            self.db.delete(u)
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
