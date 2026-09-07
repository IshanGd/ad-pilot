# AdPilot

**Instant Google Ads audit + WhatsApp monitoring for small businesses.**

> You don't come to us. We come to you — on WhatsApp, in plain language, only when it matters.

Most small businesses running Google Ads have no time to log into a dashboard and
no interest in learning what "CPA" means. So money leaks — on keywords that never
convert, on budgets left unbalanced, on nobody watching the account between setup
and the bill. Existing tools (Optmyzr, Adalysis, WordStream) assume you already
track conversions, already log in daily, and can pay $100+/month. AdPilot assumes
none of that.

**Live demo:** https://ad-pilot-gamma.vercel.app  ·  API: https://adpilot-api-lv8o.onrender.com/health
*(free-tier backend — the first request after a while takes ~50s to wake)*

---

## How it works

```
  Google Ads CSV export
          │
          ▼
   Upload  ──►  Rule engine  ──►  LLM explainer  ──►  Instant audit
 (no login)     (waste, scale,     (plain language,     "You've wasted ₹2,200
                 negatives)         number-checked)       this month" + ranked
                                                          actions, EN / हिंदी)
          │
          ▼  (opt in — only after you've seen the value)
   WhatsApp  ◄──►  you
   • alert only when something meaningfully changes
   • reply PAUSE / SCALE / DETAILS to act (execution simulated for the demo)
```

### The demo, start to finish

1. Upload `sample_data/sample_google_ads_report.csv` — no signup.
2. See the headline: **₹2,200 wasted this month**, and 8 ranked recommendations
   ("Turn off *cheap shoes online* — ₹1,240", …). Toggle **हिंदी**.
3. Open the **budget plan**: cost per sale **₹170 → ₹90**, and a suggested split
   across campaigns.
4. Enter a WhatsApp number → opt in → a confirmation message arrives.
5. When a new problem appears, AdPilot messages you. Reply **PAUSE** → it
   confirms the (simulated) action and the estimated saving.

---

## What's in the box (MVP scope)

| # | Feature | Where |
|---|---|---|
| 1 | Instant audit — CSV in, headline waste number + ranked actions out, no login | `backend/app/engine/rules.py`, `frontend/app/audit` |
| 2 | Rule-based recommendation engine (PAUSE / SCALE / NEGATIVE / low-CTR) — no ML | `backend/app/engine/rules.py` |
| 3 | LLM explainer — structured JSON in, plain sentences out; **every number is verified against the input** or a template is used | `backend/app/engine/explainer.py` |
| 4 | WhatsApp delivery (Twilio) — sent only on a *meaningful* change, never on a timer | `backend/app/scheduler/jobs.py` |
| 5 | Reply-to-act loop — `PAUSE` / `DETAILS` / `SCALE`; the Google Ads mutation is **simulated** and labelled as such | `backend/app/services/reply_service.py` |
| 6 | Chrome extension — thin MV3 popup over the same API (no page scraping, no OAuth) | `extension/` |
| + | Budget optimizer + simulator | `backend/app/engine/{budget,simulation}.py`, `frontend/app/plan` |

**Bilingual:** English + Hindi, plumbed through upload → analyze → explainer →
WhatsApp. **No PPC jargon** anywhere a business owner reads — enforced by a test.

**Explicitly out of scope** (48-hour build): live Google Ads OAuth / API writes,
any ML model, other ad platforms, billing, user accounts with passwords.

---

## Tech

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) · React · Tailwind |
| Backend | Python · FastAPI · pandas · SQLAlchemy |
| Database | PostgreSQL (Supabase) |
| LLM | Anthropic Claude (`claude-sonnet-5`) — explanation layer only, never the maths |
| Messaging | Twilio WhatsApp Sandbox (outbound + inbound webhook) |
| Extension | Plain HTML/JS, Manifest V3 |
| Deploy | Frontend → Vercel · Backend → Render · DB → Supabase |

Numbers are computed by rules in Python and checked; the LLM only rewrites them
into sentences. No figure a user sees is ever hallucinated.

---

## Repository layout

```
backend/       FastAPI service — engine/ (rules, metrics, explainer, budget,
               simulation), routes/, services/, scheduler/, models/, tests/
frontend/      Next.js app — landing, upload, /audit/[id], /plan/[id]
extension/     Manifest V3 popup
sample_data/   sample_google_ads_report.csv
```

Design docs: [`01_PROJECT_REQUIREMENTS`](01_PROJECT_REQUIREMENTS.md) ·
[`02_ARCHITECTURE`](02_ARCHITECTURE.md) · [`03_RULES`](03_RULES.md) (binding
behaviour) · [`04_PHASES`](04_PHASES.md) · [`05_DESIGN`](05_DESIGN.md)

---

## Run it locally

```bash
# backend  →  http://127.0.0.1:8000  (docs at /docs)
cd backend
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env
.venv/Scripts/python -m uvicorn app.main:app --reload
.venv/Scripts/python -m pytest        # 89 tests

# frontend  →  http://localhost:3000
cd frontend
npm install
cp .env.local.example .env.local      # NEXT_PUBLIC_API_BASE_URL
npm run dev
```

With no `.env`, the backend uses a local SQLite file and the audit works with no
external services (WhatsApp / LLM degrade to templates). Details in
[`backend/README.md`](backend/README.md), [`frontend/README.md`](frontend/README.md),
[`extension/README.md`](extension/README.md).

**Deploying:** [`DEPLOY.md`](DEPLOY.md). External-service setup:
[`SETUP.md`](SETUP.md).

---

## Status

All build phases complete (0–9). The reply-to-act execution is simulated for the
demo — everything else runs on real infrastructure.

> **Demo-day note:** the Twilio sandbox only sends free-form messages within 24h
> of the recipient's last message to it. Message the sandbox number from the demo
> phone right before presenting.
