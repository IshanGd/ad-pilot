"""Application configuration, loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite by default so Phase 1 is runnable with no external services.
    # Deploy overrides this with a Postgres (Supabase) URL.
    database_url: str = "sqlite:///./adpilot.db"

    # Rule-engine knob (Phase 2). When None, computed per-account as
    # max(500, 5% of total account spend). See 03_RULES.md section 1.
    waste_cost_threshold: float | None = None

    # LLM explainer (Phase 4). When llm_api_key is unset the explainer falls back
    # to deterministic templates, so the audit still works with no LLM configured.
    llm_api_key: str | None = None
    llm_model: str = "claude-sonnet-5"
    explainer_enabled: bool = True

    # Twilio (Phase 5-6). When unset, WhatsApp send/opt-in still record state but
    # skip the outbound message.
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_number: str | None = None

    # Scheduler (Phase 5). Off by default — the demo uses POST /api/whatsapp/check.
    # When on, re-checks opted-in accounts on an interval and messages only on a
    # meaningful change (03_RULES.md section 4).
    scheduler_enabled: bool = False
    scheduler_interval_minutes: int = 60
    # Waste must move by more than this fraction since the last message to notify.
    notify_waste_change_threshold: float = 0.15

    # Inbound webhook (Phase 6). Signature validation is off by default because it
    # requires the exact public URL Twilio calls (a tunnel host, usually) — set
    # whatsapp_webhook_url to that when turning it on.
    whatsapp_validate_signature: bool = False
    whatsapp_webhook_url: str | None = None

    @field_validator(
        "waste_cost_threshold",
        "llm_api_key",
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_whatsapp_number",
        "whatsapp_webhook_url",
        mode="before",
    )
    @classmethod
    def _empty_string_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
