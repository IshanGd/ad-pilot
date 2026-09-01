# AdPilot — Design

## 1. Design principles

- **The output is a decision, not a dashboard.** Never make the user interpret a
  chart to figure out what to do — always hand them the action directly.
- **No PPC jargon anywhere a business owner will read it.** "CPA," "CTR," "ROAS" stay
  internal to the code and the LLM prompt input — never in UI copy or WhatsApp
  messages. Use "cost per sale," "click rate," "money spent," "sales" instead.
- **One number per screen, stated first.** Every screen should have one clear
  headline figure before any supporting detail.
- **Plain language, not startup language.** No "leverage," "synergy," "optimize your
  funnel." Write the way you'd explain it to a shopkeeper across a counter.

## 2. Screens (web app)

### Screen 1 — Landing
- Hero line: "Stop wasting money on Google Ads."
- Subline: "Upload your ads report and see exactly where your money is going — free,
  no signup."
- Single CTA button: "Check my campaign"

### Screen 2 — Upload
- Drag-and-drop CSV area.
- "Download sample report" link (uses `sample_data/sample_google_ads_report.csv`) —
  critical for the demo and for first-time visitors who want to see the tool before
  trusting it with real data.
- No login field. No phone number field yet — that comes only after Screen 3.

### Screen 3 — Instant audit result (the most important screen)
Layout, top to bottom:
1. Headline: "You've wasted ₹X this month." (largest text on the page)
2. Three or four ranked recommendation cards, each with:
   - Severity indicator (color, not just a word)
   - Plain-language explanation (from the LLM explainer)
   - Estimated ₹ impact
3. Below the recommendations, the WhatsApp opt-in offer (see section 4) — never
   above the results, and never required to see the results.

### Screen 4 — Budget optimizer (secondary priority — build after Screens 1–3 and the
WhatsApp loop are solid)
- Input: total monthly budget.
- Output: current vs. suggested split across campaigns, with a one-line reason per
  campaign ("gets sales for less than half your average cost").

### Screen 5 — Simulator (secondary priority)
- Current vs. projected cost-per-sale and sales count.
- Label clearly as "Projected impact," never a guarantee.

## 3. Chrome extension popup

- Single view, no navigation: file upload control, phone number input (optional),
  "Analyze" button.
- On submit, either show a condensed result inline in the popup or open the full web
  result screen in a new tab — pick whichever is faster to build; do not build both.

## 4. WhatsApp opt-in UX (confidence ladder, step 2)

Shown only on Screen 3, after results are visible:

> "Want me to keep watching this and text you on WhatsApp if something like this
> happens again? [Phone number input] [Yes, keep me posted]"

No pre-checked box. No urgency language ("Don't miss out"). The offer should read as
optional and low-pressure, matching the trust-building principle in
`01_PROJECT_REQUIREMENTS.md`.

## 5. WhatsApp message templates

Keep every message to 2–4 lines. Use the account's `preferred_language`.

**Waste alert:**
> AdPilot: "cheap shoes online" spent ₹1,240 with zero sales this week.
> Reply PAUSE to stop it, or DETAILS for more.

**Weekly-style summary (only sent if something meaningfully new was found):**
> AdPilot check-in: You spent ₹18,420, got 61 sales this month.
> New: Campaign C is outperforming — consider giving it more budget.
> Reply DETAILS for the full picture.

**Reply confirmation (simulated action):**
> Done — "cheap shoes online" paused (simulated for demo).
> Estimated saving: ₹1,240/month.

**Unrecognized reply fallback:**
> Sorry, I didn't catch that. Reply PAUSE, SCALE, or DETAILS about your last update.

**Anomaly-flavored message (distinct tone — concern, not just underperformance):**
> AdPilot noticed something odd: the search "cheap shoes online" was searched
> word-for-word 3 times with zero sales. This can be a sign of invalid clicks.
> Reply DETAILS to see why.

## 6. Visual style (web app)

- Flat, uncluttered, generous white space — this is a tool for someone who doesn't
  want to think hard about a dashboard.
- Color used for meaning, not decoration: red/amber/green tied consistently to
  severity across every screen and message.
- Large, simple numerals for the headline metric on every screen — this is the
  first thing a busy person should be able to read at a glance.

## 7. Demo / pitch beats (for Phase 10 rehearsal)

1. **Problem** (20s): a small business owner spending ₹20,000/month with no time to
   watch every keyword.
2. **Solution intro** (15s): "We built AdPilot — upload your report, we tell you
   exactly what's wrong, and then we watch it for you over WhatsApp."
3. **Live demo** (60–90s): upload sample CSV → show headline waste number → show one
   recommendation card → show a real WhatsApp message arriving → reply to it live →
   show the confirmation come back.
4. **Why this matters** (20s): "Every existing tool assumes you already track
   conversions and already log into a dashboard. Ours assumes neither — because most
   small businesses have neither."
5. **Close** (10s): "Small businesses shouldn't need a marketing expert, or even a
   dashboard, to know where their money is going."

Keep the whole demo under 3 minutes. Stop talking before the timer forces you to.
