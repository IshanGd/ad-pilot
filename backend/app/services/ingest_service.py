"""Persist a ParsedReport into accounts / campaigns / keywords."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.engine.ingest import ParsedReport
from app.models.tables import Account, Campaign, Keyword
from app.schemas import (
    AccountAveragesOut,
    CampaignSummary,
    Totals,
    UploadResponse,
)


def store_report(
    db: Session,
    report: ParsedReport,
    *,
    account_id: str | None = None,
    business_name: str | None = None,
    preferred_language: str = "en",
) -> UploadResponse:
    """Create (or reuse) an account and replace its campaign/keyword data.

    Re-uploading for the same ``account_id`` clears the previous campaigns so the
    audit always reflects the latest report.
    """
    if account_id:
        account = db.get(Account, account_id)
        if account is None:
            raise LookupError(f"Unknown account_id: {account_id}")
        account.campaigns.clear()
        db.flush()
    else:
        account = Account(
            business_name=business_name,
            preferred_language=preferred_language,
        )
        db.add(account)
        db.flush()

    if business_name:
        account.business_name = business_name

    rows_by_campaign: dict[str, list] = defaultdict(list)
    for row in report.rows:
        rows_by_campaign[row.campaign].append(row)

    summaries: list[CampaignSummary] = []
    for name, rows in rows_by_campaign.items():
        campaign = Campaign(
            account_id=account.id,
            name=name,
            spend=sum(r.stats.spend for r in rows),
            impressions=sum(r.stats.impressions for r in rows),
            clicks=sum(r.stats.clicks for r in rows),
            conversions=sum(r.stats.conversions for r in rows),
            conversion_value=sum(r.stats.conversion_value for r in rows),
        )
        db.add(campaign)
        db.flush()

        for r in rows:
            db.add(
                Keyword(
                    campaign_id=campaign.id,
                    keyword=r.keyword,
                    search_term=r.search_term,
                    match_type=r.match_type,
                    impressions=r.stats.impressions,
                    clicks=r.stats.clicks,
                    spend=r.stats.spend,
                    conversions=r.stats.conversions,
                    conversion_value=r.stats.conversion_value,
                    ctr=r.metrics.ctr,
                    cpc=r.metrics.cpc,
                    cpa=r.metrics.cpa,
                )
            )

        summaries.append(
            CampaignSummary(
                id=str(campaign.id),
                name=name,
                spend=campaign.spend,
                impressions=campaign.impressions,
                clicks=campaign.clicks,
                conversions=campaign.conversions,
                conversion_value=campaign.conversion_value,
                keyword_count=len(rows),
            )
        )

    db.commit()

    avg = report.averages
    return UploadResponse(
        account_id=str(account.id),
        campaigns=len(summaries),
        keywords=len(report.rows),
        rows_ingested=len(report.rows),
        totals=Totals(
            spend=avg.total_spend,
            impressions=avg.total_impressions,
            clicks=avg.total_clicks,
            conversions=avg.total_conversions,
            conversion_value=avg.total_conversion_value,
        ),
        account_averages=AccountAveragesOut(
            ctr=avg.ctr, cpc=avg.cpc, cvr=avg.cvr, cpa=avg.cpa, roas=avg.roas
        ),
        campaign_breakdown=sorted(summaries, key=lambda c: c.spend, reverse=True),
    )
