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
    # Optional per-run override of the account's preferred_language ("en" | "hi").
    # When set it is also saved back to the account. 03_RULES.md section 5.
    language: str | None = None


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
    explanation_source: str | None = None  # "llm" | "template" | "stored"
    status: str


class RecommendationsResponse(BaseModel):
    account_id: str
    language: str
    total_waste_identified: float
    recommendation_count: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    recommendations: list[RecommendationOut]


class AnalyzeResponse(RecommendationsResponse):
    analyzed_keywords: int
    llm_explanations: int  # how many explanations came from the LLM (rest are templates)


# --- Phase 5: WhatsApp opt-in + delivery ---------------------------------


class OptInRequest(BaseModel):
    account_id: str
    phone_number: str
    language: str | None = None


class OptInResponse(BaseModel):
    account_id: str
    phone_number: str
    notify_opt_in: bool
    preferred_language: str
    confirmation_sent: bool
    warning: str | None = None


class SendRequest(BaseModel):
    account_id: str
    # When omitted, the message is built from the account's current audit.
    body: str | None = None
    related_recommendation_id: str | None = None


class SendResponse(BaseModel):
    account_id: str
    provider_sid: str
    body: str


class CheckRequest(BaseModel):
    account_id: str
    force: bool = False  # send regardless of whether anything changed (demo)


class CheckResponse(BaseModel):
    account_id: str
    sent: bool
    reason: str
    body: str | None = None
    provider_sid: str | None = None
    would_send: str | None = None  # message that would go out if Twilio were set


class SimulateReplyRequest(BaseModel):
    body: str
    from_number: str | None = None
    account_id: str | None = None  # alternative to from_number


class SimulateReplyResponse(BaseModel):
    reply_text: str
    keyword: str | None
    account_id: str | None
    recommendation_id: str | None
    action_taken: bool
