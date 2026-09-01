# AdPilot — 48-Hour Build Phases

Order matters. Build the core pipeline before the packaging (extension) and before
polish. If time runs short, cut from the end of this list, never from the middle.

## Phase 0 — Setup (Hours 0–3)

- Create repo, folder structure per `02_ARCHITECTURE.md`.
- Set up Postgres (Supabase) with the schema from `02_ARCHITECTURE.md`.
- Set up Twilio account + WhatsApp Sandbox, confirm "join `<code-word>`" flow works
  with at least one real phone before building anything else on top of it.
- Divide responsibilities (see team split at the end of this file).
- **Do not write recommendation logic or LLM prompts yet.**

## Phase 1 — Data pipeline (Hours 3–10)

- `POST /api/campaign/upload`: accept CSV, validate columns, parse with pandas.
- Compute per-keyword metrics (`engine/metrics.py`) per `03_RULES.md` section 1.
- Store campaigns + keywords in Postgres.
- Milestone: upload `sample_data/sample_google_ads_report.csv` and confirm metrics
  are computed correctly and stored.

## Phase 2 — Recommendation engine (Hours 10–18)

- Implement rule-based logic from `03_RULES.md` section 1 in `engine/rules.py`.
- Implement `POST /api/analyze` to run rules across all keywords for an account and
  write to `recommendations`.
- Implement `GET /api/recommendations`.
- Stretch, if time allows: `engine/anomaly.py` per `03_RULES.md` section 2.
- **No LLM calls yet — verify the rule engine output is correct against the sample
  CSV by hand first.**

## Phase 3 — Frontend core screens (Hours 18–25)

- Build with dummy/static data first, then connect to the real API.
- Screens (see `05_DESIGN.md` for full detail):
  1. Landing
  2. Upload
  3. Instant audit result (headline number + ranked recommendations)
- The instant audit screen is the most important screen in the entire product — it is
  the trust-building moment described in `01_PROJECT_REQUIREMENTS.md`. Do not let it
  be an afterthought relative to the dashboard.

## Phase 4 — LLM explainer layer (Hours 25–30)

- Implement `engine/explainer.py` per the contract in `03_RULES.md` section 3.
- Wire the validation check (numbers in output must match numbers in input) before
  storing/displaying any LLM text.
- Add Hindi as a second supported `language` value end-to-end.

## Phase 5 — WhatsApp opt-in + delivery (Hours 30–36)

- Build the opt-in flow: shown only after the audit result screen, per the
  confidence-ladder rule in `03_RULES.md` section 4.
- Implement `POST /api/whatsapp/opt-in` and `POST /api/whatsapp/send`.
- Build the scheduler job (`scheduler/jobs.py`) that re-runs analysis and sends a
  message only on meaningful new findings — not on a fixed timer regardless of
  content.
- Milestone: trigger a real WhatsApp message end-to-end from the sample data.

## Phase 6 — Reply-to-act loop (Hours 36–40)

- Implement `POST /api/whatsapp/webhook` to receive inbound replies.
- Handle `PAUSE`, `DETAILS`, `SCALE` keywords tied to the most recently sent
  recommendation for that phone number.
- The underlying Google Ads mutation is simulated — update `recommendations.status`
  and send a confirmation message. Be explicit in the pitch that execution is
  simulated for the demo.
- Milestone: reply to a WhatsApp message and receive a coherent response.

## Phase 7 — Chrome extension wrapper (Hours 40–43)

- Build the popup UI only (`extension/`): upload control, phone number field, submit
  button. Calls the same backend endpoints already built and tested.
- Do not attempt live Google Ads page scraping or OAuth — this is explicitly out of
  scope per `01_PROJECT_REQUIREMENTS.md`.
- If time is tight, this phase is the first one to cut — the web app alone is a
  complete, demoable product without it.

## Phase 8 — Polish (Hours 43–45)

- Loading states, error handling for malformed CSVs, empty states.
- Budget optimizer + simulator screens/endpoints if not already done (lower priority
  than the audit + WhatsApp loop — cut these before cutting Phase 5 or 6).
- Sample CSV download button on the upload screen.

## Phase 9 — Deployment + full rehearsal (Hours 45–47)

- Deploy frontend (Vercel), backend (Render/Railway), confirm from a fresh browser
  and a fresh phone number that has never opted in before.
- Run the entire demo flow start to finish at least twice without touching code.

## Phase 10 — Pitch prep (Hours 47–48)

- Stop coding.
- Rehearse the demo script (see `05_DESIGN.md` for suggested pitch beats).
- Confirm the demo phone is pre-joined to the Twilio sandbox before going on stage.

## Team split (4 people)

| Role | Owns |
|---|---|
| Backend/data | Phases 1, 2, 4 |
| Integrations | Phases 5, 6 (Twilio, scheduler) |
| Frontend | Phase 3, 7 (extension), 8 |
| Product/pitch | CSV validation edge cases, Phase 9, Phase 10, demo script |

If 3 people: merge integrations into backend/data. If 2 people: cut Phase 7 (extension)
entirely and skip the database in favor of in-memory/JSON storage for the demo.
