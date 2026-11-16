# backend/core/audit.py
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from backend.models.audit import AuditLog

logger = logging.getLogger("mediscanai.audit")


def record_audit_event(
    event_type: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
    *,
    isolated: bool = True
) -> None:
    """
    Persist an operational security audit event with explicit transaction ownership.

    Transaction semantics:
    - When isolated=True (default): An independent database session is used to persist the
      audit event. This guarantees durability even if the caller's business transaction
      subsequently rolls back or aborts with an HTTPException. Uncommitted changes on the
      caller's session (db) are NEVER committed, flushed, or rolled back by this function.
      If audit insertion fails, only the isolated audit session is rolled back; the caller's
      session remains completely undisturbed.
    - When isolated=False and db is provided: The audit event is attached to the caller's
      session and flushed within a savepoint (begin_nested). It commits or rolls back
      atomically with the caller's transaction.
    - Strictly forbids storing passwords, JWT tokens, or raw medical text in metadata.
    """
    # Sanitize metadata to guarantee sensitive fields are never saved
    sanitized_meta = None
    if metadata:
        sanitized_meta = {}
        forbidden_keys = {
            "password", "token", "access_token", "jwt",
            "authorization", "secret", "user_text", "symptoms"
        }
        for k, v in metadata.items():
            if k.lower() not in forbidden_keys:
                sanitized_meta[k] = v

    audit_entry = AuditLog(
        user_id=user_id,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent[:255] if user_agent else None,
        metadata_json=sanitized_meta
    )

    if isolated:
        # Isolated transaction: dedicated session bound to same engine
        if db is not None:
            audit_session = Session(bind=db.get_bind(), expire_on_commit=False)
        else:
            audit_session = SessionLocal()
        try:
            audit_session.add(audit_entry)
            audit_session.commit()
        except Exception as e:
            audit_session.rollback()
            logger.error(f"Failed to record isolated audit event '{event_type}': {e}", exc_info=True)
        finally:
            audit_session.close()
    else:
        # Caller-owned transaction
        if db is None:
            audit_session = SessionLocal()
            try:
                audit_session.add(audit_entry)
                audit_session.commit()
            except Exception as e:
                audit_session.rollback()
                logger.error(f"Failed to record audit event '{event_type}': {e}", exc_info=True)
            finally:
                audit_session.close()
        else:
            try:
                with db.begin_nested():
                    db.add(audit_entry)
                    db.flush()
            except Exception as e:
                logger.error(f"Failed to add audit event '{event_type}' to caller session: {e}", exc_info=True)
