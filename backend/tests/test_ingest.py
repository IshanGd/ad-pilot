import io

import pytest

from app.engine.ingest import CSVValidationError, parse_report


def test_parse_sample_report(sample_csv_bytes):
    report = parse_report(sample_csv_bytes)
    assert len(report.rows) == 12
    assert sorted(report.campaign_names) == [
        "Brand Search",
        "Clearance Sale",
        "Generic Shoes",
    ]

    avg = report.averages
    assert avg.total_impressions == 29800
    assert avg.total_clicks == 1071
    assert avg.total_spend == pytest.approx(11370.0)
    assert avg.total_conversions == pytest.approx(67.0)
    assert avg.total_conversion_value == pytest.approx(33200.0)
    assert avg.cpa == pytest.approx(11370.0 / 67.0)

    # "1,240.00" with quotes/comma must clean to a number.
    cheap = next(r for r in report.rows if r.search_term == "cheap shoes online")
    assert cheap.stats.spend == pytest.approx(1240.0)
    assert cheap.metrics.cpa is None  # zero conversions


def test_missing_columns_raises():
    bad = b"Campaign,Clicks,Cost\nBrand,10,100\n"
    with pytest.raises(CSVValidationError) as exc:
        parse_report(bad)
    assert exc.value.missing_columns  # populated for the API error body


def test_header_aliases_and_currency_symbols():
    csv = (
        "Campaign name,Keyword,Search term,Impr.,Clicks,Amount spent,Conv.,Conversion value\n"
        "C1,kw,term,\"1,000\",50,₹500,2,₹1000\n"
    )
    report = parse_report(csv.encode())
    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.stats.impressions == 1000
    assert row.stats.spend == pytest.approx(500.0)
    assert row.stats.conversion_value == pytest.approx(1000.0)
    assert row.metrics.cpa == pytest.approx(250.0)


def test_empty_file_raises():
    with pytest.raises(CSVValidationError):
        parse_report(b"")
