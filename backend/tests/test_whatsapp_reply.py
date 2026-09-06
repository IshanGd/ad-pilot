"""Phase 6 — inbound reply loop (PAUSE / DETAILS / SCALE), 03_RULES §4.5."""
from __future__ import annotations

import pytest

from app.models.db import SessionLocal
from app.models.tables import Recommendation, WhatsAppMessage
from app.services import reply_service as rs


def _upload(client, sample_csv_bytes) -> str:
    return client.post(
        "/api/campaign/upload",
        files={"file": ("s.csv", sample_csv_bytes, "text/csv")},
    ).json()["account_id"]


def _ready_account(client, sample_csv_bytes, phone="8296546656", lang="en") -> str:
    aid = _upload(client, sample_csv_bytes)
    client.post("/api/analyze", json={"account_id": aid})
    r = client.post(
        "/api/whatsapp/opt-in",
        json={"account_id": aid, "phone_number": phone, "language": lang},
    )
    assert r.status_code == 200, r.text
    return aid


def _reply(client, account_id: str, body: str) -> dict:
    r = client.post(
        "/api/whatsapp/simulate-reply",
        json={"account_id": account_id, "body": body},
    )
    assert r.status_code == 200, r.text
    return r.json()


# --- keyword parsing ------------------------------------------------


@pytest.mark.parametrize(
    "body,expected",
    [
        ("PAUSE", "PAUSE"),
        ("pause please", "PAUSE"),
        ("  Details.  ", "DETAILS"),
        ("scale", "SCALE"),
        ("PAWS", None),
        ("hello there", None),
        ("", None),
        ("   ", None),
    ],
)
def test_parse_keyword(body, expected):
    assert rs.parse_keyword(body) == expected


def test_account_for_number_matches_trailing_digits(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes, phone="8296546656")
    with SessionLocal() as db:
        assert rs.account_for_number(db, "whatsapp:+918296546656").id == aid
        assert rs.account_for_number(db, "+91 82965 46656").id == aid
        assert rs.account_for_number(db, "+1 000 000 0000") is None


# --- reply behaviour ---------------------------------------------


def test_pause_marks_recommendation_actioned(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes)
    out = _reply(client, aid, "PAUSE")

    assert out["keyword"] == "PAUSE"
    assert out["action_taken"] is True
    assert "paused (simulated for demo)" in out["reply_text"]
    assert "cheap shoes online" in out["reply_text"]
    assert "1,240" in out["reply_text"]

    with SessionLocal() as db:
        rec = db.get(Recommendation, out["recommendation_id"])
        assert rec.status == "ACTIONED"
        inbound = (
            db.query(WhatsAppMessage)
            .filter_by(account_id=aid, direction="INBOUND")
            .count()
        )
        assert inbound == 1


def test_details_explains_without_acting(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes)
    out = _reply(client, aid, "DETAILS")

    assert out["keyword"] == "DETAILS"
    assert out["action_taken"] is False
    assert out["reply_text"]
    with SessionLocal() as db:
        rec = db.get(Recommendation, out["recommendation_id"])
        assert rec.status == "PENDING"


def test_scale_actions_an_increase_budget_rec(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes)
    out = _reply(client, aid, "SCALE")

    assert out["keyword"] == "SCALE"
    assert out["action_taken"] is True
    assert "more budget" in out["reply_text"]
    with SessionLocal() as db:
        rec = db.get(Recommendation, out["recommendation_id"])
        assert rec.type == "INCREASE_BUDGET"
        assert rec.status == "ACTIONED"


def test_unrecognised_reply_gets_friendly_fallback(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes)
    out = _reply(client, aid, "what does this mean??")
    assert out["keyword"] is None
    assert out["action_taken"] is False
    assert "PAUSE" in out["reply_text"] and "DETAILS" in out["reply_text"]


def test_unknown_number_is_handled(client):
    r = client.post(
        "/api/whatsapp/simulate-reply",
        json={"from_number": "+1 555 000 1111", "body": "PAUSE"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["account_id"] is None
    assert "recognise" in body["reply_text"].lower() or "recognize" in body["reply_text"].lower()


def test_reply_uses_last_alerted_recommendation(client, sample_csv_bytes, monkeypatch):
    from app.scheduler import jobs

    monkeypatch.setattr(jobs, "whatsapp_configured", lambda: True)
    monkeypatch.setattr(jobs, "send_whatsapp", lambda to, body: "SM-alert")
    aid = _ready_account(client, sample_csv_bytes)
    client.post("/api/whatsapp/check", json={"account_id": aid, "force": True})

    out = _reply(client, aid, "PAUSE")
    with SessionLocal() as db:
        # the rec tied to the alert message
        msg = (
            db.query(WhatsAppMessage)
            .filter_by(account_id=aid, direction="OUTBOUND")
            .filter(WhatsAppMessage.related_recommendation_id.isnot(None))
            .first()
        )
        assert out["recommendation_id"] == msg.related_recommendation_id


def test_pause_ignores_last_rec_when_it_is_not_pausable(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes)
    scaled = _reply(client, aid, "SCALE")  # last rec is now an INCREASE_BUDGET one
    paused = _reply(client, aid, "PAUSE")
    assert paused["recommendation_id"] != scaled["recommendation_id"]
    with SessionLocal() as db:
        rec = db.get(Recommendation, paused["recommendation_id"])
        assert rec.type in ("PAUSE_KEYWORD", "ADD_NEGATIVE")


def test_hindi_reply(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes, lang="hi")
    out = _reply(client, aid, "PAUSE")
    assert "रोक दिया गया" in out["reply_text"]
    assert "नकली" in out["reply_text"]


# --- Twilio webhook (TwiML) ------------------------------------


def test_webhook_returns_twiml(client, sample_csv_bytes):
    aid = _ready_account(client, sample_csv_bytes)
    r = client.post(
        "/api/whatsapp/webhook",
        data={"From": "whatsapp:+918296546656", "Body": "DETAILS", "MessageSid": "SM1"},
    )
    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]
    assert "<Response><Message>" in r.text
    assert "</Message></Response>" in r.text


def test_webhook_unknown_keyword_still_replies(client):
    r = client.post(
        "/api/whatsapp/webhook",
        data={"From": "whatsapp:+910000000000", "Body": "hi"},
    )
    assert r.status_code == 200
    assert "<Message>" in r.text
