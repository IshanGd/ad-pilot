"""Pydantic request/response models for the API (03_RULES.md section 6)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Totals(BaseModel):
    spend: float
    impressions: int
    clicks: int
    conversions: float
    conversion_value: float


class AccountAveragesOut(BaseModel):
    ctr: float | None
    cpc: float | None
    cvr: float | None
    cpa: float | None
    roas: float | None


class CampaignSummary(BaseModel):
    id: str
    name: str
    spend: float
    impressions: int
    clicks: int
    conversions: float
    conversion_value: float
    keyword_count: int


class UploadResponse(BaseModel):
    account_id: str
    campaigns: int
    keywords: int
    rows_ingested: int
    totals: Totals
    account_averages: AccountAveragesOut
    campaign_breakdown: list[CampaignSummary]


class ErrorResponse(BaseModel):
    detail: str
    missing_columns: list[str] = Field(default_factory=list)


# --- Phase 2: recommendation engine ---------------------------------------


class AnalyzeRequest(BaseModel):
    account_id: str


class RecommendationOut(BaseModel):
    id: str
    campaign_id: str
    campaign_name: str
    keyword_id: str | None
    label: str
    type: str
    severity: str
    confidence: float | None
    estimated_impact: float | None
    explanation: str | None
    status: str


class RecommendationsResponse(BaseModel):
    account_id: str
    total_waste_identified: float
    recommendation_count: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    recommendations: list[RecommendationOut]


class AnalyzeResponse(RecommendationsResponse):
    analyzed_keywords: int
