# AdPilot backend

FastAPI + pandas + SQLAlchemy. See `../02_ARCHITECTURE.md` and `../03_RULES.md`.
External-service setup (Supabase, Twilio) is tracked in `../SETUP.md`.

## Run locally

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux
cp .env.example .env
.venv/Scripts/python -m uvicorn app.main:app --reload
```

Docs at http://127.0.0.1:8000/docs. With no `DATABASE_URL` set, it uses a local
SQLite file (`adpilot.db`); set a Postgres URL for deploy.

## Test

```bash
cd backend
.venv/Scripts/python -m pytest
```

## Twilio WhatsApp sandbox smoke test (Phase 0)

Once `TWILIO_*` vars are set in `.env` (see `../SETUP.md`):

```bash
cd backend
.venv/Scripts/python -m scripts.whatsapp_smoke_test +9198XXXXXXXX
```

Sends one WhatsApp message to a phone that has joined the sandbox. Standalone —
no app or DB involved.

## Phase 1 status — data pipeline

| Item | State |
|---|---|
| `POST /api/campaign/upload` — CSV validate + parse (pandas) | done |
| `engine/metrics.py` — CTR/CPC/CVR/CPA/ROAS + account averages | done |
| Store campaigns + keywords (SQLite/Postgres) | done |
| Milestone: upload `sample_data/sample_google_ads_report.csv`, metrics stored | verified |

### Upload endpoint

`POST /api/campaign/upload` (multipart form):

- `file` — Google Ads CSV export (required). Columns matched case/spacing/
  punctuation-insensitively: Campaign, Keyword, Search Term, Impressions, Clicks,
  Cost, Conversions, Conv. Value. `Ad Group` and `Match Type` optional.
- `account_id` — optional; re-uploads replace that account's campaign data.
- `business_name`, `preferred_language` (default `en`) — optional.

Returns the new `account_id`, campaign/keyword counts, account totals, aggregate
account averages, and a per-campaign breakdown (sorted by spend).

## Phase 2 status — recommendation engine

| Item | State |
|---|---|
| `engine/rules.py` — rule logic from `03_RULES.md` §1 (pure, no DB/LLM) | done |
| `POST /api/analyze` — run rules for an account, write `recommendations` | done |
| `GET /api/recommendations?account_id=…` | done |
| Verified by hand against the sample CSV (`tests/test_rules.py`) | done |
| `engine/anomaly.py` (stretch) | not started |

### Analyze / recommendations endpoints

`POST /api/analyze` — body `{"account_id": "..."}`. Recomputes recommendations
for the account from its stored keywords, **replacing** the previous run. Returns
the headline `total_waste_identified` (₹ on `PAUSE_KEYWORD` + `ADD_NEGATIVE`),
`by_severity` / `by_type` counts, and the ranked list.

`GET /api/recommendations?account_id=…` — the persisted list, same ranking.

Recommendation types: `PAUSE_KEYWORD` (HIGH), `INCREASE_BUDGET` / `ADD_NEGATIVE`
(MEDIUM), `REVIEW_LOW_CTR` (LOW). Ranked by severity, then ₹ impact desc. The
`WASTE_COST_THRESHOLD` defaults to `max(₹500, 5% of account spend)`; override with
the env var.

`explanation` is a deterministic template built from the input numbers — Phase 4
replaces it with validated LLM text. No LLM calls in this phase.

### Notes / deviations from the architecture doc

- Money is stored as `float` (rupees) rather than `NUMERIC`/`Decimal`, to avoid
  Decimal/float friction across pandas, the rule engine, and JSON. Still numeric
  end to end; formatting happens only at the display layer (03_RULES.md §6).
- `keywords.conversion_value` added (not in the original schema) so ROAS can be
  computed per 03_RULES.md §1.
- `recommendations` / `optimization_runs` / `whatsapp_messages` tables exist in
  `schema.sql` but are not written to until later phases.
