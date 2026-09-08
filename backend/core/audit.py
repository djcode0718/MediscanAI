# backend/core/audit.py
import logging
from typing import Optional, Dict, Any

from backend.db.session import SessionLocal
from backend.models.audit import AuditLog

logger = logging.getLogger("mediscanai.audit")


from sqlalchemy.orm import Session

def record_audit_event(
    event_type: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None
) -> None:
    """
    Persist an operational security audit event in an isolated database transaction.
    Ensures that audit log write failures never roll back or disrupt the primary application flow.
    Strictly forbids storing passwords, JWT tokens, or raw medical text in metadata.
    """
    own_session = False
    session = db
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        # Sanitize metadata to guarantee sensitive fields are never saved
        sanitized_meta = None
        if metadata:
            sanitized_meta = {}
            forbidden_keys = {"password", "token", "access_token", "jwt", "authorization", "secret", "user_text", "symptoms"}
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
        session.add(audit_entry)
        if own_session:
            session.commit()
    except Exception as e:
        if own_session:
            session.rollback()
        logger.error(f"Failed to record audit event '{event_type}': {e}", exc_info=True)
    finally:
        if own_session:
            session.close()
