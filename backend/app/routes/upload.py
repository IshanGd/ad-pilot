"""POST /api/campaign/upload — accept a Google Ads CSV, validate, store."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.engine.ingest import CSVValidationError, parse_report
from app.models.db import get_db
from app.schemas import UploadResponse
from app.services.ingest_service import store_report

router = APIRouter(prefix="/api/campaign", tags=["campaign"])

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB — reports in scope are a few hundred rows


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a Google Ads CSV export",
)
async def upload_campaign_csv(
    file: UploadFile = File(...),
    account_id: str | None = Form(default=None),
    business_name: str | None = Form(default=None),
    preferred_language: str = Form(default="en"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    filename = (file.filename or "").lower()
    if filename and not filename.endswith((".csv", ".tsv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a .csv file exported from Google Ads.",
        )

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is larger than 5 MB.",
        )

    try:
        report = parse_report(raw)
    except CSVValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        return store_report(
            db,
            report,
            account_id=account_id,
            business_name=business_name,
            preferred_language=preferred_language,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
