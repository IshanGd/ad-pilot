"""Recurring notification check (03_RULES.md section 4 — the confidence ladder).

The rule that matters: a WhatsApp message goes out only when something
meaningfully new is found — a new HIGH-severity finding, or total identified
waste moving by more than a threshold since the last message. If nothing is new,
nothing is sent. Silence is intentional.

`run_notification_check` is the unit the scheduler calls per account; it is also
exposed directly as `POST /api/whatsapp/check` for the demo.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.tables import Account, NotificationState, WhatsAppMessage
from app.services.analyze_service import get_recommendations, run_analysis
from app.services.whatsapp_service import (
    WhatsAppSendError,
    send_whatsapp,
    whatsapp_configured,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _rupees(value: float) -> str:
    return f"₹{int(round(value)):,}"


# --- message text (05_DESIGN.md section 5) ------------------------------


def _high_labels(audit) -> set[str]:
    return {r.label for r in audit.recommendations if r.severity == "HIGH"}


def build_notification_message(audit, language: str) -> tuple[str, str | None]:
    """Return (body, related_recommendation_id). 2-4 lines: one number, one action."""
    hi = language == "hi"
    highs = [r for r in audit.recommendations if r.severity == "HIGH"]
    total = audit.total_waste_identified

    if highs:
        top = highs[0]
        spent = _rupees(top.estimated_impact or 0)
        if hi:
            body = (
                f"AdPilot: “{top.label}” पर {spent} खर्च हुए, कोई बिक्री नहीं। "
                f"इस महीने अब तक {_rupees(total)} बेकार गया।\n"
                f"रोकने के लिए PAUSE भेजें, ज़्यादा जानकारी के लिए DETAILS।"
            )
        else:
            body = (
                f"AdPilot: “{top.label}” spent {spent} with no sales. "
                f"That's {_rupees(total)} wasted this month so far.\n"
                f"Reply PAUSE to stop it, or DETAILS for more."
            )
        return body, top.id

    if total > 0 or audit.recommendation_count:
        n = audit.recommendation_count
        if hi:
            body = (
                f"AdPilot जाँच: लगभग {_rupees(total)} {n} कीवर्ड पर बेकार जा रहा है।\n"
                f"पूरी जानकारी के लिए DETAILS भेजें।"
            )
        else:
            body = (
                f"AdPilot check-in: about {_rupees(total)} is being wasted across "
                f"{n} keywords.\nReply DETAILS for the full picture."
            )
        return body, None

    return "", None


# --- change detection --------------------------------------------------


def meaningful_change(
    prev_waste: float | None,
    prev_high: set[str],
    audit,
    threshold: float,
) -> tuple[bool, str]:
    current_high = _high_labels(audit)

    if prev_waste is None:  # never notified this account
        if current_high or audit.total_waste_identified > 0:
            return True, "first_check"
        return False, "nothing_to_report"

    if current_high - prev_high:
        return True, "new_high_finding"

    base = max(prev_waste, 1.0)
    if abs(audit.total_waste_identified - prev_waste) / base > threshold:
        return True, "waste_changed"

    return False, "no_meaningful_change"


# --- the per-account job ----------------------------------------------


@dataclass
class NotifyOutcome:
    account_id: str
    sent: bool
    reason: str
    body: str | None = None
    provider_sid: str | None = None
    would_send: str | None = None

    def as_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "sent": self.sent,
            "reason": self.reason,
            "body": self.body,
            "provider_sid": self.provider_sid,
            "would_send": self.would_send,
        }


def _save_state(db: Session, account_id: str, audit, message_id: str | None) -> None:
    state = db.get(NotificationState, account_id)
    if state is None:
        state = NotificationState(account_id=account_id)
        db.add(state)
    state.last_notified_at = _utcnow()
    state.last_waste = audit.total_waste_identified
    state.last_high_keywords = "\n".join(sorted(_high_labels(audit)))
    state.last_message_id = message_id


def run_notification_check(
    db: Session, account: Account, *, force: bool = False
) -> NotifyOutcome:
    settings = get_settings()

    audit = run_analysis(db, account.id)  # re-run the rules; uses account language
    language = audit.language

    state = db.get(NotificationState, account.id)
    prev_waste = state.last_waste if state else None
    prev_high = (
        {s for s in (state.last_high_keywords or "").split("\n") if s}
        if state
        else set()
    )

    changed, reason = meaningful_change(
        prev_waste, prev_high, audit, settings.notify_waste_change_threshold
    )
    out = NotifyOutcome(account_id=str(account.id), sent=False, reason=reason)

    if not (force or changed):
        return out
    if not account.notify_opt_in or not account.phone_number:
        out.reason = "not_opted_in"
        return out

    body, rec_id = build_notification_message(audit, language)
    if not body:
        out.reason = "nothing_to_report"
        return out

    if not whatsapp_configured():
        out.reason = "twilio_not_configured"
        out.would_send = body
        return out

    try:
        sid = send_whatsapp(account.phone_number, body)
    except WhatsAppSendError as exc:
        out.reason = f"send_failed: {exc}"
        return out

    msg = WhatsAppMessage(
        account_id=account.id,
        direction="OUTBOUND",
        body=body,
        related_recommendation_id=rec_id,
        provider_sid=sid,
    )
    db.add(msg)
    db.flush()
    _save_state(db, account.id, audit, msg.id)
    db.commit()

    out.sent = True
    out.reason = reason if changed else "forced"
    out.body = body
    out.provider_sid = sid
    return out


def run_all_checks(session_factory) -> list[dict]:
    """Scheduler entrypoint: check every opted-in account."""
    results: list[dict] = []
    with session_factory() as db:
        accounts = db.scalars(
            select(Account).where(Account.notify_opt_in.is_(True))
        ).all()
        for account in accounts:
            try:
                results.append(run_notification_check(db, account).as_dict())
            except Exception:  # noqa: BLE001 - one bad account must not stop the rest
                logger.exception("notification check failed for account %s", account.id)
                db.rollback()
    logger.info("notification sweep: %d accounts, %d sent",
                len(results), sum(1 for r in results if r["sent"]))
    return results


def message_from_current_audit(db: Session, account_id: str) -> tuple[str, str | None]:
    """Build a message from what's already stored (no re-analysis). Used by
    POST /api/whatsapp/send when no explicit body is given."""
    audit = get_recommendations(db, account_id)
    return build_notification_message(audit, audit.language)
