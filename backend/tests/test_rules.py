"""Rule engine verified by hand against sample_data/sample_google_ads_report.csv.

Account totals (from test_upload_endpoint): spend 11,370 / clicks 1,071 /
impressions 29,800 / conversions 67.
  account_avg_cpa = 11370 / 67   = 169.70
  account_avg_ctr = 1071 / 29800 = 0.03594
  waste threshold = max(500, 5% * 11370) = 568.50
"""
from __future__ import annotations

import pytest

from app.engine.ingest import parse_report
from app.engine.rules import (
    ADD_NEGATIVE,
    INCREASE_BUDGET,
    PAUSE_KEYWORD,
    REVIEW_LOW_CTR,
    KeywordRow,
    analyze_keywords,
    total_waste_identified,
    waste_cost_threshold,
)
from tests.conftest import SAMPLE_CSV


def _rows_and_averages():
    report = parse_report(SAMPLE_CSV.read_bytes())
    rows = [
        KeywordRow(
            keyword_id=f"kw{i}",
            campaign_id=f"c-{r.campaign}",
            label=r.keyword or r.search_term or "?",
            search_term=r.search_term,
            stats=r.stats,
            metrics=r.metrics,
        )
        for i, r in enumerate(report.rows)
    ]
    return rows, report.averages


def _by_label(recs):
    return {r.label: r for r in recs}


def test_waste_cost_threshold_default_and_override():
    assert waste_cost_threshold(11370.0) == pytest.approx(568.5)
    assert waste_cost_threshold(4000.0) == 500.0  # floor wins
    assert waste_cost_threshold(11370.0, configured=250.0) == 250.0


def test_sample_csv_recommendations():
    rows, averages = _rows_and_averages()
    recs = analyze_keywords(rows, averages)
    by_label = _by_label(recs)

    # Two zero-conversion keywords over the ₹568.50 threshold -> PAUSE, HIGH.
    assert by_label["cheap shoes online"].type == PAUSE_KEYWORD
    assert by_label["cheap shoes online"].severity == "HIGH"
    assert by_label["cheap shoes online"].confidence == 0.9  # 83 clicks > 20
    assert by_label["cheap shoes online"].estimated_impact == pytest.approx(1240.0)
    assert by_label["shoe repair"].type == PAUSE_KEYWORD
    assert by_label["shoe repair"].estimated_impact == pytest.approx(700.0)

    # 35 clicks, no sales, under the spend threshold -> ADD_NEGATIVE.
    assert by_label["free shoes"].type == ADD_NEGATIVE
    assert by_label["free shoes"].severity == "MEDIUM"
    assert by_label["free shoes"].estimated_impact == pytest.approx(260.0)

    # CPA far below account average with >= 3 conversions -> INCREASE_BUDGET.
    assert by_label["adpilot shoes"].type == INCREASE_BUDGET
    assert by_label["adpilot store"].type == INCREASE_BUDGET

    # Very low CTR, > 500 impressions, not caught by an earlier rule.
    for label in ("kids shoes", "leather boots", "sneaker sale"):
        assert by_label[label].type == REVIEW_LOW_CTR
        assert by_label[label].severity == "LOW"

    # Keywords that trigger nothing.
    for label in ("adpilot coupon", "buy shoes online", "running shoes", "discount sneakers"):
        assert label not in by_label


def test_sample_csv_totals_and_ranking():
    rows, averages = _rows_and_averages()
    recs = analyze_keywords(rows, averages)

    assert len(recs) == 8
    assert total_waste_identified(recs) == pytest.approx(2200.0)  # 1240 + 700 + 260

    severities = [r.severity for r in recs]
    assert severities == sorted(severities, key={"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get)
    # HIGH block ranked by ₹ impact desc.
    assert [r.label for r in recs if r.severity == "HIGH"] == [
        "cheap shoes online",
        "shoe repair",
    ]


def test_explanations_have_no_ppc_jargon():
    rows, averages = _rows_and_averages()
    recs = analyze_keywords(rows, averages)
    banned = ("CPA", "CTR", "ROAS", "impressions", "conversion rate")
    for r in recs:
        assert r.explanation
        lowered = r.explanation.lower()
        assert not any(term.lower() in lowered for term in banned), r.explanation


def test_increase_budget_needs_three_conversions():
    rows, averages = _rows_and_averages()
    # adpilot coupon: 1 conversion, cheap CPA — must NOT be INCREASE_BUDGET.
    recs = _by_label(analyze_keywords(rows, averages))
    assert "adpilot coupon" not in recs
