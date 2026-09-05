"""Thin Twilio WhatsApp wrapper — the only place the Twilio SDK is touched.

When Twilio is not configured the rest of Phase 5 still works: opt-in is recorded
and the scheduler logic runs, the outbound message is just skipped.
"""
from __future__ import annotations

import logging
import re

from app.config import get_settings

logger = logging.getLogger(__name__)

_DIGITS = re.compile(r"\d+")


class WhatsAppNotConfigured(RuntimeError):
    """Raised when a send is attempted with no Twilio credentials."""


class WhatsAppSendError(RuntimeError):
    """Twilio rejected the outbound message."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


def whatsapp_configured() -> bool:
    s = get_settings()
    return bool(
        s.twilio_account_sid and s.twilio_auth_token and s.twilio_whatsapp_number
    )


def normalize_number(raw: str) -> str:
    """'+91 82965 46656', '8296546656', 'whatsapp:+91...' -> 'whatsapp:+918296546656'."""
    raw = (raw or "").strip()
    if raw.startswith("whatsapp:"):
        raw = raw[len("whatsapp:") :].strip()
    digits = "".join(_DIGITS.findall(raw))
    if not digits:
        raise ValueError("No digits in phone number.")
    # Assume an India number if no country code was given (10 digits).
    if len(digits) == 10:
        digits = "91" + digits
    if not (10 <= len(digits) <= 15):
        raise ValueError("Phone number does not look valid.")
    return f"whatsapp:+{digits}"


def display_number(normalized: str) -> str:
    """'whatsapp:+918296546656' -> '+918296546656' (what we store on the account)."""
    return normalized.removeprefix("whatsapp:")


def send_whatsapp(to: str, body: str) -> str:
    """Send one WhatsApp message. Returns the Twilio message SID."""
    s = get_settings()
    if not whatsapp_configured():
        raise WhatsAppNotConfigured("Twilio credentials are not set.")

    from twilio.base.exceptions import TwilioRestException
    from twilio.rest import Client

    client = Client(s.twilio_account_sid, s.twilio_auth_token)
    from_ = normalize_number(s.twilio_whatsapp_number)
    to_ = normalize_number(to)
    try:
        msg = client.messages.create(from_=from_, to=to_, body=body)
    except TwilioRestException as exc:
        logger.warning("Twilio send failed (%s): %s", exc.code, exc.msg)
        raise WhatsAppSendError(exc.msg, code=exc.code) from exc
    return msg.sid
