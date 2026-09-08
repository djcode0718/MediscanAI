# backend/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 DeclarativeBase for all MediScanAI ORM models.
    """
    pass


# Import models here so Base.metadata is fully populated for Alembic discovery
from backend.models.user import User  # noqa: E402, F401
from backend.models.analysis import Analysis  # noqa: E402, F401
from backend.models.audit import AuditLog  # noqa: E402, F401
