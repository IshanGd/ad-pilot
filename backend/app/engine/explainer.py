"""LLM explainer layer (03_RULES.md section 3).

Turns a structured recommendation into one to three sentences of plain language,
in the account's language. The rules that matter here are hard rules:

* the model only ever sees structured JSON, never raw CSV rows;
* the fixed system instruction below cannot be overridden by any input;
* before any generated text is used, every number in it must already appear in
  the structured input — otherwise the text is discarded and a template built
  directly from the numbers is used instead (never show an unverified figure).

If no LLM is configured (`LLM_API_KEY` unset) or the call fails, every
explanation falls back to the template. The audit works either way.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.config import get_settings
from app.engine.rules import (
    ADD_NEGATIVE,
    INCREASE_BUDGET,
    PAUSE_KEYWORD,
    REVIEW_LOW_CTR,
    Recommendation,
)

logger = logging.getLogger(__name__)

# 03_RULES.md section 3 — fixed, must not be overridable by user/keyword input.
SYSTEM_INSTRUCTION = (
    "Explain this recommendation to a small business owner in simple, "
    "non-technical language, in the specified language. Do not invent statistics "
    "or figures beyond what is provided. Keep it under 3 sentences. Do not use "
    "PPC jargon (CPA, CTR, ROAS, impressions) — describe outcomes in plain terms "
    "(money spent, sales, clicks) instead."
)

SUPPORTED_LANGUAGES = ("en", "hi")
_LANGUAGE_NAMES = {"en": "English", "hi": "Hindi"}

# Words that must never reach a business owner (03_RULES.md section 3 / 05_DESIGN).
_JARGON = ("cpa", "ctr", "roas", "impression", "conversion rate", "click-through")

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def normalize_language(value: str | None) -> str:
    v = (value or "en").strip().lower()
    return v if v in SUPPORTED_LANGUAGES else "en"


@dataclass(frozen=True)
class ExplainerInput:
    ref: str  # correlation key (keyword_id) — links output back to the rec
    keyword: str
    recommendation: str
    language: str
    facts: dict[str, float]


@dataclass(frozen=True)
class Explanation:
    ref: str
    text: str
    source: str  # "llm" | "template"
    language: str


@dataclass(frozen=True)
class ExplainerResult:
    by_ref: dict[str, Explanation] = field(default_factory=dict)

    @property
    def llm_count(self) -> int:
        return sum(1 for e in self.by_ref.values() if e.source == "llm")


# --- building the structured input ---------------------------------------


def to_explainer_input(rec: Recommendation, language: str) -> ExplainerInput:
    s = rec.signals
    facts: dict[str, float]
    if rec.type in (PAUSE_KEYWORD, ADD_NEGATIVE):
        facts = {
            "money_spent": round(s.get("spend", 0.0)),
            "clicks": round(s.get("clicks", 0.0)),
            "sales": 0,
            "money_at_stake": round(rec.estimated_impact or s.get("spend", 0.0)),
        }
    elif rec.type == INCREASE_BUDGET:
        facts = {
            "money_spent": round(s.get("spend", 0.0)),
            "sales": round(s.get("conversions", 0.0)),
            "cost_per_sale": round(s.get("cost_per_sale", 0.0)),
            "average_cost_per_sale": round(s.get("account_avg_cost_per_sale", 0.0)),
        }
        if rec.estimated_impact:
            facts["possible_extra_value"] = round(rec.estimated_impact)
    elif rec.type == REVIEW_LOW_CTR:
        facts = {
            "clicks": round(s.get("clicks", 0.0)),
            "views": round(s.get("impressions", 0.0)),
        }
    else:  # pragma: no cover - unknown type, keep whatever numbers we have
        facts = {k: round(v) for k, v in s.items()}

    return ExplainerInput(
        ref=rec.keyword_id,
        keyword=rec.label,
        recommendation=rec.type,
        language=normalize_language(language),
        facts=facts,
    )


# --- number validation --------------------------------------------------


def _allowed_numbers(facts: dict[str, float]) -> set[int]:
    allowed = {0}
    for v in facts.values():
        allowed.add(int(round(v)))
    return allowed


def extract_numbers(text: str) -> list[float]:
    text = text.translate(_DEVANAGARI_DIGITS)
    out: list[float] = []
    for token in _NUMBER_RE.findall(text):
        token = token.replace(",", "")
        try:
            out.append(float(token))
        except ValueError:
            continue
    return out


def numbers_are_grounded(text: str, facts: dict[str, float]) -> bool:
    """True iff every number in ``text`` matches a number in ``facts``."""
    allowed = _allowed_numbers(facts)
    for n in extract_numbers(text):
        if int(round(n)) not in allowed:
            return False
    return True


def _has_jargon(text: str) -> bool:
    low = text.lower()
    return any(term in low for term in _JARGON)


def _looks_like_language(text: str, language: str) -> bool:
    has_devanagari = bool(re.search(r"[ऀ-ॿ]", text))
    if language == "hi":
        return has_devanagari
    return not has_devanagari  # never mix languages (03_RULES.md section 5)


def _acceptable(text: str, inp: ExplainerInput) -> bool:
    text = text.strip()
    return (
        bool(text)
        and numbers_are_grounded(text, inp.facts)
        and not _has_jargon(text)
        and _looks_like_language(text, inp.language)
    )


# --- templates (fallback, and the only path with no LLM) ----------------


def _rupees(value: float) -> str:
    return f"₹{int(round(value)):,}"


def _n(value: float) -> str:
    return f"{int(round(value)):,}"


def template_explanation(inp: ExplainerInput) -> str:
    f = inp.facts
    hi = inp.language == "hi"
    kw = inp.keyword

    if inp.recommendation in (PAUSE_KEYWORD, ADD_NEGATIVE):
        if hi:
            return (
                f"“{kw}” पर {_rupees(f['money_spent'])} खर्च हुए और {_n(f['clicks'])} "
                f"क्लिक मिले, लेकिन एक भी बिक्री नहीं। इसे बंद करने से यह खर्च रुक जाएगा।"
            )
        return (
            f"“{kw}” cost {_rupees(f['money_spent'])} over {_n(f['clicks'])} clicks "
            f"and brought in no sales. Stopping it saves that money."
        )

    if inp.recommendation == INCREASE_BUDGET:
        if hi:
            return (
                f"“{kw}” से हर बिक्री {_rupees(f['cost_per_sale'])} में मिल रही है, जो "
                f"आपके औसत {_rupees(f['average_cost_per_sale'])} से काफी कम है। इस पर "
                f"ज़्यादा बजट लगाने से और बिक्री मिल सकती है।"
            )
        return (
            f"“{kw}” is bringing sales at {_rupees(f['cost_per_sale'])} each, well "
            f"below your average of {_rupees(f['average_cost_per_sale'])}. Giving it "
            f"more budget should bring more sales at a similar cost."
        )

    if inp.recommendation == REVIEW_LOW_CTR:
        if hi:
            return (
                f"“{kw}” को {_n(f['views'])} बार दिखाया गया पर सिर्फ {_n(f['clicks'])} "
                f"लोगों ने क्लिक किया। इसके विज्ञापन या शब्दों को देखना ठीक रहेगा।"
            )
        return (
            f"“{kw}” was shown {_n(f['views'])} times but only {_n(f['clicks'])} "
            f"people clicked. It is worth reviewing the wording or the keyword."
        )

    return inp.keyword  # pragma: no cover


# --- the LLM call ------------------------------------------------------


@lru_cache(maxsize=1)
def _client():  # pragma: no cover - exercised via integration, not unit tests
    settings = get_settings()
    if not settings.explainer_enabled:
        return None
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed; explainer uses templates")
        return None
    import os

    if not (
        settings.llm_api_key
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    ):
        logger.info("no LLM API key configured; explainer uses templates")
        return None
    try:
        if settings.llm_api_key:
            return anthropic.Anthropic(api_key=settings.llm_api_key)
        return anthropic.Anthropic()  # ANTHROPIC_API_KEY / profile
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not create Anthropic client: %s", exc)
        return None


def _build_user_message(inputs: list[ExplainerInput]) -> str:
    items = [
        {
            "ref": i.ref,
            "keyword": i.keyword,
            "recommendation": i.recommendation,
            "facts": i.facts,
        }
        for i in inputs
    ]
    return (
        "Write one explanation per item below. Use ONLY the numbers given in "
        '"facts", exactly as written — do not round, combine, or add any figure. '
        "Respond with a JSON object mapping each item's \"ref\" to its explanation "
        "string, and nothing else.\n\n"
        + json.dumps(items, ensure_ascii=False, indent=2)
    )


def _parse_response(text: str) -> dict[str, str]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model response")
    data = json.loads(text[start : end + 1])
    return {str(k): str(v) for k, v in data.items()}


def _call_llm(inputs: list[ExplainerInput], language: str) -> dict[str, str]:
    client = _client()
    if client is None:
        return {}
    settings = get_settings()
    system = (
        f"{SYSTEM_INSTRUCTION}\n\nThe specified language is "
        f"{_LANGUAGE_NAMES[language]}. Write every explanation in "
        f"{_LANGUAGE_NAMES[language]} only."
    )
    try:
        resp = client.with_options(timeout=20.0).messages.create(
            model=settings.llm_model,
            max_tokens=2000,
            thinking={"type": "disabled"},
            output_config={"effort": "low"},
            system=system,
            messages=[{"role": "user", "content": _build_user_message(inputs)}],
        )
    except Exception as exc:  # noqa: BLE001 - any failure -> templates
        logger.warning("explainer LLM call failed: %s", exc)
        return {}

    body = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    try:
        return _parse_response(body)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("could not parse explainer response: %s", exc)
        return {}


# --- public entrypoint ------------------------------------------------


def explain(recommendations: list[Recommendation], language: str) -> ExplainerResult:
    """Return one Explanation per recommendation, keyed by ``keyword_id``."""
    language = normalize_language(language)
    inputs = [to_explainer_input(r, language) for r in recommendations]
    by_ref: dict[str, Explanation] = {}

    generated = _call_llm(inputs, language) if inputs else {}

    for inp in inputs:
        candidate = generated.get(inp.ref, "").strip()
        if candidate and _acceptable(candidate, inp):
            by_ref[inp.ref] = Explanation(inp.ref, candidate, "llm", language)
        else:
            if candidate:
                logger.info(
                    "explainer output rejected for %s (%s); using template",
                    inp.ref,
                    inp.recommendation,
                )
            by_ref[inp.ref] = Explanation(
                inp.ref, template_explanation(inp), "template", language
            )
    return ExplainerResult(by_ref)
