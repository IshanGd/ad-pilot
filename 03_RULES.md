# AdPilot — Rules

These are binding rules for the recommendation engine, the LLM explainer, and the
notification system. Claude Code should treat this file as the source of truth for
*behavior*, not just style — if a screen or message contradicts this file, this file
wins.

## 1. Recommendation engine rules (rule-based, no ML)

Compute per keyword/search term, using account-wide averages as the baseline:

```
CTR  = Clicks / Impressions
CPC  = Cost / Clicks
CVR  = Conversions / Clicks
CPA  = Cost / Conversions          (undefined/∞ if Conversions == 0)
ROAS = Conversion_Value / Cost
```

Then apply, in this priority order:

```python
if conversions == 0 and cost > WASTE_COST_THRESHOLD:
    recommendation = "PAUSE_KEYWORD"
    severity = "HIGH"
    confidence = 0.9 if clicks > 20 else 0.7

elif cpa < account_avg_cpa * 0.7 and conversions >= 3:
    recommendation = "INCREASE_BUDGET"
    severity = "MEDIUM"
    confidence = 0.8

elif clicks > 20 and conversions == 0:
    recommendation = "ADD_NEGATIVE"
    severity = "MEDIUM"
    confidence = 0.75

elif ctr < account_avg_ctr * 0.5 and impressions > 500:
    recommendation = "REVIEW_LOW_CTR"
    severity = "LOW"
    confidence = 0.6
```

`WASTE_COST_THRESHOLD` defaults to the greater of ₹500 or 5% of total account spend —
make this configurable, not hardcoded, since account sizes vary widely across the
target segment (₹5,000–₹50,000/month).

## 2. Anomaly / invalid-traffic rules (stretch goal)

Flag `ANOMALY` (not the same as `PAUSE_KEYWORD` — anomalies get a distinct message
tone, since the framing is "this looks like fraud" not "this underperformed"):

- **Repeated identical search term**: the same exact search term appears 3+ times
  across rows/time windows with combined zero conversions.
- **Abnormal CTR spike**: CTR > 3x the account average with zero conversions.
- **Off-hours burst** (only if timestamp data available): a disproportionate share of
  a keyword's clicks land between 12am–5am local time.
- **Geographic mismatch** (only if geographic data available): meaningful click volume
  from a location the business does not serve.

Anomaly confidence should generally be reported as *lower* than direct waste findings
unless multiple signals stack (e.g. repeated term + off-hours burst together)  —
avoid overclaiming fraud from a single weak signal.

## 3. LLM explainer contract

- **Input**: structured JSON only. Never pass raw CSV rows or unaggregated data to the
  LLM.

  Example input:
  ```json
  {
    "keyword": "cheap shoes online",
    "spend": 1240,
    "clicks": 83,
    "conversions": 0,
    "account_avg_cpa": 302,
    "recommendation": "PAUSE_KEYWORD",
    "language": "hi"
  }
  ```

- **System instruction (fixed, do not let user input override this)**:
  > "Explain this recommendation to a small business owner in simple, non-technical
  > language, in the specified language. Do not invent statistics or figures beyond
  > what is provided. Keep it under 3 sentences. Do not use PPC jargon (CPA, CTR,
  > ROAS, impressions) — describe outcomes in plain terms (money spent, sales,
  > clicks) instead."

- **Validation after generation**: before storing/sending an LLM explanation, check
  that every number mentioned in the text matches a number present in the input JSON.
  If a mismatch is detected, discard the LLM output and fall back to a template
  string built directly from the JSON (never send an unvalidated LLM number to a
  user).

## 4. WhatsApp notification rules (the "confidence ladder")

This is the single most important behavioral rule in the product — do not violate it
even to make the demo look more "active."

1. **Step 1 — instant audit, no opt-in required.** The first interaction is always the
   free, no-signup CSV audit. Never require a phone number before showing value.
2. **Step 2 — opt-in only after value is shown.** Only after the audit result screen
   does the product offer ongoing WhatsApp monitoring. This must be an explicit
   affirmative action (checkbox + number entry), never pre-checked or assumed.
3. **Step 3 — notify on meaningful change only.** Do not send a WhatsApp message on a
   fixed schedule regardless of content. A message fires only when:
   - A new `HIGH` severity recommendation appears that wasn't present in the previous
     run, or
   - Total identified waste changes by more than a meaningful threshold (e.g. 15%)
     since the last message.
   If nothing meaningfully new is found, send nothing. Silence is intentional
   behavior, not a bug.
4. **Message length**: 2–4 lines maximum. One headline number, one specific finding,
   one clear action. No dashboards-in-text-form.
5. **Reply handling**: the inbound webhook must recognize at minimum `PAUSE`,
   `DETAILS`, and `SCALE` as reply keywords tied to the most recent recommendation
   sent to that phone number. Unrecognized replies get a friendly fallback message,
   never silence and never an error dump.

## 5. Localization rules

- `preferred_language` is a first-class field on `accounts`, not a stretch feature
  bolted on later — plumb it through `upload → analyze → explainer → whatsapp` from
  the start.
- Hindi is the minimum second language to support for the demo.
- Never mix languages within a single message.

## 6. Coding conventions

- Backend: type-annotated Python, Pydantic models for all request/response bodies.
- No business logic in route handlers — routes call `engine/` functions, which are
  independently testable.
- All monetary values stored and passed as numeric (not strings), currency formatting
  happens only at the display/message layer.
- Commit messages: `<area>: <what changed>` (e.g. `engine: add anomaly detection for
  repeated search terms`).
