# backend/schemas/analysis.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class AnalysisListItem(BaseModel):
    """Minimal schema for analysis items displayed in history lists."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    modality: str
    status: str
    verdict: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    created_at: datetime


class AnalysisDetailResponse(BaseModel):
    """Detailed schema for retrieving a single persisted analysis result."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    modality: str
    status: str
    verdict: Optional[str] = None
    summary_card: Dict[str, Any]
    processing_duration_ms: Optional[int] = None
    created_at: datetime


class AnalysisListResponse(BaseModel):
    """Paginated list response for user analysis history."""
    items: List[AnalysisListItem]
    total: int
    limit: int
    offset: int
