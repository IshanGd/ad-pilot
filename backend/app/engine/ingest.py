"""Google Ads CSV export -> validated, metric-annotated rows.

Pure parsing/validation logic. No DB access — see app/services/ingest_service.py
for persistence.

Expected columns (case/spacing/punctuation insensitive), per
01_PROJECT_REQUIREMENTS.md section 4:

    Campaign, Ad Group, Keyword, Search Term, Impressions, Clicks, Cost,
    Conversions, Conv. Value

"Match Type" is accepted if present but not required.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import pandas as pd

from app.engine.metrics import (
    AccountAverages,
    KeywordMetrics,
    KeywordStats,
    account_averages,
    keyword_metrics,
)

# canonical field -> accepted header spellings (after normalisation)
_COLUMN_ALIASES: dict[str, set[str]] = {
    "campaign": {"campaign", "campaign name"},
    "ad_group": {"ad group", "adgroup", "ad group name"},
    "keyword": {"keyword", "keywords", "search keyword"},
    "search_term": {"search term", "search terms", "query", "search query"},
    "match_type": {"match type", "keyword match type"},
    "impressions": {"impressions", "impr", "impr."},
    "clicks": {"clicks"},
    "spend": {"cost", "spend", "amount spent"},
    "conversions": {"conversions", "conv", "conv.", "conversion"},
    "conversion_value": {
        "conv value",
        "conv. value",
        "conversion value",
        "total conv value",
        "value",
    },
}

REQUIRED_FIELDS = (
    "campaign",
    "keyword",
    "search_term",
    "impressions",
    "clicks",
    "spend",
    "conversions",
    "conversion_value",
)

_NUMERIC_FIELDS = (
    "impressions",
    "clicks",
    "spend",
    "conversions",
    "conversion_value",
)


class CSVValidationError(ValueError):
    """Raised when the uploaded file is not a usable Google Ads report."""

    def __init__(self, message: str, missing_columns: list[str] | None = None):
        super().__init__(message)
        self.missing_columns = missing_columns or []


@dataclass
class IngestRow:
    campaign: str
    ad_group: str | None
    keyword: str | None
    search_term: str | None
    match_type: str | None
    stats: KeywordStats
    metrics: KeywordMetrics


@dataclass
class ParsedReport:
    rows: list[IngestRow] = field(default_factory=list)
    averages: AccountAverages | None = None

    @property
    def campaign_names(self) -> list[str]:
        seen: dict[str, None] = {}
        for r in self.rows:
            seen.setdefault(r.campaign, None)
        return list(seen)


def _normalise_header(name: str) -> str:
    name = name.strip().lower()
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name)
    return name


def _build_header_map(columns: list[str]) -> dict[str, str]:
    """Map canonical field -> actual column name present in the DataFrame."""
    normalised = {col: _normalise_header(col) for col in columns}
    resolved: dict[str, str] = {}
    for field_name, aliases in _COLUMN_ALIASES.items():
        for actual, norm in normalised.items():
            if norm in aliases:
                resolved[field_name] = actual
                break
    return resolved


def _clean_number(value: object) -> float:
    """Parse '1,240.50', '₹300', '$1.2', '--', '' -> float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if pd.notna(value) else 0.0
    text = str(value).strip()
    if text in {"", "--", "-", "—", "N/A", "n/a"}:
        return 0.0
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", ".", "-."}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _read_dataframe(file_bytes: bytes) -> pd.DataFrame:
    if not file_bytes.strip():
        raise CSVValidationError("The uploaded file is empty.")
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, skip_blank_lines=True)
    except Exception as exc:  # pragma: no cover - pandas raises many types
        raise CSVValidationError(f"Could not parse the file as CSV: {exc}") from exc
    df = df.dropna(how="all")
    if df.empty:
        raise CSVValidationError("The file has headers but no data rows.")
    return df


def parse_report(file_bytes: bytes) -> ParsedReport:
    df = _read_dataframe(file_bytes)
    header_map = _build_header_map(list(df.columns))

    missing = [f for f in REQUIRED_FIELDS if f not in header_map]
    if missing:
        raise CSVValidationError(
            "The report is missing required columns: "
            + ", ".join(_pretty(f) for f in missing),
            missing_columns=[_pretty(f) for f in missing],
        )

    report = ParsedReport()
    for _, raw in df.iterrows():
        campaign = _text(raw.get(header_map["campaign"]))
        if not campaign:
            continue  # skip total/summary rows with no campaign

        stats = KeywordStats(
            impressions=int(_clean_number(raw.get(header_map["impressions"]))),
            clicks=int(_clean_number(raw.get(header_map["clicks"]))),
            spend=_clean_number(raw.get(header_map["spend"])),
            conversions=_clean_number(raw.get(header_map["conversions"])),
            conversion_value=_clean_number(raw.get(header_map["conversion_value"])),
        )
        report.rows.append(
            IngestRow(
                campaign=campaign,
                ad_group=_text(raw.get(header_map.get("ad_group"))),
                keyword=_text(raw.get(header_map.get("keyword"))),
                search_term=_text(raw.get(header_map.get("search_term"))),
                match_type=_text(raw.get(header_map.get("match_type"))),
                stats=stats,
                metrics=keyword_metrics(stats),
            )
        )

    if not report.rows:
        raise CSVValidationError("No usable rows found in the report.")

    report.averages = account_averages(r.stats for r in report.rows)
    return report


def _pretty(field_name: str) -> str:
    return {
        "campaign": "Campaign",
        "keyword": "Keyword",
        "search_term": "Search Term",
        "impressions": "Impressions",
        "clicks": "Clicks",
        "spend": "Cost",
        "conversions": "Conversions",
        "conversion_value": "Conv. Value",
    }.get(field_name, field_name)


def _text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None
