"""POST /api/analyze and GET /api/recommendations (03_RULES.md section 1).

No LLM calls here — Phase 2 is the rule engine only. Phase 4 swaps the templated
``explanation`` for validated LLM text.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db import get_db
from app.schemas import AnalyzeRequest, AnalyzeResponse, RecommendationsResponse
from app.services.analyze_service import get_recommendations, run_analysis

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Run the rule engine over an account's keywords",
)
def analyze(
    body: AnalyzeRequest, db: Session = Depends(get_db)
) -> AnalyzeResponse:
    try:
        return run_analysis(
            db,
            body.account_id,
            configured_threshold=get_settings().waste_cost_threshold,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Current recommendations for an account",
)
def recommendations(
    account_id: str = Query(...), db: Session = Depends(get_db)
) -> RecommendationsResponse:
    try:
        return get_recommendations(db, account_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
