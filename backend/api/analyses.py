# backend/api/analyses.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.models.analysis import Analysis
from backend.api.deps import get_current_active_user
from backend.schemas.analysis import (
    AnalysisListItem,
    AnalysisDetailResponse,
    AnalysisListResponse
)
from backend.core.audit import record_audit_event

router = APIRouter(prefix="/api/analyses", tags=["Analyses"])


@router.get(
    "",
    response_model=AnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="List paginated analysis history for current user"
)
def list_analyses(
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Offset starting point for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve deterministic paginated analysis records strictly owned by the authenticated user.
    """
    # 1. Count total records for this user
    total_count = db.execute(
        select(func.count())
        .select_from(Analysis)
        .where(Analysis.user_id == current_user.id)
    ).scalar_one()

    # 2. Query paginated list ordered by creation time
    analyses = db.execute(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    items = [AnalysisListItem.model_validate(a) for a in analyses]

    return AnalysisListResponse(
        items=items,
        total=total_count,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single analysis details"
)
def get_analysis_detail(
    analysis_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve single detailed analysis record. Strict ownership enforcement guarantees
    users can only inspect their own records (returns 404 on non-owned or missing records).
    """
    analysis = db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found."
        )

    # Record operational audit event
    record_audit_event(
        event_type="ANALYSIS_ACCESSED",
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"analysis_id": analysis.id, "modality": analysis.modality},
        db=db
    )

    return AnalysisDetailResponse.model_validate(analysis)


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete single analysis record"
)
def delete_analysis(
    analysis_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a user's own analysis record from PostgreSQL.
    Strict ownership enforcement guarantees cross-user deletion is impossible.
    """
    analysis = db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found."
        )

    db.delete(analysis)
    db.commit()

    # Record audit event (without storing deleted medical details)
    record_audit_event(
        event_type="ANALYSIS_DELETED",
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"analysis_id": analysis_id},
        db=db
    )

    return {"status": "deleted", "id": analysis_id}
