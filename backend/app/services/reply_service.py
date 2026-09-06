"""Inbound WhatsApp replies — the reply-to-act loop (Phase 6, 03_RULES §4.5).

Recognised keywords: PAUSE, DETAILS, SCALE. They act on the recommendation the
account was last messaged about (falling back to its current top finding).

The Google Ads mutation is **simulated** — we set `recommendations.status` and
send a confirmation. This is called out as simulated in the pitch.
Unrecognised replies get a friendly nudge, never silence, never a stack trace.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.engine.explainer import normalize_language
from app.models.tables import Account, Keyword, Recommendation, WhatsAppMessage
from app.services.analyze_service import get_recommendations

KEYWORDS = ("PAUSE", "DETAILS", "SCALE")


@dataclass
class ReplyResult:
    reply_text: str
    keyword: str | None  # PAUSE | DETAILS | SCALE | None (unrecognised)
    account_id: str | None
    recommendation_id: str | None = None
    action_taken: bool = False


def _rupees(value: float | None) -> str:
    return f"₹{int(round(value or 0)):,}"


def parse_keyword(body: str) -> str | None:
    tokens = (body or "").split()
    if not tokens:
        return None
    first = re.sub(r"[^A-Za-z]", "", tokens[0]).upper()
    return first if first in KEYWORDS else None


def account_for_number(db: Session, phone_number: str) -> Account | None:
    """The account a reply from ``phone_number`` belongs to.

    Match on the trailing digits (forgiving of "+", spaces, "whatsapp:"). If the
    same number has run more than one audit, the most recent account wins — that's
    what the person is replying about.
    """
    digits = re.sub(r"\D", "", phone_number or "")
    if not digits:
        return None
    candidates = db.scalars(
        select(Account)
        .where(Account.phone_number.isnot(None))
        .order_by(desc(Account.created_at))
    ).all()
    for acc in candidates:
        if re.sub(r"\D", "", acc.phone_number or "") == digits:
            return acc
    return None


def _last_related_recommendation(db: Session, account_id: str) -> Recommendation | None:
    msg = db.scalars(
        select(WhatsAppMessage)
        .where(
            WhatsAppMessage.account_id == account_id,
            WhatsAppMessage.direction == "OUTBOUND",
            WhatsAppMessage.related_recommendation_id.isnot(None),
        )
        .order_by(desc(WhatsAppMessage.created_at))
    ).first()
    if msg is None or msg.related_recommendation_id is None:
        return None
    return db.get(Recommendation, msg.related_recommendation_id)


def _label(db: Session, rec: Recommendation) -> str:
    if rec.keyword_id:
        kw = db.get(Keyword, rec.keyword_id)
        if kw is not None:
            return (kw.keyword or kw.search_term or "this keyword").strip()
    return "this keyword"


def handle_inbound(db: Session, from_number: str, body: str) -> ReplyResult:
    account = account_for_number(db, from_number)
    keyword = parse_keyword(body)

    if account is None:
        return ReplyResult(
            reply_text=(
                "I don't recognise this number yet. Run a free audit at AdPilot "
                "and opt in there first."
            ),
            keyword=keyword,
            account_id=None,
        )

    lang = normalize_language(account.preferred_language)
    hi = lang == "hi"

    # Log the inbound message.
    db.add(
        WhatsAppMessage(account_id=account.id, direction="INBOUND", body=body or "")
    )
    db.flush()

    if keyword is None:
        text = (
            "माफ़ करें, समझ नहीं आया। अपने पिछले अपडेट के बारे में PAUSE, SCALE, "
            "या DETAILS लिखें।"
            if hi
            else "Sorry, I didn't catch that. Reply PAUSE, SCALE, or DETAILS "
            "about your last update."
        )
        return _finish(db, account, text, keyword, None, False)

    current = get_recommendations(db, account.id).recommendations
    related = _last_related_recommendation(db, account.id)

    def pick(*types: str) -> Recommendation | None:
        """The last recommendation we messaged about if it fits, else the current
        top one of the wanted type(s)."""
        if related is not None and (not types or related.type in types):
            return related
        return _first_of_type(db, current, types)

    if keyword == "DETAILS":
        rec = pick()  # any type
        if rec is None:
            text = (
                "अभी इस नंबर के लिए कोई अपडेट नहीं है।"
                if hi
                else "There's no recent update for this number yet."
            )
            return _finish(db, account, text, keyword, None, False)
        text = rec.explanation or _label(db, rec)
        if rec.estimated_impact:
            text += (
                f"\nइसमें शामिल पैसा: {_rupees(rec.estimated_impact)}."
                if hi
                else f"\nMoney involved: {_rupees(rec.estimated_impact)}."
            )
        return _finish(db, account, text, keyword, rec.id, False)

    if keyword == "PAUSE":
        rec = pick("PAUSE_KEYWORD", "ADD_NEGATIVE")
        if rec is None:
            text = (
                "रोकने के लिए अभी कोई कीवर्ड नहीं है।"
                if hi
                else "There's nothing to pause right now."
            )
            return _finish(db, account, text, keyword, None, False)
        rec.status = "ACTIONED"
        label = _label(db, rec)
        text = (
            f"हो गया — “{label}” रोक दिया गया (डेमो के लिए नकली)। "
            f"अनुमानित बचत: {_rupees(rec.estimated_impact)}/माह।"
            if hi
            else f"Done — “{label}” paused (simulated for demo). "
            f"Estimated saving: {_rupees(rec.estimated_impact)}/month."
        )
        return _finish(db, account, text, keyword, rec.id, True)

    # SCALE
    rec = pick("INCREASE_BUDGET")
    if rec is None:
        text = (
            "अभी बढ़ाने लायक कोई कीवर्ड नहीं दिख रहा।"
            if hi
            else "You don't have a clear keyword to scale up right now."
        )
        return _finish(db, account, text, keyword, None, False)
    rec.status = "ACTIONED"
    label = _label(db, rec)
    extra = (
        (
            f" संभावित अतिरिक्त मूल्य: {_rupees(rec.estimated_impact)}."
            if hi
            else f" Possible extra value: about {_rupees(rec.estimated_impact)}."
        )
        if rec.estimated_impact
        else ""
    )
    text = (
        f"हो गया — “{label}” को ज़्यादा बजट (डेमो के लिए नकली)।{extra}"
        if hi
        else f"Done — more budget going to “{label}” (simulated for demo).{extra}"
    )
    return _finish(db, account, text, keyword, rec.id, True)


def _first_of_type(db: Session, current_recs, types: tuple[str, ...]):
    for r in current_recs:
        if not types or r.type in types:
            return db.get(Recommendation, r.id)
    return None


def _finish(
    db: Session,
    account: Account,
    text: str,
    keyword: str | None,
    rec_id: str | None,
    action_taken: bool,
) -> ReplyResult:
    rec_id = str(rec_id) if rec_id is not None else None
    db.add(
        WhatsAppMessage(
            account_id=account.id,
            direction="OUTBOUND",
            body=text,
            related_recommendation_id=rec_id,
        )
    )
    db.commit()
    return ReplyResult(
        reply_text=text,
        keyword=keyword,
        account_id=str(account.id),
        recommendation_id=rec_id,
        action_taken=action_taken,
    )
