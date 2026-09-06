"""WhatsApp opt-in + outbound delivery (Phase 5) and inbound replies (Phase 6).

Confidence ladder (03_RULES.md section 4): opt-in is only ever reached from the
audit result screen, is an explicit action, and is never assumed. Inbound replies
(PAUSE / DETAILS / SCALE) act on the last recommendation the number was messaged
about; the Google Ads mutation is simulated.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.engine.explainer import normalize_language
from app.models.db import get_db
from app.models.tables import Account, WhatsAppMessage
from app.schemas import (
    CheckRequest,
    CheckResponse,
    OptInRequest,
    OptInResponse,
    SendRequest,
    SendResponse,
    SimulateReplyRequest,
    SimulateReplyResponse,
)
from app.scheduler.jobs import message_from_current_audit, run_notification_check
from app.services.reply_service import handle_inbound
from app.services.whatsapp_service import (
    WhatsAppNotConfigured,
    WhatsAppSendError,
    display_number,
    normalize_number,
    send_whatsapp,
    whatsapp_configured,
)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


def _account(db: Session, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown account_id: {account_id}",
        )
    return account


def _confirmation_text(language: str, business_name: str | None) -> str:
    who = f" {business_name}" if business_name else ""
    if language == "hi":
        return (
            f"AdPilot अब आपके साथ है{who}। हम इस नंबर पर सिर्फ़ तभी संदेश भेजेंगे "
            f"जब आपके विज्ञापनों में कुछ ध्यान देने लायक हो — और कभी नहीं।"
        )
    return (
        f"You're set up with AdPilot{who}. We'll message this number only when "
        f"something about your ads needs attention — never otherwise."
    )


@router.post("/opt-in", response_model=OptInResponse, summary="Opt in to WhatsApp updates")
def opt_in(body: OptInRequest, db: Session = Depends(get_db)) -> OptInResponse:
    account = _account(db, body.account_id)

    try:
        normalized = normalize_number(body.phone_number)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    account.phone_number = display_number(normalized)
    account.notify_opt_in = True
    if body.language:
        account.preferred_language = normalize_language(body.language)
    db.commit()

    confirmation_sent = False
    warning: str | None = None
    if whatsapp_configured():
        text = _confirmation_text(account.preferred_language, account.business_name)
        try:
            sid = send_whatsapp(account.phone_number, text)
            db.add(
                WhatsAppMessage(
                    account_id=account.id,
                    direction="OUTBOUND",
                    body=text,
                    provider_sid=sid,
                )
            )
            db.commit()
            confirmation_sent = True
        except WhatsAppSendError as exc:
            warning = (
                f"Saved, but we couldn't reach that number ({exc}). Make sure it "
                f"has sent the WhatsApp sandbox join message first."
            )
    else:
        warning = "Saved. WhatsApp isn't configured on the server, so no message was sent."

    return OptInResponse(
        account_id=str(account.id),
        phone_number=account.phone_number,
        notify_opt_in=True,
        preferred_language=account.preferred_language,
        confirmation_sent=confirmation_sent,
        warning=warning,
    )


@router.post("/send", response_model=SendResponse, summary="Send an outbound WhatsApp message")
def send(body: SendRequest, db: Session = Depends(get_db)) -> SendResponse:
    account = _account(db, body.account_id)
    if not account.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No phone number on file for this account — opt in first.",
        )

    text = body.body
    rec_id = body.related_recommendation_id
    if not text:
        text, rec_id = message_from_current_audit(db, account.id)
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to send yet — run an audit for this account first.",
        )

    try:
        sid = send_whatsapp(account.phone_number, text)
    except WhatsAppNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except WhatsAppSendError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    db.add(
        WhatsAppMessage(
            account_id=account.id,
            direction="OUTBOUND",
            body=text,
            related_recommendation_id=rec_id,
            provider_sid=sid,
        )
    )
    db.commit()
    return SendResponse(account_id=str(account.id), provider_sid=sid, body=text)


@router.post(
    "/check",
    response_model=CheckResponse,
    summary="Re-check an account and message it only if something changed",
)
def check(body: CheckRequest, db: Session = Depends(get_db)) -> CheckResponse:
    account = _account(db, body.account_id)
    outcome = run_notification_check(db, account, force=body.force)
    return CheckResponse(**outcome.as_dict())


def _twiml(text: str) -> Response:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(text)}</Message></Response>"
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/webhook", summary="Twilio inbound WhatsApp webhook (PAUSE / DETAILS / SCALE)")
async def webhook(request: Request, db: Session = Depends(get_db)) -> Response:
    form = await request.form()
    data = {k: str(v) for k, v in form.items()}

    settings = get_settings()
    if settings.whatsapp_validate_signature:
        from twilio.request_validator import RequestValidator

        validator = RequestValidator(settings.twilio_auth_token or "")
        url = settings.whatsapp_webhook_url or str(request.url)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(url, data, signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )

    result = handle_inbound(db, data.get("From", ""), data.get("Body", ""))
    return _twiml(result.reply_text)


@router.post(
    "/simulate-reply",
    response_model=SimulateReplyResponse,
    summary="Run the reply handler without Twilio (demo / testing)",
)
def simulate_reply(
    body: SimulateReplyRequest, db: Session = Depends(get_db)
) -> SimulateReplyResponse:
    from_number = body.from_number
    if not from_number and body.account_id:
        account = _account(db, body.account_id)
        from_number = account.phone_number or ""
    result = handle_inbound(db, from_number or "", body.body)
    return SimulateReplyResponse(
        reply_text=result.reply_text,
        keyword=result.keyword,
        account_id=result.account_id,
        recommendation_id=result.recommendation_id,
        action_taken=result.action_taken,
    )
