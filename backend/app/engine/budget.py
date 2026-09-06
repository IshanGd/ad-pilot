"""Budget reallocation across campaigns (05_DESIGN.md screen 4).

Rule-based: put more of the monthly budget behind campaigns that turn spend into
sales cheaply, and pull it away from campaigns with no sales. Pure functions.
"""
from __future__ import annotations

from dataclasses import dataclass

PAUSE = "PAUSE"
SCALE_UP = "SCALE_UP"
TRIM = "TRIM"
AVERAGE = "AVERAGE"

_REASON_EN = {
    PAUSE: "No sales from this campaign — move its budget elsewhere.",
    SCALE_UP: "Brings sales for well under your average cost — give it more.",
    TRIM: "Sales here cost more than your average — trim it back.",
    AVERAGE: "Performing about average.",
}


@dataclass(frozen=True)
class CampaignInput:
    campaign_id: str
    name: str
    spend: float
    conversions: float
    conversion_value: float


@dataclass(frozen=True)
class CampaignAllocation:
    campaign_id: str
    name: str
    current_spend: float
    current_share: float
    suggested_budget: float
    suggested_share: float
    delta: float
    cpa: float | None
    reason_code: str
    reason: str


def _cpa(spend: float, conversions: float) -> float | None:
    return spend / conversions if conversions else None


def _reason_code(cpa: float | None, conversions: float, avg_cpa: float | None) -> str:
    if conversions == 0:
        return PAUSE
    if avg_cpa and cpa is not None:
        if cpa < avg_cpa * 0.7:
            return SCALE_UP
        if cpa > avg_cpa * 1.3:
            return TRIM
    return AVERAGE


def optimize_budget(
    campaigns: list[CampaignInput],
    total_budget: float,
    account_avg_cpa: float | None,
) -> list[CampaignAllocation]:
    total_spend = sum(c.spend for c in campaigns)

    # Weight by value returned; campaigns with no sales get nothing.
    weights = [c.conversion_value if c.conversions > 0 else 0.0 for c in campaigns]
    if sum(weights) == 0:
        # Nothing converts anywhere — keep the current split rather than divide by 0.
        weights = [c.spend for c in campaigns] or [1.0]
    weight_total = sum(weights) or 1.0

    raw = [round(total_budget * w / weight_total) for w in weights]
    # Fix rounding drift onto the largest allocation.
    drift = round(total_budget) - sum(raw)
    if raw:
        raw[raw.index(max(raw))] += drift

    out: list[CampaignAllocation] = []
    for c, suggested in zip(campaigns, raw):
        cpa = _cpa(c.spend, c.conversions)
        code = _reason_code(cpa, c.conversions, account_avg_cpa)
        out.append(
            CampaignAllocation(
                campaign_id=c.campaign_id,
                name=c.name,
                current_spend=round(c.spend, 2),
                current_share=(c.spend / total_spend) if total_spend else 0.0,
                suggested_budget=float(suggested),
                suggested_share=(suggested / total_budget) if total_budget else 0.0,
                delta=round(suggested - c.spend, 2),
                cpa=round(cpa, 2) if cpa is not None else None,
                reason_code=code,
                reason=_REASON_EN[code],
            )
        )
    # Biggest suggested budget first.
    out.sort(key=lambda a: a.suggested_budget, reverse=True)
    return out
