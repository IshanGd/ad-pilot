import pytest

from app.models.db import SessionLocal
from app.models.tables import Account, Campaign, Keyword


def test_upload_sample_csv_stores_campaigns_and_keywords(client, sample_csv_bytes):
    resp = client.post(
        "/api/campaign/upload",
        files={"file": ("sample_google_ads_report.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["campaigns"] == 3
    assert body["keywords"] == 12
    assert body["totals"]["spend"] == pytest.approx(11370.0)
    assert body["totals"]["clicks"] == 1071
    assert body["totals"]["conversions"] == pytest.approx(67.0)
    assert body["account_averages"]["cpa"] == pytest.approx(11370.0 / 67.0)

    # campaign_breakdown sorted by spend desc
    names = [c["name"] for c in body["campaign_breakdown"]]
    assert names[0] == "Generic Shoes"
    assert body["campaign_breakdown"][0]["spend"] == pytest.approx(7310.0)

    # Persisted correctly
    account_id = body["account_id"]
    with SessionLocal() as db:
        account = db.get(Account, account_id)
        assert account is not None
        campaigns = db.query(Campaign).filter_by(account_id=account_id).all()
        assert len(campaigns) == 3
        keywords = (
            db.query(Keyword)
            .join(Campaign)
            .filter(Campaign.account_id == account_id)
            .all()
        )
        assert len(keywords) == 12
        cheap = next(k for k in keywords if k.search_term == "cheap shoes online")
        assert cheap.cpa is None
        assert cheap.spend == pytest.approx(1240.0)
        strong = next(k for k in keywords if k.keyword == "adpilot shoes")
        assert strong.cpa == pytest.approx(1500.0 / 40.0)
        assert strong.ctr == pytest.approx(300 / 2000)


def test_reupload_replaces_previous_data(client, sample_csv_bytes):
    first = client.post(
        "/api/campaign/upload",
        files={"file": ("r.csv", sample_csv_bytes, "text/csv")},
    ).json()
    account_id = first["account_id"]

    smaller = (
        b"Campaign,Keyword,Search Term,Impressions,Clicks,Cost,Conversions,Conv. Value\n"
        b"Only Campaign,kw,term,100,10,50,1,200\n"
    )
    resp = client.post(
        "/api/campaign/upload",
        data={"account_id": account_id},
        files={"file": ("r2.csv", smaller, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["account_id"] == account_id
    assert body["campaigns"] == 1
    assert body["keywords"] == 1

    with SessionLocal() as db:
        campaigns = db.query(Campaign).filter_by(account_id=account_id).all()
        assert len(campaigns) == 1
        assert campaigns[0].name == "Only Campaign"


def test_rejects_csv_without_required_columns(client):
    bad = b"Campaign,Clicks\nBrand,10\n"
    resp = client.post(
        "/api/campaign/upload",
        files={"file": ("bad.csv", bad, "text/csv")},
    )
    assert resp.status_code == 422
    assert "missing required columns" in resp.json()["detail"].lower()


def test_rejects_non_csv_extension(client):
    resp = client.post(
        "/api/campaign/upload",
        files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 415
