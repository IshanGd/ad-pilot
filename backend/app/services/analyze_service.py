"""Run the rule engine over a stored account and persist recommendations.

Route handlers call these functions; all the rule logic lives in
``engine/rules.py`` and the plain-language text in ``engine/explainer.py`` —
both stay independently testable (03_RULES.md section 6).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.explainer import explain, normalize_language
from app.engine.metrics import KeywordStats, account_averages, keyword_metrics
from app.engine.rules import KeywordRow, analyze_keywords, total_waste_identified
from app.models.tables import Account, Campaign, Keyword, Recommendation
from app.schemas import (
    AnalyzeResponse,
    RecommendationOut,
    RecommendationsResponse,
)

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
_WASTE_TYPES = {"PAUSE_KEYWORD", "ADD_NEGATIVE"}


def _load_account(db: Session, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise LookupError(f"Unknown account_id: {account_id}")
    return account


def _keyword_label(kw: Keyword) -> str:
    return (kw.keyword or kw.search_term or "(unnamed keyword)").strip()


def run_analysis(
    db: Session,
    account_id: str,
    *,
    configured_threshold: float | None = None,
    language: str | None = None,
) -> AnalyzeResponse:
    """Recompute recommendations for an account, replacing any previous run.

    When ``language`` is given it overrides (and is saved back to) the account's
    ``preferred_language``.
    """
    account = _load_account(db, account_id)

    lang = normalize_language(language or account.preferred_language)
    if language is not None and lang != account.preferred_language:
        account.preferred_language = lang

    campaigns = db.scalars(
        select(Campaign).where(Campaign.account_id == account_id)
    ).all()
    campaign_names = {str(c.id): c.name for c in campaigns}
    campaign_ids = [c.id for c in campaigns]

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
            keyword_id=str(kw.id),
            campaign_id=str(kw.campaign_id),
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

    # Plain-language text. Every number is verified against the rule input before
    # use; anything that fails falls back to a template (engine/explainer.py).
    explained = explain(rule_recs, lang)

    def _text(r) -> str:
        e = explained.by_ref.get(r.keyword_id)
        return e.text if e is not None else r.explanation

    sources = {ref: e.source for ref, e in explained.by_ref.items()}

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
            explanation=_text(r),
            confidence=r.confidence,
            estimated_impact=r.estimated_impact,
            status="PENDING",
        )
        for r in rule_recs
    ]
    db.add_all(orm_recs)
    db.commit()

    labels = {str(r.keyword_id): r.label for r in rule_recs}
    out = _to_out(orm_recs, campaign_names, labels, sources)
    base = _aggregate(account_id, lang, out, total_waste_identified(rule_recs))
    return AnalyzeResponse(
        analyzed_keywords=len(rows),
        llm_explanations=explained.llm_count,
        **base.model_dump(),
    )


def get_recommendations(db: Session, account_id: str) -> RecommendationsResponse:
    account = _load_account(db, account_id)

    rows = db.execute(
        select(Recommendation, Campaign, Keyword)
        .join(Campaign, Recommendation.campaign_id == Campaign.id)
        .join(Keyword, Recommendation.keyword_id == Keyword.id, isouter=True)
        .where(Campaign.account_id == account_id)
    ).all()

    campaign_names = {str(c.id): c.name for _, c, _ in rows}
    labels = {
        str(rec.keyword_id): _keyword_label(kw)
        for rec, _, kw in rows
        if kw is not None
    }
    recs = [rec for rec, _, _ in rows]
    out = _to_out(recs, campaign_names, labels, sources=None)

    waste = sum(
        r.estimated_impact or 0.0 for r in recs if r.type in _WASTE_TYPES
    )
    return _aggregate(
        account_id, normalize_language(account.preferred_language), out, waste
    )


def _to_out(
    recs: list[Recommendation],
    campaign_names: dict[str, str],
    labels: dict[str, str],
    sources: dict[str, str] | None,
) -> list[RecommendationOut]:
    items = [
        RecommendationOut(
            id=str(r.id),
            campaign_id=str(r.campaign_id),
            campaign_name=campaign_names.get(str(r.campaign_id), ""),
            keyword_id=str(r.keyword_id) if r.keyword_id is not None else None,
            label=labels.get(str(r.keyword_id), ""),
            type=r.type,
            severity=r.severity,
            confidence=r.confidence,
            estimated_impact=r.estimated_impact,
            explanation=r.explanation,
            explanation_source=(
                sources.get(str(r.keyword_id), "template")
                if sources is not None
                else "stored"
            ),
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
    account_id: str,
    language: str,
    out: list[RecommendationOut],
    waste: float,
) -> RecommendationsResponse:
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for r in out:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_type[r.type] = by_type.get(r.type, 0) + 1
    return RecommendationsResponse(
        account_id=account_id,
        language=language,
        total_waste_identified=round(waste, 2),
        recommendation_count=len(out),
        by_severity=by_severity,
        by_type=by_type,
        recommendations=out,
    )
