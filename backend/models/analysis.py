# backend/models/analysis.py
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class Analysis(Base):
    """
    SQLAlchemy ORM model representing persisted structured analysis records.
    Adheres strictly to privacy by data minimization: raw image/audio binaries
    and raw user inputs are not stored in database columns.
    """
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    modality: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    verdict: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary_card: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    user = relationship("User", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} user_id={self.user_id} modality={self.modality} status={self.status}>"
