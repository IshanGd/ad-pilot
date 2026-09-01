# AdPilot — Project Requirements

## 1. Problem statement

Small business owners running Google Ads lack the time and expertise to continuously
monitor and optimize their campaigns. This causes real, ongoing waste: money spent on
keywords and search terms that never convert, budgets left unbalanced between good and
bad campaigns, and no one watching the account between the day it was set up and the
day the bill arrives.

This is not a knowledge problem alone — it is a **time and attention** problem. Owners
who understand PPC terminology still don't have an extra hour a week to log in and
check. Existing tools (Optmyzr, Adalysis, WordStream, Adzooma) assume the user already
has conversion tracking set up, already logs into a dashboard, and can afford
$100+/month. That is not this user.

## 2. Target user

- Small business owner (India-first, but not India-only) spending roughly
  ₹5,000–₹50,000/month on Google Ads.
- Not a marketer. May not know what CPA, CTR, or ROAS mean, and does not want to learn
  a new dashboard.
- Runs the business day-to-day (retail, services, D2C) — checks a phone, not a laptop,
  during the day.
- May be more comfortable in a regional language than in English business jargon.
- Has NOT hired an agency or full-time marketer (this is the ceiling of our target
  segment — once they hire one, they graduate out of our product, and that's fine).

## 3. Core value proposition

> "You don't come to us. We come to you — on WhatsApp, in plain language, only when it
> matters."

Three things differentiate this from every existing tool in the space:
1. **Zero setup** — CSV upload, no OAuth, no login wall, works in the first 60 seconds.
2. **Zero dashboard required** — insights are pushed to WhatsApp, not pulled from a UI.
3. **Trust before commitment** — value is proven with one free instant audit before any
   ongoing automation is offered.

## 4. MVP scope (must build for the hackathon)

### Feature 1 — Instant audit (no login, no automation)
- User uploads a Google Ads CSV export (Campaign, Ad Group, Keyword, Search Term,
  Impressions, Clicks, Cost, Conversions, Conv. Value).
- Backend runs a rule-based analysis (see `03_RULES.md`).
- Output: one clear headline number ("₹X wasted this month") plus a ranked list of
  specific, explained recommendations.
- This step must work standalone, with no signup, as the trust-building first touch.

### Feature 2 — Recommendation engine
- Rule-based (not ML) detection of:
  - Zero-conversion keywords/search terms with meaningful spend ("PAUSE")
  - High-performing campaigns/keywords worth scaling ("SCALE")
  - Search terms suggesting intent mismatch ("NEGATIVE KEYWORD")
  - Optional stretch: anomaly patterns suggesting invalid traffic (repeated identical
    search terms, abnormal CTR spikes, off-hours click bursts) — see `03_RULES.md`.
- Each recommendation carries: type, confidence, estimated ₹ saved/gained, and a plain
  explanation.

### Feature 3 — LLM explainer layer
- Takes structured recommendation data (JSON) — never raw CSV — and produces a
  plain-language explanation.
- Must not invent numbers. Every figure in the explanation must come from the
  structured input.
- Must support at least one non-English language output (Hindi at minimum) as a
  first-class option, not an afterthought.

### Feature 4 — WhatsApp delivery (Twilio Sandbox)
- After the instant audit, user is offered (opt-in, not automatic) recurring
  monitoring via WhatsApp.
- Delivered messages are short (2–4 lines), one clear number, one clear action.
- Messages fire only on meaningful new findings — not on a fixed schedule regardless of
  content (see confidence-ladder rules in `03_RULES.md`).

### Feature 5 — Reply-to-act loop (at least simulated)
- User can reply to a WhatsApp message with a short keyword (e.g. `PAUSE`, `DETAILS`)
  to trigger an action or get more information.
- For the hackathon, the actual Google Ads mutation can be **simulated** — clearly
  labelled as such in the pitch — since live account write access is out of scope for
  48 hours. The reply-and-acknowledge loop must still work end-to-end.

### Feature 6 — Minimal Chrome extension (UI wrapper only)
- A popup with: CSV upload control, WhatsApp number input, "Analyze" button.
- Calls the same backend as the web flow. Not responsible for scraping or live
  Google Ads account access.

## 5. Explicitly out of scope for 48 hours

- Google Ads OAuth / live API read or write access.
- Any ML/deep-learning model (rules + LLM explanation only).
- Multi-platform ad support (Meta, LinkedIn, etc.).
- Billing, payments, or subscription logic.
- User accounts with persistent login (a phone number is the only identifier needed
  for the MVP).
- Real WhatsApp Business API (use Twilio Sandbox only).
- Native mobile app.

## 6. Success criteria (what "done" looks like for the demo)

- A judge can upload the sample CSV and see a headline waste number and 3+ ranked
  recommendations within seconds.
- A judge can trigger (or watch a pre-triggered) WhatsApp message arrive with a
  plain-language summary.
- A judge can reply to that WhatsApp message and see a response come back.
- The full loop (CSV → analysis → WhatsApp → reply → response) must survive a live
  demo on unfamiliar wifi — deploy and test this before the pitch, not during it.

## 7. Non-functional requirements

- Analysis must run in under 5 seconds for a CSV of a few hundred rows.
- No sensitive data (real ad account credentials, payment info) is ever collected.
- All LLM-generated text must be traceable back to structured numeric input — no
  hallucinated figures, ever, in any generated message.
