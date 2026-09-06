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

## Phase 8 status — budget optimizer + simulator

| Item | State |
|---|---|
| `POST /api/budget/optimize` — split a monthly budget across campaigns | done |
| `POST /api/simulation` — current vs projected cost per sale + sales count | done |
| `engine/budget.py` + `engine/simulation.py` (pure, rule-based) | done |
| `optimization_runs` row written on each simulation | done |
| Frontend `/plan/[accountId]` (linked from the audit) | done |
| Loading / error / empty states, sample CSV download | done (Phase 3) |

- Budget: weight by value returned; zero-sale campaigns get nothing; each line
  gets a plain reason (`SCALE_UP` / `TRIM` / `PAUSE` / `AVERAGE`).
- Simulation: the money on zero-sale keywords is reinvested into the best
  keyword at its cost per sale (or just saved if there's no efficient one).
  Always labelled "projected impact, not a guarantee".
- The `/plan` screen is English-only for now (the audit + WhatsApp loop are the
  bilingual core); the reason codes make localising it straightforward later.

## Phase 6 status — reply-to-act loop

| Item | State |
|---|---|
| `POST /api/whatsapp/webhook` — Twilio inbound, returns TwiML `<Message>` | done |
| `PAUSE` / `DETAILS` / `SCALE` keywords, tied to the last recommendation messaged | done |
| Unrecognised reply → friendly fallback (never silence, never a stack trace) | done |
| Simulated action: `recommendations.status` → `ACTIONED` + confirmation message | done |
| `POST /api/whatsapp/simulate-reply` — run the handler without Twilio (demo/tests) | done |
| Milestone: reply to a real WhatsApp message and get a response | needs a public URL |

- Replies are matched to an account by the sender's number (most recent audit
  wins). `PAUSE` acts on the last pausable finding, `SCALE` on the best
  `INCREASE_BUDGET`, `DETAILS` explains without acting.
- The Google Ads mutation is **simulated** — say so in the pitch.
- Signature validation is opt-in (`WHATSAPP_VALIDATE_SIGNATURE=true` +
  `WHATSAPP_WEBHOOK_URL=<exact public URL>`); off by default for tunnel testing.
- The real inbound milestone needs Twilio to reach the webhook — a tunnel
  (ngrok / cloudflared) or the deployed backend (Phase 9). Set the sandbox's
  "When a message comes in" to `<public-url>/api/whatsapp/webhook`.

## Phase 5 status — WhatsApp opt-in + delivery

| Item | State |
|---|---|
| `POST /api/whatsapp/opt-in` — register number + language, set `notify_opt_in` | done |
| `POST /api/whatsapp/send` — outbound message (explicit body or built from audit) | done |
| `POST /api/whatsapp/check` — re-check an account, message only on a real change | done |
| `scheduler/jobs.py` — the meaningful-change logic + `run_all_checks` sweep | done |
| APScheduler wiring (gated by `SCHEDULER_ENABLED`, default off) | done |
| Milestone: real WhatsApp message end to end from the sample data | needs Twilio creds |
| Inbound replies (PAUSE / DETAILS / SCALE) | Phase 6 |

**Confidence ladder (03_RULES §4).** A message is sent only when something
meaningfully new is found — a new HIGH-severity keyword vs the last message, or
total waste moving by more than `NOTIFY_WASTE_CHANGE_THRESHOLD` (15%). Otherwise
nothing is sent. `notification_state` (one row per account) holds the last
message's waste figure and HIGH keyword set.

- `whatsapp_service.py` is the only place the Twilio SDK is used. With no Twilio
  creds, opt-in/check still record state and report `twilio_not_configured` /
  `would_send` instead of sending.
- `POST /api/whatsapp/check` body: `{account_id, force?}`. `force: true` sends
  regardless (demo). Response: `sent`, `reason`, `body`/`would_send`, `provider_sid`.
- `scripts/whatsapp_smoke_test.py` (Phase 0) is still the quickest "does Twilio
  work at all" check.

## Phase 4 status — LLM explainer

| Item | State |
|---|---|
| `engine/explainer.py` — structured-JSON in, plain sentences out (03_RULES §3) | done |
| Number-grounding validation before any generated text is used | done |
| Template fallback (also the path when no `LLM_API_KEY` is set) | done |
| Hindi (`hi`) supported end to end: upload → analyze → explainer → API | done |

`POST /api/analyze` now runs the explainer after the rules. Response gains
`language`, `llm_explanations` (how many came from the LLM vs template), and
`explanation_source` per recommendation (`llm` | `template`; `stored` on GET).

- `POST /api/analyze` body accepts an optional `language` (`en` | `hi`); when
  given it is saved back to the account.
- The LLM only ever receives rounded, structured numbers — never CSV rows. Every
  figure in the returned text must already be in that input or the text is
  discarded for a template. Jargon (`CPA`/`CTR`/…) or a language mismatch also
  forces the template.
- Model: `LLM_MODEL` (default `claude-sonnet-5`). One batched call per audit.
- No key configured → every explanation is a template; the audit is unchanged.

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
