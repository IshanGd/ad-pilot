# AdPilot Chrome extension

Manifest V3 popup — a thin wrapper over the same backend the web app uses. It
does **not** scrape Google Ads pages or use OAuth (out of scope,
`01_PROJECT_REQUIREMENTS.md` §5).

## What it does

Popup (`popup.html`): pick your Google Ads CSV, optionally type a WhatsApp
number, hit **Analyze**. It uploads the report to `POST /api/campaign/upload` and
opens the full web audit result (`/audit/<account_id>`) in a new tab. If you
typed a number it's carried over as `?phone=` and pre-fills the opt-in box on
that page — opt-in still happens there with an explicit click (confidence ladder,
`03_RULES.md` §4).

## Load it (unpacked)

1. `chrome://extensions` → turn on **Developer mode**
2. **Load unpacked** → select this `extension/` folder
3. Pin the AdPilot icon, click it

The backend (`../backend`) and web app (`../frontend`) must be running.

## Config

`config.js` holds the two URLs (default: `127.0.0.1:8000` / `localhost:3000`).
After Phase 9 deployment:

- set `API_BASE` / `WEB_BASE` to the deployed URLs
- add the deployed API origin to `host_permissions` in `manifest.json`

## Files

```
manifest.json   MV3 manifest (popup + icons + host_permissions)
popup.html      single view, no navigation
popup.css       matches the web app's flat/light style
config.js       API_BASE / WEB_BASE (swap for prod)
popup.js        upload -> open audit tab
icons/          16 / 48 / 128 px
```
