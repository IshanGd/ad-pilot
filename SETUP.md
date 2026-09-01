# AdPilot — Phase 0 setup

External-service setup that has to exist before the later phases. Tracks
`04_PHASES.md` → Phase 0.

| Item | State |
|---|---|
| Repo + folder structure (`02_ARCHITECTURE.md` §3) | done |
| Postgres schema (`backend/app/models/schema.sql`) | done |
| Supabase Postgres provisioned + schema applied | done |
| Twilio account + WhatsApp Sandbox + join flow confirmed | **todo — see below** |
| LLM API key (Phase 4 explainer) | optional — see §3 |
| Team split | see `04_PHASES.md` "Team split" |

---

## 1. Supabase (done)

Project is provisioned and `schema.sql` has been applied. For deploy, the backend
reads the connection string from `DATABASE_URL` in `backend/.env`:

```
DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@HOST:5432/postgres
```

Use the **session pooler** connection string from Supabase → Project Settings →
Database. Leave `DATABASE_URL` unset for local dev (falls back to SQLite).

To re-apply the schema after a change:

```bash
psql "$DATABASE_URL_PLAIN" -f backend/app/models/schema.sql
```

(`$DATABASE_URL_PLAIN` = the same URL without the `+psycopg2` driver suffix.)

---

## 2. Twilio WhatsApp Sandbox (todo)

Do this before building anything in Phase 5. The goal is only to **confirm an
outbound WhatsApp message reaches a real phone** — no backend routes yet.

### 2a. Create the account

1. Sign up at <https://www.twilio.com/try-twilio> (free trial is fine).
2. Verify your email and a phone number.
3. From the Twilio Console home, copy **Account SID** and **Auth Token**.

### 2b. Activate the WhatsApp Sandbox

1. Console → **Messaging → Try it out → Send a WhatsApp message**
   (direct link: <https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn>).
2. Note the sandbox **sender number** (usually `+1 415 523 8886`) and the
   **join code** (e.g. `join clever-panda`).
3. From every phone that needs to receive messages (at minimum the demo phone),
   open WhatsApp and send `join <your-code>` to the sandbox number.
   You should get a "You are all set!" reply. This lasts 72 hours of inactivity,
   then must be re-sent — re-join the demo phone the morning of the demo.

### 2c. Fill in `backend/.env`

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886
```

### 2d. Run the smoke test

From `backend/`, with the venv set up (`README.md` → Run locally) and `twilio`
installed (`pip install -r requirements.txt`):

```bash
.venv/Scripts/python -m scripts.whatsapp_smoke_test +9198XXXXXXXX
```

Pass the number of a phone that has already joined the sandbox. Expected output:

```
Sent. message SID: SMxxxx…, status: queued
Check the destination phone — the message should arrive within a few seconds.
```

If the phone receives the message, Phase 0's Twilio item is complete.

Common failures the script explains:
- missing env vars → fill in `backend/.env`
- error `63016` → the destination phone has not sent `join <code-word>`
- error `63007` → `TWILIO_WHATSAPP_NUMBER` isn't this account's sandbox number

### 2e. Inbound webhook (defer to Phase 6)

The sandbox's "When a message comes in" webhook URL is configured in Phase 6,
once `POST /api/whatsapp/webhook` exists and the backend is deployed. Nothing to
do now.

---

## 3. LLM API key (Phase 4 explainer — optional)

The audit works without this: with no key, recommendation explanations use
deterministic templates (English and Hindi). Add a key to get LLM-written
phrasing — every number in it is still verified against the rule input before
it's shown.

1. Get an Anthropic API key from <https://console.anthropic.com> (`sk-ant-...`).
2. In `backend/.env`:

   ```
   LLM_API_KEY=sk-ant-...
   LLM_MODEL=claude-sonnet-5
   ```

3. Restart the backend. `POST /api/analyze` responses will show
   `"llm_explanations"` > 0 and `"explanation_source": "llm"` on recommendations
   whose generated text passed validation.

Set `EXPLAINER_ENABLED=false` to force templates even with a key present.
