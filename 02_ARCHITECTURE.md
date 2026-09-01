# AdPilot — Architecture

## 1. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend (web) | Next.js + React + Tailwind + Recharts | Upload, dashboard, audit result screens |
| Chrome extension | Plain HTML/JS popup (Manifest V3) | Thin UI only, calls the same backend API |
| Backend | Python + FastAPI | REST API, all business logic lives here |
| Data processing | Pandas + NumPy | CSV parsing, metric calculation |
| Database | PostgreSQL (Supabase acceptable) | See schema below |
| LLM | Any available LLM API | Explanation layer only — never the math |
| Messaging | Twilio WhatsApp Sandbox | Outbound + inbound webhook |
| Deployment | Frontend → Vercel, Backend → Render/Railway, DB → Supabase | Must be deployed before demo, not run locally |

## 2. System diagram (data flow)

```
 Business owner
       |
       v
 [Chrome extension]  or  [Web app upload screen]
       |  (CSV file)
       v
 POST /api/campaign/upload
       |
       v
 [Data pipeline: pandas validation + metric calculation]
       |
       v
 [Rule engine]  --------->  produces structured recommendations (JSON)
       |
       v
 [LLM explainer]  ------->  plain-language text, per recommendation
       |
       v
 [Postgres: campaigns, keywords, recommendations, optimization_runs]
       |
       +--> Web dashboard (instant audit screen)
       |
       +--> (opt-in) [Scheduler] --> [Twilio WhatsApp API] --> Business owner's phone
                                              ^
                                              |
                                   Inbound reply webhook
                                   (e.g. "PAUSE", "DETAILS")
                                              |
                                              v
                                   [Backend: simulated action handler]
                                              |
                                              v
                                   Confirmation message back to owner
```

## 3. Folder structure

```
adpilot/
  backend/
    app/
      main.py                 # FastAPI app entrypoint
      routes/
        upload.py              # POST /api/campaign/upload
        analyze.py              # POST /api/analyze
        recommendations.py      # GET /api/recommendations
        budget.py                # POST /api/budget/optimize
        simulation.py             # POST /api/simulation
        whatsapp.py                # Twilio send + inbound webhook
      engine/
        metrics.py              # CTR/CPC/CVR/CPA/ROAS calculations
        rules.py                # Rule-based recommendation logic (see 03_RULES.md)
        anomaly.py               # Stretch: fraud/anomaly pattern detection
        explainer.py             # LLM prompt construction + call
      models/
        schema.sql               # Table definitions (see below)
        db.py                     # DB connection/session
      scheduler/
        jobs.py                   # Recurring analysis job (APScheduler or cron)
    requirements.txt
  frontend/
    (Next.js app — screens per 05_DESIGN.md)
  extension/
    manifest.json
    popup.html
    popup.js
  sample_data/
    sample_google_ads_report.csv
```

## 4. Database schema

```sql
CREATE TABLE accounts (
  id UUID PRIMARY KEY,
  business_name TEXT,
  phone_number TEXT,          -- WhatsApp identifier, no login/password needed for MVP
  monthly_budget NUMERIC,
  preferred_language TEXT DEFAULT 'en',
  notify_opt_in BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE campaigns (
  id UUID PRIMARY KEY,
  account_id UUID REFERENCES accounts(id),
  name TEXT,
  budget NUMERIC,
  spend NUMERIC,
  impressions INT,
  clicks INT,
  conversions INT,
  conversion_value NUMERIC
);

CREATE TABLE keywords (
  id UUID PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id),
  keyword TEXT,
  search_term TEXT,
  match_type TEXT,
  impressions INT,
  clicks INT,
  spend NUMERIC,
  conversions INT,
  ctr NUMERIC,
  cpc NUMERIC,
  cpa NUMERIC
);

CREATE TABLE recommendations (
  id UUID PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id),
  keyword_id UUID REFERENCES keywords(id),
  type TEXT,                  -- PAUSE_KEYWORD | INCREASE_BUDGET | DECREASE_BUDGET | ADD_NEGATIVE | ANOMALY
  severity TEXT,               -- HIGH | MEDIUM | LOW
  explanation TEXT,             -- LLM-generated plain-language text
  confidence NUMERIC,
  estimated_impact NUMERIC,      -- ₹ saved or gained
  status TEXT DEFAULT 'PENDING'   -- PENDING | ACTIONED | DISMISSED
);

CREATE TABLE optimization_runs (
  id UUID PRIMARY KEY,
  account_id UUID REFERENCES accounts(id),
  created_at TIMESTAMP DEFAULT now(),
  current_cpa NUMERIC,
  projected_cpa NUMERIC,
  current_conversions INT,
  projected_conversions INT,
  total_waste_identified NUMERIC
);

CREATE TABLE whatsapp_messages (
  id UUID PRIMARY KEY,
  account_id UUID REFERENCES accounts(id),
  direction TEXT,              -- OUTBOUND | INBOUND
  body TEXT,
  related_recommendation_id UUID REFERENCES recommendations(id),
  created_at TIMESTAMP DEFAULT now()
);
```

## 5. API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/campaign/upload` | Accept CSV, validate, store campaigns/keywords |
| POST | `/api/analyze` | Run rule engine + LLM explainer, store recommendations |
| GET | `/api/recommendations` | Return current recommendations for an account |
| POST | `/api/budget/optimize` | Return suggested budget reallocation for a given total |
| POST | `/api/simulation` | Return current vs projected CPA/conversions |
| POST | `/api/whatsapp/opt-in` | Register phone number + language, set `notify_opt_in` |
| POST | `/api/whatsapp/send` | Trigger an outbound WhatsApp message (used by scheduler) |
| POST | `/api/whatsapp/webhook` | Twilio inbound webhook — handles replies like `PAUSE`, `DETAILS` |

## 6. Environment variables

```
DATABASE_URL=
LLM_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=
```

## 7. Integration notes

- **Twilio WhatsApp Sandbox**: recipients must send a one-time "join `<code-word>`"
  message to the Twilio sandbox number before they can receive messages. This is a
  Meta requirement, not skippable — account for it in the demo script.
- **LLM explainer**: always called with structured JSON (see `03_RULES.md` for the
  exact prompt contract), never with raw CSV rows.
- **Scheduler**: for the hackathon, a simple timer-based job is sufficient — it does
  not need to be a production-grade task queue.
