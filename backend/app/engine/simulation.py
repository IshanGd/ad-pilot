"""Current vs projected impact (05_DESIGN.md screen 5).

Always framed as "projected impact, not a guarantee". Pure functions.

Model: the money currently spent on keywords with no sales is either
 - reinvested into the best-performing keyword at its current cost per sale, or
 - simply saved (when there's no clearly efficient keyword to move it to).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationInput:
    current_spend: float
    current_conversions: float
    wasted_spend: float  # spend on zero-sale keywords (PAUSE + ADD_NEGATIVE)
    best_efficient_cpa: float | None  # cost per sale of the top scale-up keyword


@dataclass(frozen=True)
class SimulationResult:
    current_spend: float
    current_conversions: float
    current_cpa: float | None
    projected_spend: float
    projected_conversions: float
    projected_cpa: float | None
    monthly_saving: float
    extra_sales: float
    reinvested: bool
    assumptions: list[str]


def _cpa(spend: float, conversions: float) -> float | None:
    return spend / conversions if conversions else None


def simulate(inp: SimulationInput) -> SimulationResult:
    current_cpa = _cpa(inp.current_spend, inp.current_conversions)
    waste = max(0.0, inp.wasted_spend)

    reinvest = bool(waste > 0 and inp.best_efficient_cpa and inp.best_efficient_cpa > 0)

    if reinvest:
        extra = waste / inp.best_efficient_cpa  # type: ignore[operator]
        projected_spend = inp.current_spend
        projected_conversions = inp.current_conversions + extra
        assumptions = [
            f"The ₹{round(waste):,} now spent on keywords with no sales is moved "
            f"to your best-performing keyword.",
            f"That keyword keeps bringing sales at about "
            f"₹{round(inp.best_efficient_cpa):,} each.",  # type: ignore[arg-type]
            "Projected impact, not a guarantee.",
        ]
    else:
        extra = 0.0
        projected_spend = max(0.0, inp.current_spend - waste)
        projected_conversions = inp.current_conversions
        assumptions = [
            f"You stop spending ₹{round(waste):,}/month on keywords with no sales.",
            "Everything else stays the same.",
            "Projected impact, not a guarantee.",
        ]

    return SimulationResult(
        current_spend=round(inp.current_spend, 2),
        current_conversions=round(inp.current_conversions, 2),
        current_cpa=round(current_cpa, 2) if current_cpa is not None else None,
        projected_spend=round(projected_spend, 2),
        projected_conversions=round(projected_conversions, 2),
        projected_cpa=(
            round(_cpa(projected_spend, projected_conversions), 2)
            if projected_conversions
            else None
        ),
        monthly_saving=round(waste, 2),
        extra_sales=round(extra, 2),
        reinvested=reinvest,
        assumptions=assumptions,
    )
