"""Rule-based recommendation engine (03_RULES.md section 1).

Pure functions only — no DB, no I/O, no LLM. Given the per-keyword stats/metrics
already computed by ``engine/metrics.py`` plus the account-wide averages, decide
which single recommendation (if any) applies to each keyword, in the fixed
priority order from the rules doc.

The ``explanation`` produced here is a deterministic template built straight from
the input numbers. Phase 4 replaces it with a validated LLM explanation; until
then it is what the API and WhatsApp layer show.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.metrics import AccountAverages, KeywordMetrics, KeywordStats

# Recommendation type constants (mirror the CHECK values in schema.sql / arch doc).
PAUSE_KEYWORD = "PAUSE_KEYWORD"
INCREASE_BUDGET = "INCREASE_BUDGET"
ADD_NEGATIVE = "ADD_NEGATIVE"
REVIEW_LOW_CTR = "REVIEW_LOW_CTR"

# Types whose estimated_impact counts toward the headline "money wasted" number.
WASTE_TYPES = frozenset({PAUSE_KEYWORD, ADD_NEGATIVE})

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

_MIN_WASTE_THRESHOLD = 500.0
_WASTE_THRESHOLD_SPEND_FRACTION = 0.05


@dataclass(frozen=True)
class KeywordRow:
    """One keyword/search-term row to be evaluated."""

    keyword_id: str
    campaign_id: str
    label: str  # keyword text (falls back to search term) — for display
    search_term: str | None
    stats: KeywordStats
    metrics: KeywordMetrics


@dataclass(frozen=True)
class Recommendation:
    keyword_id: str
    campaign_id: str
    label: str
    type: str
    severity: str
    confidence: float
    estimated_impact: float | None
    explanation: str
    # The numbers that triggered the rule — fed to the Phase 4 LLM explainer as
    # structured JSON (never raw CSV rows). See 03_RULES.md section 3.
    signals: dict[str, float] = field(default_factory=dict)


def waste_cost_threshold(
    total_account_spend: float, configured: float | None = None
) -> float:
    """₹ spend on a zero-conversion keyword that counts as "meaningful waste".

    Configurable per 03_RULES.md section 1; defaults to the greater of ₹500 or
    5% of total account spend.
    """
    if configured is not None:
        return configured
    return max(_MIN_WASTE_THRESHOLD, _WASTE_THRESHOLD_SPEND_FRACTION * total_account_spend)


def evaluate_keyword(
    row: KeywordRow, averages: AccountAverages, threshold: float
) -> Recommendation | None:
    """Apply the rules in priority order. Returns at most one recommendation."""
    stats = row.stats
    metrics = row.metrics
    conversions = stats.conversions
    clicks = stats.clicks
    spend = stats.spend

    avg_cpa = averages.cpa
    avg_ctr = averages.ctr

    if conversions == 0 and spend > threshold:
        confidence = 0.9 if clicks > 20 else 0.7
        return _make(
            row,
            PAUSE_KEYWORD,
            "HIGH",
            confidence,
            estimated_impact=spend,
            explanation=(
                f"This search term cost {_rupees(spend)} over {_int(clicks)} clicks "
                f"and brought in no sales. Pausing it stops that spend."
            ),
            signals={"spend": spend, "clicks": float(clicks), "conversions": 0.0},
        )

    if (
        avg_cpa is not None
        and metrics.cpa is not None
        and metrics.cpa < avg_cpa * 0.7
        and conversions >= 3
    ):
        surplus = max(0.0, (avg_cpa - metrics.cpa) * conversions)
        return _make(
            row,
            INCREASE_BUDGET,
            "MEDIUM",
            0.8,
            estimated_impact=surplus or None,
            explanation=(
                f"This keyword brings sales at {_rupees(metrics.cpa)} each, well below "
                f"your account average of {_rupees(avg_cpa)}. It is performing — giving "
                f"it more budget should bring more sales at a similar cost."
            ),
            signals={
                "spend": spend,
                "conversions": float(conversions),
                "cost_per_sale": metrics.cpa,
                "account_avg_cost_per_sale": avg_cpa,
            },
        )

    if clicks > 20 and conversions == 0:
        return _make(
            row,
            ADD_NEGATIVE,
            "MEDIUM",
            0.75,
            estimated_impact=spend,
            explanation=(
                f"“{row.search_term or row.label}” got {_int(clicks)} clicks "
                f"and no sales — these searches are not your buyers. Add it as a "
                f"negative keyword so you stop paying for them."
            ),
            signals={"spend": spend, "clicks": float(clicks), "conversions": 0.0},
        )

    if (
        avg_ctr is not None
        and metrics.ctr is not None
        and metrics.ctr < avg_ctr * 0.5
        and stats.impressions > 500
    ):
        return _make(
            row,
            REVIEW_LOW_CTR,
            "LOW",
            0.6,
            estimated_impact=None,
            explanation=(
                f"Very few people who see this keyword click it "
                f"({_int(stats.clicks)} clicks from {_int(stats.impressions)} views). "
                f"Worth reviewing the ad wording or the keyword itself."
            ),
            signals={
                "clicks": float(stats.clicks),
                "impressions": float(stats.impressions),
            },
        )

    return None


def analyze_keywords(
    rows: list[KeywordRow],
    averages: AccountAverages,
    *,
    configured_threshold: float | None = None,
) -> list[Recommendation]:
    """Evaluate every row and return recommendations, ranked for display.

    Ranking: severity (HIGH → LOW), then estimated impact (largest ₹ first),
    then keyword label for stability.
    """
    threshold = waste_cost_threshold(averages.total_spend, configured_threshold)
    recs = [
        rec
        for row in rows
        if (rec := evaluate_keyword(row, averages, threshold)) is not None
    ]
    recs.sort(
        key=lambda r: (
            _SEVERITY_RANK.get(r.severity, 9),
            -(r.estimated_impact or 0.0),
            r.label.lower(),
        )
    )
    return recs


def total_waste_identified(recs: list[Recommendation]) -> float:
    """Headline number: ₹ currently spent on things that should stop."""
    return sum(
        r.estimated_impact or 0.0 for r in recs if r.type in WASTE_TYPES
    )


def _make(
    row: KeywordRow,
    type_: str,
    severity: str,
    confidence: float,
    *,
    estimated_impact: float | None,
    explanation: str,
    signals: dict[str, float],
) -> Recommendation:
    return Recommendation(
        keyword_id=row.keyword_id,
        campaign_id=row.campaign_id,
        label=row.label,
        type=type_,
        severity=severity,
        confidence=confidence,
        estimated_impact=estimated_impact,
        explanation=explanation,
        signals=signals,
    )


def _rupees(value: float) -> str:
    return f"₹{round(value):,}"


def _int(value: float) -> str:
    return f"{int(round(value)):,}"
