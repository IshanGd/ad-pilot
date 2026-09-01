"use client";

import { useState } from "react";
import type { Language } from "@/lib/api";

/*
 * 05_DESIGN.md section 4 — the confidence ladder, step 2. Shown only after the
 * audit result is visible, never pre-checked, no urgency language.
 *
 * Phase 5 wires the submit to POST /api/whatsapp/opt-in. Until then it just
 * acknowledges so the screen layout and copy are locked in.
 */
const STRINGS = {
  en: {
    prompt:
      "Want me to keep watching this and text you on WhatsApp if something like this happens again?",
    placeholder: "Your WhatsApp number",
    button: "Yes, keep me posted",
    fine: "Optional. No spam — you'll only hear from us when something changes.",
    done: "Thanks — WhatsApp updates aren't switched on in this build yet, but your number is noted for when they are.",
  },
  hi: {
    prompt:
      "क्या मैं इस पर नज़र रखूँ और ऐसा दोबारा होने पर आपको WhatsApp पर बताऊँ?",
    placeholder: "आपका WhatsApp नंबर",
    button: "हाँ, मुझे बताते रहें",
    fine: "वैकल्पिक। कोई स्पैम नहीं — कुछ बदलने पर ही संदेश आएगा।",
    done: "धन्यवाद — इस बिल्ड में WhatsApp अपडेट अभी चालू नहीं हैं, पर आपका नंबर नोट कर लिया गया है।",
  },
};

export function WhatsAppOptIn({ language }: { language: Language }) {
  const t = STRINGS[language];
  const [phone, setPhone] = useState("");
  const [done, setDone] = useState(false);

  if (done) {
    return (
      <div className="rounded-xl border border-border bg-surface p-5 text-sm text-muted">
        {t.done}
      </div>
    );
  }

  return (
    <form
      className="rounded-xl border border-border bg-surface p-5"
      onSubmit={(e) => {
        e.preventDefault();
        // Phase 5: POST /api/whatsapp/opt-in { phone_number, preferred_language }
        setDone(true);
      }}
    >
      <p className="text-[15px] text-foreground">{t.prompt}</p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          type="tel"
          inputMode="tel"
          required
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder={t.placeholder}
          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-[15px] outline-none focus:border-brand"
        />
        <button
          type="submit"
          className="rounded-lg bg-brand px-4 py-2 text-[15px] font-medium text-white hover:opacity-90"
        >
          {t.button}
        </button>
      </div>
      <p className="mt-2 text-xs text-muted">{t.fine}</p>
    </form>
  );
}
