"""POST /api/budget/optimize and POST /api/simulation (Phase 8, 05_DESIGN screens 4-5).

Rule-based, no ML. Secondary to the audit + WhatsApp loop.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.schemas import (
    BudgetOptimizeRequest,
    BudgetOptimizeResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.services.planning_service import (
    optimize_budget_for_account,
    simulate_for_account,
)

router = APIRouter(prefix="/api", tags=["planning"])


@router.post(
    "/budget/optimize",
    response_model=BudgetOptimizeResponse,
    summary="Suggest how to split a monthly budget across campaigns",
)
def budget_optimize(
    body: BudgetOptimizeRequest, db: Session = Depends(get_db)
) -> BudgetOptimizeResponse:
    try:
        return optimize_budget_for_account(db, body.account_id, body.total_budget)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post(
    "/simulation",
    response_model=SimulationResponse,
    summary="Current vs projected cost per sale and sales count",
)
def simulation(
    body: SimulationRequest, db: Session = Depends(get_db)
) -> SimulationResponse:
    try:
        return simulate_for_account(db, body.account_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
