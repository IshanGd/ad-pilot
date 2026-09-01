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

    # Later phases — unused in Phase 1.
    llm_api_key: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_number: str | None = None

    @field_validator(
        "waste_cost_threshold",
        "llm_api_key",
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_whatsapp_number",
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
