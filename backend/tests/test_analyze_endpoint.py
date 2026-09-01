import pytest

from app.models.db import SessionLocal
from app.models.tables import Campaign, Recommendation


def _upload(client, sample_csv_bytes) -> str:
    resp = client.post(
        "/api/campaign/upload",
        files={"file": ("sample.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["account_id"]


def test_analyze_then_get_recommendations(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)

    resp = client.post("/api/analyze", json={"account_id": account_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["analyzed_keywords"] == 12
    assert body["recommendation_count"] == 8
    assert body["total_waste_identified"] == pytest.approx(2200.0)
    assert body["by_severity"] == {"HIGH": 2, "MEDIUM": 3, "LOW": 3}
    assert body["by_type"] == {
        "PAUSE_KEYWORD": 2,
        "INCREASE_BUDGET": 2,
        "ADD_NEGATIVE": 1,
        "REVIEW_LOW_CTR": 3,
    }

    first = body["recommendations"][0]
    assert first["severity"] == "HIGH"
    assert first["type"] == "PAUSE_KEYWORD"
    assert first["label"] == "cheap shoes online"
    assert first["campaign_name"] == "Generic Shoes"
    assert first["status"] == "PENDING"
    assert first["explanation"]

    # GET returns the same, persisted.
    got = client.get("/api/recommendations", params={"account_id": account_id})
    assert got.status_code == 200
    gbody = got.json()
    assert gbody["recommendation_count"] == 8
    assert gbody["total_waste_identified"] == pytest.approx(2200.0)
    assert [r["id"] for r in gbody["recommendations"]] == [
        r["id"] for r in body["recommendations"]
    ]


def test_analyze_is_idempotent(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)

    client.post("/api/analyze", json={"account_id": account_id})
    client.post("/api/analyze", json={"account_id": account_id})

    with SessionLocal() as db:
        rows = (
            db.query(Recommendation)
            .join(Campaign, Recommendation.campaign_id == Campaign.id)
            .filter(Campaign.account_id == account_id)
            .all()
        )
        assert len(rows) == 8  # not 16 — previous run replaced


def test_reupload_clears_stale_recommendations(client, sample_csv_bytes):
    account_id = _upload(client, sample_csv_bytes)
    client.post("/api/analyze", json={"account_id": account_id})

    smaller = (
        b"Campaign,Keyword,Search Term,Impressions,Clicks,Cost,Conversions,Conv. Value\n"
        b"Solo,kw,term,100,10,50,2,400\n"
    )
    client.post(
        "/api/campaign/upload",
        data={"account_id": account_id},
        files={"file": ("r2.csv", smaller, "text/csv")},
    )

    got = client.get("/api/recommendations", params={"account_id": account_id})
    assert got.json()["recommendation_count"] == 0  # cascade-deleted with campaigns


def test_analyze_unknown_account_404(client):
    resp = client.post("/api/analyze", json={"account_id": "does-not-exist"})
    assert resp.status_code == 404


def test_recommendations_unknown_account_404(client):
    resp = client.get("/api/recommendations", params={"account_id": "nope"})
    assert resp.status_code == 404
