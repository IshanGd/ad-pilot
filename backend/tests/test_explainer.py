"""Explainer: number-grounding validation, templates, and fallback (03_RULES §3)."""
from __future__ import annotations

import pytest

from app.engine import explainer as ex
from app.engine.rules import (
    ADD_NEGATIVE,
    INCREASE_BUDGET,
    PAUSE_KEYWORD,
    REVIEW_LOW_CTR,
    Recommendation,
)


def _rec(type_: str, **signals) -> Recommendation:
    return Recommendation(
        keyword_id=f"kw-{type_}",
        campaign_id="c1",
        label="cheap shoes online",
        type=type_,
        severity="HIGH",
        confidence=0.9,
        estimated_impact=signals.get("spend"),
        explanation="rule template",
        signals=signals,
    )


# --- number grounding -------------------------------------------------


def test_numbers_grounded_accepts_only_input_figures():
    facts = {"money_spent": 1240, "clicks": 83, "sales": 0}
    assert ex.numbers_are_grounded("Spent ₹1,240 over 83 clicks, 0 sales.", facts)
    assert not ex.numbers_are_grounded("Spent ₹1,240 and lost ₹5,000 more.", facts)


def test_numbers_grounded_handles_devanagari_and_separators():
    facts = {"money_spent": 1240, "clicks": 83}
    assert ex.numbers_are_grounded("₹1,240 खर्च, ८३ क्लिक।", facts)
    assert not ex.numbers_are_grounded("₹१२४५ खर्च।", facts)


def test_numbers_grounded_true_when_no_numbers():
    assert ex.numbers_are_grounded("This keyword is not working for you.", {"x": 5})


# --- acceptance gate -------------------------------------------------


def _input(language="en"):
    return ex.ExplainerInput(
        ref="k1",
        keyword="cheap shoes online",
        recommendation=PAUSE_KEYWORD,
        language=language,
        facts={"money_spent": 1240, "clicks": 83, "sales": 0, "money_at_stake": 1240},
    )


def test_acceptable_rejects_jargon():
    assert not ex._acceptable("Your CPA on this keyword is too high.", _input())


def test_acceptable_rejects_wrong_language():
    # English text when Hindi was asked for -> mixed language, reject.
    assert not ex._acceptable("This cost you 1240 and made no sales.", _input("hi"))
    # Hindi text when English asked for -> reject.
    assert not ex._acceptable("यह ₹1,240 का नुकसान है।", _input("en"))


def test_acceptable_passes_clean_grounded_text():
    assert ex._acceptable(
        "You spent ₹1,240 on this and got nothing back. Turn it off.", _input()
    )


# --- templates ------------------------------------------------------


@pytest.mark.parametrize("language", ["en", "hi"])
@pytest.mark.parametrize(
    "rec",
    [
        _rec(PAUSE_KEYWORD, spend=1240.0, clicks=83.0, conversions=0.0),
        _rec(ADD_NEGATIVE, spend=260.0, clicks=35.0, conversions=0.0),
        _rec(
            INCREASE_BUDGET,
            spend=1500.0,
            conversions=40.0,
            cost_per_sale=37.5,
            account_avg_cost_per_sale=169.7,
        ),
        _rec(REVIEW_LOW_CTR, clicks=8.0, impressions=1500.0),
    ],
)
def test_templates_are_grounded_and_jargon_free(rec, language):
    inp = ex.to_explainer_input(rec, language)
    text = ex.template_explanation(inp)
    assert text
    assert ex.numbers_are_grounded(text, inp.facts), text
    assert not ex._has_jargon(text), text
    assert ex._looks_like_language(text, language), text


def test_to_explainer_input_maps_signals():
    rec = _rec(INCREASE_BUDGET, spend=1500.0, conversions=40.0,
               cost_per_sale=37.5, account_avg_cost_per_sale=169.7)
    inp = ex.to_explainer_input(rec, "en")
    assert inp.facts["cost_per_sale"] == 38  # rounded
    assert inp.facts["average_cost_per_sale"] == 170
    assert inp.facts["sales"] == 40


# --- fallback behaviour --------------------------------------------


def test_explain_without_llm_returns_all_templates():
    # EXPLAINER_ENABLED=false in conftest, so _client() is None.
    recs = [
        _rec(PAUSE_KEYWORD, spend=1240.0, clicks=83.0, conversions=0.0),
        _rec(REVIEW_LOW_CTR, clicks=8.0, impressions=1500.0),
    ]
    result = ex.explain(recs, "en")
    assert result.llm_count == 0
    assert set(result.by_ref) == {r.keyword_id for r in recs}
    assert all(e.source == "template" for e in result.by_ref.values())


def test_explain_uses_llm_text_when_grounded(monkeypatch):
    rec = _rec(PAUSE_KEYWORD, spend=1240.0, clicks=83.0, conversions=0.0)
    monkeypatch.setattr(
        ex,
        "_call_llm",
        lambda inputs, language: {
            rec.keyword_id: "You spent ₹1,240 over 83 clicks with no sales at all."
        },
    )
    result = ex.explain([rec], "en")
    assert result.by_ref[rec.keyword_id].source == "llm"


def test_explain_rejects_llm_text_with_invented_number(monkeypatch):
    rec = _rec(PAUSE_KEYWORD, spend=1240.0, clicks=83.0, conversions=0.0)
    monkeypatch.setattr(
        ex,
        "_call_llm",
        lambda inputs, language: {
            rec.keyword_id: "This wastes about ₹9,999 every single month."
        },
    )
    result = ex.explain([rec], "en")
    assert result.by_ref[rec.keyword_id].source == "template"
