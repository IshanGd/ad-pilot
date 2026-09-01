from app.engine.metrics import KeywordStats, account_averages, keyword_metrics


def test_keyword_metrics_basic():
    m = keyword_metrics(
        KeywordStats(impressions=1000, clicks=100, spend=500.0, conversions=10, conversion_value=2500.0)
    )
    assert m.ctr == 0.1
    assert m.cpc == 5.0
    assert m.cvr == 0.1
    assert m.cpa == 50.0
    assert m.roas == 5.0


def test_cpa_is_none_when_no_conversions():
    m = keyword_metrics(
        KeywordStats(impressions=4000, clicks=83, spend=1240.0, conversions=0)
    )
    assert m.cpa is None
    assert m.roas == 0.0  # conversion_value 0 / spend 1240


def test_metrics_none_when_denominator_zero():
    m = keyword_metrics(KeywordStats(impressions=0, clicks=0, spend=0.0, conversions=0))
    assert m.ctr is None and m.cpc is None and m.cvr is None and m.cpa is None
    assert m.roas is None


def test_account_averages_are_aggregate_ratios():
    rows = [
        KeywordStats(impressions=1000, clicks=100, spend=200.0, conversions=10, conversion_value=1000.0),
        KeywordStats(impressions=1000, clicks=50, spend=300.0, conversions=0, conversion_value=0.0),
    ]
    avg = account_averages(rows)
    assert avg.total_impressions == 2000
    assert avg.total_clicks == 150
    assert avg.total_spend == 500.0
    assert avg.total_conversions == 10
    assert avg.ctr == 150 / 2000
    assert avg.cpa == 500.0 / 10
    assert avg.roas == 1000.0 / 500.0
