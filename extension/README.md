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

`config.js` points at the **deployed** backend/frontend by default
(`adpilot-api-lv8o.onrender.com` / `ad-pilot-gamma.vercel.app`); a commented
block switches it to local. `manifest.json` `host_permissions` lists both the
deployed API origin and localhost, so the same unpacked extension works either
way — just edit `config.js` and reload the extension.

If you deploy to different URLs, update both `config.js` and the
`host_permissions` array.

## Files

```
manifest.json   MV3 manifest (popup + icons + host_permissions)
popup.html      single view, no navigation
popup.css       matches the web app's flat/light style
config.js       API_BASE / WEB_BASE (swap for prod)
popup.js        upload -> open audit tab
icons/          16 / 48 / 128 px
```
