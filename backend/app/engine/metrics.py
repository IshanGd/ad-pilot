"""Per-keyword and account-wide advertising metrics.

Formulas are fixed by 03_RULES.md section 1:

    CTR  = Clicks / Impressions
    CPC  = Cost / Clicks
    CVR  = Conversions / Clicks
    CPA  = Cost / Conversions          (None if Conversions == 0)
    ROAS = Conversion_Value / Cost

Account-wide values are the *aggregate* ratios (sum of numerators over sum of
denominators), not the mean of per-keyword ratios — they are the baseline the
rule engine compares individual keywords against.

Pure functions only. No DB, no I/O.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def _safe_div(numerator: float, denominator: float) -> float | None:
    """Divide, returning None when the denominator is zero/missing."""
    if not denominator:
        return None
    return numerator / denominator


@dataclass(frozen=True)
class KeywordMetrics:
    ctr: float | None
    cpc: float | None
    cvr: float | None
    cpa: float | None
    roas: float | None


@dataclass(frozen=True)
class KeywordStats:
    """Raw counts for one keyword/search-term row."""

    impressions: int
    clicks: int
    spend: float
    conversions: float
    conversion_value: float = 0.0


@dataclass(frozen=True)
class AccountAverages:
    ctr: float | None
    cpc: float | None
    cvr: float | None
    cpa: float | None
    roas: float | None
    total_impressions: int
    total_clicks: int
    total_spend: float
    total_conversions: float
    total_conversion_value: float


def keyword_metrics(stats: KeywordStats) -> KeywordMetrics:
    return KeywordMetrics(
        ctr=_safe_div(stats.clicks, stats.impressions),
        cpc=_safe_div(stats.spend, stats.clicks),
        cvr=_safe_div(stats.conversions, stats.clicks),
        cpa=_safe_div(stats.spend, stats.conversions),
        roas=_safe_div(stats.conversion_value, stats.spend),
    )


def account_averages(rows: Iterable[KeywordStats]) -> AccountAverages:
    rows = list(rows)
    total_impressions = sum(r.impressions for r in rows)
    total_clicks = sum(r.clicks for r in rows)
    total_spend = sum(r.spend for r in rows)
    total_conversions = sum(r.conversions for r in rows)
    total_conversion_value = sum(r.conversion_value for r in rows)

    return AccountAverages(
        ctr=_safe_div(total_clicks, total_impressions),
        cpc=_safe_div(total_spend, total_clicks),
        cvr=_safe_div(total_conversions, total_clicks),
        cpa=_safe_div(total_spend, total_conversions),
        roas=_safe_div(total_conversion_value, total_spend),
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_spend=total_spend,
        total_conversions=total_conversions,
        total_conversion_value=total_conversion_value,
    )
