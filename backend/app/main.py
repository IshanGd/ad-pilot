"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.db import init_db
from app.routes import analyze, upload, whatsapp

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()

    scheduler = None
    settings = get_settings()
    if settings.scheduler_enabled:
        from apscheduler.schedulers.background import BackgroundScheduler

        from app.models.db import SessionLocal
        from app.scheduler.jobs import run_all_checks

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            lambda: run_all_checks(SessionLocal),
            "interval",
            minutes=settings.scheduler_interval_minutes,
            id="whatsapp-notify",
        )
        scheduler.start()
        logger.info(
            "notification scheduler started (every %d min)",
            settings.scheduler_interval_minutes,
        )

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title="AdPilot API",
    version="0.1.0",
    summary="Instant Google Ads audit + WhatsApp monitoring for small businesses.",
    lifespan=lifespan,
)

# Frontend (Next.js) and the Chrome extension call this API from other origins.
_origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(whatsapp.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
