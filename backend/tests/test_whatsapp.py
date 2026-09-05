"""Phase 5 — WhatsApp opt-in, send, and the meaningful-change scheduler logic."""
from __future__ import annotations

import pytest

from app.models.db import SessionLocal
from app.models.tables import Account, NotificationState, WhatsAppMessage
from app.scheduler import jobs
from app.services import whatsapp_service as wa


def _upload(client, sample_csv_bytes) -> str:
    resp = client.post(
        "/api/campaign/upload",
        files={"file": ("sample.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["account_id"]


# --- phone normalization -------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+91 82965 46656", "whatsapp:+918296546656"),
        ("8296546656", "whatsapp:+918296546656"),
        ("whatsapp:+14155238886", "whatsapp:+14155238886"),
        ("+1 (415) 523-8886", "whatsapp:+14155238886"),
    ],
)
def test_normalize_number(raw, expected):
    assert wa.normalize_number(raw) == expected


def test_normalize_number_rejects_junk():
    with pytest.raises(ValueError):
        wa.normalize_number("not a phone")


# --- meaningful_change (03_RULES section 4) -----------------------


class _FakeRec:
    def __init__(self, label, severity):
        self.label = label
        self.severity = severity
        self.id = f"rec-{label}"
        self.estimated_impact = 100.0


class _FakeAudit:
    def __init__(self, waste, highs=(), language="en"):
        self.total_waste_identified = waste
        self.language = language
        self.recommendations = [_FakeRec(h, "HIGH") for h in highs]
        self.recommendation_count = len(self.recommendations)


def test_first_check_notifies_when_there_is_waste():
    changed, reason = jobs.meaningful_change(None, set(), _FakeAudit(2200, ["a"]), 0.15)
    assert changed and reason == "first_check"


def test_first_check_silent_when_nothing_found():
    changed, reason = jobs.meaningful_change(None, set(), _FakeAudit(0), 0.15)
    assert not changed and reason == "nothing_to_report"


def test_new_high_finding_notifies():
    changed, reason = jobs.meaningful_change(
        2000.0, {"old"}, _FakeAudit(2000, ["old", "new"]), 0.15
    )
    assert changed and reason == "new_high_finding"


def test_small_waste_move_is_silent():
    changed, reason = jobs.meaningful_change(
        2000.0, {"a"}, _FakeAudit(2100, ["a"]), 0.15
    )
    assert not changed and reason == "no_meaningful_change"


def test_large_waste_move_notifies():
    changed, reason = jobs.meaningful_change(
        2000.0, {"a"}, _FakeAudit(2600, ["a"]), 0.15
    )
    assert changed and reason == "waste_changed"


# --- message text -------------------------------------------------


@pytest.mark.parametrize("language", ["en", "hi"])
def test_build_message_has_number_and_action(language):
    audit = _FakeAudit(2200, ["cheap shoes online"], language=language)
    body, rec_id = jobs.build_notification_message(audit, language)
    assert rec_id == "rec-cheap shoes online"
    assert "2,200" in body
    assert ("PAUSE" in body) and ("DETAILS" in body)
    assert 2 <= body.count("\n") + 1 <= 4  # 2-4 lines


def test_build_message_summary_when_no_high():
    audit = _FakeAudit(400, [])
    audit.recommendations = [_FakeRec("x", "MEDIUM")]
    audit.recommendation_count = 1
    body, rec_id = jobs.build_notification_message(audit, "en")
    assert rec_id is None
    assert "400" in body and "DETAILS" in body


# --- opt-in endpoint ---------------------------------------------


def test_opt_in_records_number_without_twilio(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)
    resp = client.post(
        "/api/whatsapp/opt-in",
        json={"account_id": account_id, "phone_number": "+91 82965 46656", "language": "hi"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["notify_opt_in"] is True
    assert body["phone_number"] == "+918296546656"
    assert body["preferred_language"] == "hi"
    assert body["confirmation_sent"] is False
    assert body["warning"]

    with SessionLocal() as db:
        acc = db.get(Account, account_id)
        assert acc.notify_opt_in is True
        assert acc.phone_number == "+918296546656"


def test_opt_in_rejects_bad_number(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)
    resp = client.post(
        "/api/whatsapp/opt-in",
        json={"account_id": account_id, "phone_number": "abc"},
    )
    assert resp.status_code == 422


def test_opt_in_sends_confirmation_when_twilio_configured(
    client, sample_csv_bytes, monkeypatch
):
    sent = []
    monkeypatch.setattr("app.routes.whatsapp.whatsapp_configured", lambda: True)
    monkeypatch.setattr(
        "app.routes.whatsapp.send_whatsapp",
        lambda to, body: sent.append((to, body)) or "SM-confirm",
    )
    account_id = _upload(client, sample_csv_bytes)
    resp = client.post(
        "/api/whatsapp/opt-in",
        json={"account_id": account_id, "phone_number": "8296546656"},
    )
    assert resp.status_code == 200
    assert resp.json()["confirmation_sent"] is True
    assert sent and sent[0][0] == "+918296546656"


# --- send endpoint ---------------------------------------------


def test_send_requires_phone(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)
    resp = client.post("/api/whatsapp/send", json={"account_id": account_id})
    assert resp.status_code == 400


def test_send_uses_current_audit_when_no_body(client, sample_csv_bytes, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.routes.whatsapp.send_whatsapp",
        lambda to, body: sent.append((to, body)) or "SM-1",
    )
    account_id = _upload(client, sample_csv_bytes)
    client.post("/api/analyze", json={"account_id": account_id})
    client.post(
        "/api/whatsapp/opt-in",
        json={"account_id": account_id, "phone_number": "8296546656"},
    )
    resp = client.post("/api/whatsapp/send", json={"account_id": account_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider_sid"] == "SM-1"
    assert "cheap shoes online" in body["body"]


# --- check endpoint / scheduler job -------------------------------


def test_check_sends_once_then_stays_quiet(client, sample_csv_bytes, monkeypatch):
    sent = []
    monkeypatch.setattr(jobs, "whatsapp_configured", lambda: True)
    monkeypatch.setattr(
        jobs, "send_whatsapp", lambda to, body: sent.append((to, body)) or "SM-x"
    )
    account_id = _upload(client, sample_csv_bytes)
    client.post(
        "/api/whatsapp/opt-in",
        json={"account_id": account_id, "phone_number": "8296546656"},
    )

    first = client.post("/api/whatsapp/check", json={"account_id": account_id}).json()
    assert first["sent"] is True
    assert first["reason"] == "first_check"
    assert len(sent) == 1

    second = client.post("/api/whatsapp/check", json={"account_id": account_id}).json()
    assert second["sent"] is False
    assert second["reason"] == "no_meaningful_change"
    assert len(sent) == 1  # nothing new -> nothing sent

    forced = client.post(
        "/api/whatsapp/check", json={"account_id": account_id, "force": True}
    ).json()
    assert forced["sent"] is True and forced["reason"] == "forced"
    assert len(sent) == 2

    with SessionLocal() as db:
        state = db.get(NotificationState, account_id)
        assert state is not None and state.last_waste == pytest.approx(2200.0)
        msgs = db.query(WhatsAppMessage).filter_by(account_id=account_id).all()
        assert len(msgs) == 2
        assert all(m.direction == "OUTBOUND" for m in msgs)


def test_check_reports_twilio_not_configured(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)
    client.post(
        "/api/whatsapp/opt-in",
        json={"account_id": account_id, "phone_number": "8296546656"},
    )
    out = client.post("/api/whatsapp/check", json={"account_id": account_id}).json()
    assert out["sent"] is False
    assert out["reason"] == "twilio_not_configured"
    assert out["would_send"] and "2,200" in out["would_send"]


def test_check_not_opted_in(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)
    out = client.post("/api/whatsapp/check", json={"account_id": account_id}).json()
    assert out["sent"] is False and out["reason"] == "not_opted_in"
