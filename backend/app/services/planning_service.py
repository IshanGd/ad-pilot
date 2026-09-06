"""Budget optimizer + simulator over stored account data (Phase 8).

Route handlers call these; the maths lives in engine/budget.py and
engine/simulation.py and stays independently testable.
"""
from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.budget import CampaignInput, optimize_budget
from app.engine.simulation import SimulationInput, simulate
from app.models.tables import Account, Campaign, Keyword, OptimizationRun
from app.schemas import (
    BudgetOptimizeResponse,
    CampaignAllocationOut,
    SimulationResponse,
)
from app.services.analyze_service import get_recommendations

_WASTE_TYPES = {"PAUSE_KEYWORD", "ADD_NEGATIVE"}


def _load_account(db: Session, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise LookupError(f"Unknown account_id: {account_id}")
    return account


def _campaigns(db: Session, account_id: str) -> list[Campaign]:
    return list(
        db.scalars(select(Campaign).where(Campaign.account_id == account_id)).all()
    )


def optimize_budget_for_account(
    db: Session, account_id: str, total_budget: float
) -> BudgetOptimizeResponse:
    _load_account(db, account_id)
    campaigns = _campaigns(db, account_id)

    total_spend = sum(c.spend for c in campaigns)
    total_conv = sum(c.conversions for c in campaigns)
    avg_cpa = (total_spend / total_conv) if total_conv else None

    allocations = optimize_budget(
        [
            CampaignInput(
                campaign_id=str(c.id),
                name=c.name,
                spend=c.spend,
                conversions=c.conversions,
                conversion_value=c.conversion_value,
            )
            for c in campaigns
        ],
        total_budget,
        avg_cpa,
    )

    return BudgetOptimizeResponse(
        account_id=str(account_id),
        total_budget=total_budget,
        current_total_spend=round(total_spend, 2),
        allocations=[CampaignAllocationOut(**asdict(a)) for a in allocations],
    )


def simulate_for_account(db: Session, account_id: str) -> SimulationResponse:
    _load_account(db, account_id)
    campaigns = _campaigns(db, account_id)

    total_spend = sum(c.spend for c in campaigns)
    total_conv = sum(c.conversions for c in campaigns)

    recs = get_recommendations(db, account_id).recommendations
    wasted = sum(
        r.estimated_impact or 0.0 for r in recs if r.type in _WASTE_TYPES
    )

    best_cpa: float | None = None
    for r in recs:
        if r.type == "INCREASE_BUDGET" and r.keyword_id:
            kw = db.get(Keyword, r.keyword_id)
            if kw is not None and kw.cpa:
                best_cpa = kw.cpa
                break

    result = simulate(
        SimulationInput(
            current_spend=total_spend,
            current_conversions=total_conv,
            wasted_spend=wasted,
            best_efficient_cpa=best_cpa,
        )
    )

    db.add(
        OptimizationRun(
            account_id=account_id,
            current_cpa=result.current_cpa,
            projected_cpa=result.projected_cpa,
            current_conversions=int(round(result.current_conversions)),
            projected_conversions=int(round(result.projected_conversions)),
            total_waste_identified=result.monthly_saving,
        )
    )
    db.commit()

    return SimulationResponse(account_id=str(account_id), **asdict(result))
