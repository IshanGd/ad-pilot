# AdPilot backend

FastAPI + pandas + SQLAlchemy. See `../02_ARCHITECTURE.md` and `../03_RULES.md`.

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

### Notes / deviations from the architecture doc

- Money is stored as `float` (rupees) rather than `NUMERIC`/`Decimal`, to avoid
  Decimal/float friction across pandas, the rule engine, and JSON. Still numeric
  end to end; formatting happens only at the display layer (03_RULES.md §6).
- `keywords.conversion_value` added (not in the original schema) so ROAS can be
  computed per 03_RULES.md §1.
- `recommendations` / `optimization_runs` / `whatsapp_messages` tables exist in
  `schema.sql` but are not written to until later phases.
