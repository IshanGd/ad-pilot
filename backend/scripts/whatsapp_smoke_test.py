"""Phase 0 smoke test: confirm the Twilio WhatsApp Sandbox is wired up.

This is deliberately standalone — it does not import the FastAPI app or touch the
database. It only proves that:

  1. TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_NUMBER are set, and
  2. an outbound WhatsApp message actually reaches a real phone that has already
     sent "join <code-word>" to the sandbox number.

Per 04_PHASES.md, get this working before building any of Phase 5 on top of it.

Usage (from backend/):

    .venv/Scripts/python -m scripts.whatsapp_smoke_test +9198XXXXXXXX
    .venv/Scripts/python -m scripts.whatsapp_smoke_test +9198XXXXXXXX --body "custom text"

The destination number must belong to a phone that has joined the sandbox.
"""
from __future__ import annotations

import argparse
import sys

from app.config import get_settings


def _normalize(number: str) -> str:
    """Accept "+9198...", "9198...", or an already-prefixed "whatsapp:+9198..."."""
    number = number.strip()
    if number.startswith("whatsapp:"):
        return number
    if not number.startswith("+"):
        number = "+" + number
    return f"whatsapp:{number}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("to", help="destination phone, e.g. +9198XXXXXXXX (must have joined the sandbox)")
    parser.add_argument(
        "--body",
        default="AdPilot sandbox smoke test — if you see this, outbound WhatsApp works.",
        help="message text to send",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    missing = [
        name
        for name, value in (
            ("TWILIO_ACCOUNT_SID", settings.twilio_account_sid),
            ("TWILIO_AUTH_TOKEN", settings.twilio_auth_token),
            ("TWILIO_WHATSAPP_NUMBER", settings.twilio_whatsapp_number),
        )
        if not value
    ]
    if missing:
        print("Missing required env vars:", ", ".join(missing), file=sys.stderr)
        print("Fill them in backend/.env (see ../SETUP.md).", file=sys.stderr)
        return 2

    # Imported here so `--help` works without the dependency installed yet.
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException

    from_number = _normalize(settings.twilio_whatsapp_number)
    to_number = _normalize(args.to)

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    try:
        message = client.messages.create(from_=from_number, to=to_number, body=args.body)
    except TwilioRestException as exc:
        print(f"Twilio rejected the request: {exc.msg}", file=sys.stderr)
        if exc.code == 63007:
            print("Hint: TWILIO_WHATSAPP_NUMBER is not the sandbox number for this account.", file=sys.stderr)
        elif exc.code == 63015 or exc.code == 63016:
            print("Hint: the destination phone has not sent 'join <code-word>' to the sandbox.", file=sys.stderr)
        return 1

    print(f"Sent. message SID: {message.sid}, status: {message.status}")
    print("Check the destination phone — the message should arrive within a few seconds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
