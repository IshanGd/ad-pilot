"""Run the rule engine over a stored account and persist recommendations.

Route handlers call these functions; all the rule logic lives in
``engine/rules.py`` and stays independently testable (03_RULES.md section 6).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.metrics import KeywordStats, account_averages, keyword_metrics
from app.engine.rules import (
    KeywordRow,
    Recommendation as RuleRecommendation,
    analyze_keywords,
    total_waste_identified,
)
from app.models.tables import Account, Campaign, Keyword, Recommendation
from app.schemas import (
    AnalyzeResponse,
    RecommendationOut,
    RecommendationsResponse,
)

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _load_account(db: Session, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise LookupError(f"Unknown account_id: {account_id}")
    return account


def _keyword_label(kw: Keyword) -> str:
    return (kw.keyword or kw.search_term or "(unnamed keyword)").strip()


def run_analysis(
    db: Session, account_id: str, *, configured_threshold: float | None = None
) -> AnalyzeResponse:
    """Recompute recommendations for an account, replacing any previous run."""
    _load_account(db, account_id)

    campaigns = db.scalars(
        select(Campaign).where(Campaign.account_id == account_id)
    ).all()
    campaign_names = {c.id: c.name for c in campaigns}
    campaign_ids = list(campaign_names)

    keywords: list[Keyword] = []
    if campaign_ids:
        keywords = list(
            db.scalars(
                select(Keyword).where(Keyword.campaign_id.in_(campaign_ids))
            ).all()
        )

    stats_by_keyword = {
        kw.id: KeywordStats(
            impressions=kw.impressions,
            clicks=kw.clicks,
            spend=kw.spend,
            conversions=kw.conversions,
            conversion_value=kw.conversion_value,
        )
        for kw in keywords
    }
    averages = account_averages(stats_by_keyword.values())

    rows = [
        KeywordRow(
            keyword_id=kw.id,
            campaign_id=kw.campaign_id,
            label=_keyword_label(kw),
            search_term=kw.search_term,
            stats=stats_by_keyword[kw.id],
            metrics=keyword_metrics(stats_by_keyword[kw.id]),
        )
        for kw in keywords
    ]

    rule_recs = analyze_keywords(
        rows, averages, configured_threshold=configured_threshold
    )

    # Replace the previous run for this account.
    if campaign_ids:
        db.query(Recommendation).filter(
            Recommendation.campaign_id.in_(campaign_ids)
        ).delete(synchronize_session=False)

    orm_recs = [
        Recommendation(
            campaign_id=r.campaign_id,
            keyword_id=r.keyword_id,
            type=r.type,
            severity=r.severity,
            explanation=r.explanation,
            confidence=r.confidence,
            estimated_impact=r.estimated_impact,
            status="PENDING",
        )
        for r in rule_recs
    ]
    db.add_all(orm_recs)
    db.commit()

    labels = {r.keyword_id: r.label for r in rule_recs}
    out = _to_out(orm_recs, campaign_names, labels)
    base = _aggregate(account_id, out, total_waste_identified(rule_recs))
    return AnalyzeResponse(analyzed_keywords=len(rows), **base.model_dump())


def get_recommendations(db: Session, account_id: str) -> RecommendationsResponse:
    _load_account(db, account_id)

    rows = db.execute(
        select(Recommendation, Campaign, Keyword)
        .join(Campaign, Recommendation.campaign_id == Campaign.id)
        .join(Keyword, Recommendation.keyword_id == Keyword.id, isouter=True)
        .where(Campaign.account_id == account_id)
    ).all()

    campaign_names = {c.id: c.name for _, c, _ in rows}
    labels = {
        rec.keyword_id: _keyword_label(kw)
        for rec, _, kw in rows
        if kw is not None
    }
    recs = [rec for rec, _, _ in rows]
    out = _to_out(recs, campaign_names, labels)

    waste = sum(
        r.estimated_impact or 0.0
        for r in recs
        if r.type in {"PAUSE_KEYWORD", "ADD_NEGATIVE"}
    )
    return _aggregate(account_id, out, waste)


def _to_out(
    recs: list[Recommendation],
    campaign_names: dict[str, str],
    labels: dict[str, str],
) -> list[RecommendationOut]:
    items = [
        RecommendationOut(
            id=r.id,
            campaign_id=r.campaign_id,
            campaign_name=campaign_names.get(r.campaign_id, ""),
            keyword_id=r.keyword_id,
            label=labels.get(r.keyword_id, ""),
            type=r.type,
            severity=r.severity,
            confidence=r.confidence,
            estimated_impact=r.estimated_impact,
            explanation=r.explanation,
            status=r.status,
        )
        for r in recs
    ]
    items.sort(
        key=lambda r: (
            _SEVERITY_RANK.get(r.severity, 9),
            -(r.estimated_impact or 0.0),
            r.label.lower(),
        )
    )
    return items


def _aggregate(
    account_id: str, out: list[RecommendationOut], waste: float
) -> RecommendationsResponse:
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for r in out:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_type[r.type] = by_type.get(r.type, 0) + 1
    return RecommendationsResponse(
        account_id=account_id,
        total_waste_identified=round(waste, 2),
        recommendation_count=len(out),
        by_severity=by_severity,
        by_type=by_type,
        recommendations=out,
    )
