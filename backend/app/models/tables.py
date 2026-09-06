"""SQLAlchemy ORM models.

Monetary values are stored as floats (rupees). Per 03_RULES.md section 6 money is
kept numeric end to end; currency formatting happens only at the display/message
layer, never here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base, new_uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    business_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    notify_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    campaigns: Mapped[list["Campaign"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0)

    account: Mapped[Account] = relationship(back_populates="campaigns")
    keywords: Mapped[list["Keyword"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    keyword: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_term: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0)
    # Derived metrics, persisted for convenience (recomputed on every upload).
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpa: Mapped[float | None] = mapped_column(Float, nullable=True)

    campaign: Mapped[Campaign] = relationship(back_populates="keywords")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    keyword_id: Mapped[str | None] = mapped_column(
        ForeignKey("keywords.id"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(8))
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    current_cpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_cpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_conversions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projected_conversions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_waste_identified: Mapped[float | None] = mapped_column(Float, nullable=True)


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    direction: Mapped[str] = mapped_column(String(8))  # OUTBOUND | INBOUND
    body: Mapped[str] = mapped_column(Text)
    related_recommendation_id: Mapped[str | None] = mapped_column(
        ForeignKey("recommendations.id"), nullable=True
    )
    provider_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class NotificationState(Base):
    """One row per account: what the last WhatsApp notification was about, so the
    scheduler can tell whether anything meaningfully new has appeared."""

    __tablename__ = "notification_state"

    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id"), primary_key=True
    )
    last_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_waste: Mapped[float | None] = mapped_column(Float, nullable=True)
    # newline-joined HIGH-severity keyword labels at the time of the last message
    last_high_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
