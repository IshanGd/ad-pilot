"""Phase 8 — budget optimizer + simulator, verified against the sample CSV.

Campaign aggregates: Generic Shoes 7310/8 sales, Brand Search 2300/53,
Clearance Sale 1760/6. Account avg cost per sale = 11370/67 = 169.70.
"""
from __future__ import annotations

import pytest

from app.engine.budget import CampaignInput, optimize_budget
from app.engine.simulation import SimulationInput, simulate
from app.models.db import SessionLocal
from app.models.tables import OptimizationRun


# --- engine: budget ------------------------------------------------


def _sample_campaigns():
    return [
        CampaignInput("g", "Generic Shoes", 7310.0, 8.0, 4300.0),
        CampaignInput("b", "Brand Search", 2300.0, 53.0, 26400.0),
        CampaignInput("c", "Clearance Sale", 1760.0, 6.0, 2500.0),
    ]


def test_optimize_budget_favours_efficient_campaign():
    allocs = optimize_budget(_sample_campaigns(), 20000.0, 169.70)
    by_name = {a.name: a for a in allocs}

    # Brand Search converts cheapest -> most budget, and it's ranked first.
    assert allocs[0].name == "Brand Search"
    assert by_name["Brand Search"].reason_code == "SCALE_UP"
    assert by_name["Generic Shoes"].reason_code == "TRIM"
    assert sum(a.suggested_budget for a in allocs) == pytest.approx(20000.0)
    assert by_name["Brand Search"].suggested_budget > by_name["Generic Shoes"].suggested_budget


def test_optimize_budget_zero_conversion_campaign_gets_nothing():
    campaigns = [
        CampaignInput("a", "Works", 1000.0, 10.0, 5000.0),
        CampaignInput("b", "Dead", 800.0, 0.0, 0.0),
    ]
    allocs = optimize_budget(campaigns, 2000.0, 100.0)
    dead = next(a for a in allocs if a.name == "Dead")
    assert dead.suggested_budget == 0
    assert dead.reason_code == "PAUSE"


def test_optimize_budget_all_zero_keeps_current_split():
    campaigns = [
        CampaignInput("a", "A", 750.0, 0.0, 0.0),
        CampaignInput("b", "B", 250.0, 0.0, 0.0),
    ]
    allocs = optimize_budget(campaigns, 1000.0, None)
    by_name = {a.name: a.suggested_budget for a in allocs}
    assert by_name["A"] == pytest.approx(750.0)
    assert by_name["B"] == pytest.approx(250.0)


# --- engine: simulation ------------------------------------------


def test_simulate_reinvests_waste_into_efficient_keyword():
    r = simulate(
        SimulationInput(
            current_spend=11370.0,
            current_conversions=67.0,
            wasted_spend=2200.0,
            best_efficient_cpa=37.5,
        )
    )
    assert r.reinvested is True
    assert r.current_cpa == pytest.approx(169.70, abs=0.1)
    assert r.extra_sales == pytest.approx(2200 / 37.5, abs=0.1)
    assert r.projected_conversions > r.current_conversions
    assert r.projected_cpa < r.current_cpa
    assert r.projected_spend == pytest.approx(11370.0)  # reallocated, not cut
    assert any("not a guarantee" in a for a in r.assumptions)


def test_simulate_just_saves_when_no_efficient_keyword():
    r = simulate(
        SimulationInput(
            current_spend=5000.0,
            current_conversions=20.0,
            wasted_spend=800.0,
            best_efficient_cpa=None,
        )
    )
    assert r.reinvested is False
    assert r.projected_spend == pytest.approx(4200.0)
    assert r.projected_conversions == pytest.approx(20.0)
    assert r.projected_cpa < r.current_cpa
    assert r.monthly_saving == pytest.approx(800.0)


# --- endpoints -------------------------------------------------


def _upload(client, sample_csv_bytes) -> str:
    return client.post(
        "/api/campaign/upload",
        files={"file": ("s.csv", sample_csv_bytes, "text/csv")},
    ).json()["account_id"]


def test_budget_optimize_endpoint(client, sample_csv_bytes):
    aid = _upload(client, sample_csv_bytes)
    resp = client.post(
        "/api/budget/optimize", json={"account_id": aid, "total_budget": 20000}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_total_spend"] == pytest.approx(11370.0)
    assert body["allocations"][0]["name"] == "Brand Search"
    assert sum(a["suggested_budget"] for a in body["allocations"]) == pytest.approx(20000)
    assert all(a["reason"] for a in body["allocations"])


def test_budget_optimize_rejects_non_positive_budget(client, sample_csv_bytes):
    aid = _upload(client, sample_csv_bytes)
    resp = client.post(
        "/api/budget/optimize", json={"account_id": aid, "total_budget": 0}
    )
    assert resp.status_code == 422


def test_simulation_endpoint_writes_a_run(client, sample_csv_bytes):
    aid = _upload(client, sample_csv_bytes)
    client.post("/api/analyze", json={"account_id": aid})

    resp = client.post("/api/simulation", json={"account_id": aid})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_cpa"] == pytest.approx(169.70, abs=0.1)
    assert body["projected_cpa"] < body["current_cpa"]
    assert body["monthly_saving"] == pytest.approx(2200.0)
    assert body["reinvested"] is True
    assert body["projected_conversions"] > body["current_conversions"]

    with SessionLocal() as db:
        runs = db.query(OptimizationRun).filter_by(account_id=aid).all()
        assert len(runs) == 1
        assert runs[0].total_waste_identified == pytest.approx(2200.0)


def test_planning_unknown_account_404(client):
    assert (
        client.post(
            "/api/budget/optimize",
            json={"account_id": "nope", "total_budget": 1000},
        ).status_code
        == 404
    )
    assert (
        client.post("/api/simulation", json={"account_id": "nope"}).status_code == 404
    )
