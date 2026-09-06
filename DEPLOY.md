# AdPilot — deployment (Phase 9)

Frontend → **Vercel**, backend → **Render**, database → **Supabase** (already
provisioned). Everything must be deployed and rehearsed before the pitch, not run
from a laptop.

---

## 0. Prerequisites

- **GitHub repo.** Recreate it and push `main` (Vercel and Render both deploy
  from GitHub):
  ```bash
  git remote set-url origin https://github.com/<you>/adpilot.git   # or `git remote add origin …`
  git push -u origin main
  ```
- **Supabase** is done. Have the **session-pooler** connection string ready
  (Project Settings → Database → Connection string → "Session pooler"), in the
  form `postgresql+psycopg2://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
  If this is a fresh database, run `backend/app/models/schema.sql` against it once.

---

## 1. Backend → Render

1. **New → Blueprint**, pick the repo. Render reads `render.yaml` and creates
   `adpilot-api`.
2. Set the env vars it marks as required:
   | Var | Value |
   |---|---|
   | `DATABASE_URL` | the Supabase session-pooler URL |
   | `CORS_ORIGINS` | leave blank for now; set in step 3 |
   | `LLM_API_KEY` | `sk-ant-…` (optional — templates are used if unset) |
   | `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | from the Twilio console |
   | `TWILIO_WHATSAPP_NUMBER` | `+14155238886` (already in the blueprint) |
3. Deploy. Note the URL, e.g. `https://adpilot-api.onrender.com`.
4. Check `https://adpilot-api.onrender.com/health` → `{"status":"ok"}`.

> Render's free instance sleeps after ~15 min idle; the first request then takes
> ~50s. Hit `/health` a minute before the demo to wake it. Keep
> `SCHEDULER_ENABLED=false` (a sleeping instance can't run the scheduler anyway —
> the demo uses `POST /api/whatsapp/check`).

---

## 2. Frontend → Vercel

1. **Add New → Project**, import the repo. Set **Root Directory** to `frontend`.
   Framework preset: Next.js (auto).
2. Environment variable:
   | Var | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://adpilot-api.onrender.com` |
3. Deploy. Note the URL, e.g. `https://adpilot.vercel.app`.

---

## 3. Wire them together

1. **Render** → `adpilot-api` → Environment → set
   `CORS_ORIGINS = https://adpilot.vercel.app` → save (redeploys).
2. Re-check: open the Vercel site, upload `sample_google_ads_report.csv`, confirm
   the audit renders (no CORS error in the browser console).

---

## 4. Twilio — inbound webhook

1. Twilio Console → **Messaging → Try it out → Send a WhatsApp message →
   Sandbox settings**.
2. **When a message comes in**: `https://adpilot-api.onrender.com/api/whatsapp/webhook`
   — method **POST**. Save.
3. (Optional, more secure) On Render set `WHATSAPP_VALIDATE_SIGNATURE=true` and
   `WHATSAPP_WEBHOOK_URL=https://adpilot-api.onrender.com/api/whatsapp/webhook`.
4. Re-join the demo phone: from it, WhatsApp `join <code>` to `+1 415 523 8886`
   (the join lapses after ~72h idle — do this again the morning of the demo).

---

## 5. Chrome extension

Edit `extension/config.js`:
```js
window.ADPILOT_CONFIG = {
  API_BASE: "https://adpilot-api.onrender.com",
  WEB_BASE: "https://adpilot.vercel.app",
};
```
Add `"https://adpilot-api.onrender.com/*"` to `host_permissions` in
`extension/manifest.json`. Reload the unpacked extension.

---

## 6. Full-rehearsal checklist (do this twice, without touching code)

From a **fresh browser profile** and a **phone that has never opted in**:

- [ ] Wake the backend (`/health`) a minute before starting.
- [ ] Landing → "Check my campaign" → upload the sample CSV.
- [ ] Audit screen shows **₹2,200 wasted** and the ranked cards. Toggle हिन्दी.
- [ ] Enter the WhatsApp number, opt in → confirmation message arrives.
- [ ] Trigger the alert: `POST https://adpilot-api.onrender.com/api/whatsapp/check`
      with `{"account_id":"<id>","force":true}` (or wait for the real one).
- [ ] Reply **PAUSE** from the phone → confirmation comes back.
- [ ] Reply **DETAILS** → explanation comes back.
- [ ] (Extension) click the icon, upload the sample, audit tab opens.

If any step fails on unfamiliar wifi, that's what rehearsal is for — fix it now,
not on stage.
