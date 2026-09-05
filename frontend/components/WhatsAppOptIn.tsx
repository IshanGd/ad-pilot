"use client";

import { useState } from "react";
import { ApiError, whatsappOptIn, type Language } from "@/lib/api";

/*
 * 05_DESIGN.md section 4 — the confidence ladder, step 2. Shown only after the
 * audit result is visible, never pre-checked, no urgency language. On submit it
 * calls POST /api/whatsapp/opt-in.
 */
const STRINGS = {
  en: {
    prompt:
      "Want me to keep watching this and text you on WhatsApp if something like this happens again?",
    placeholder: "Your WhatsApp number",
    button: "Yes, keep me posted",
    sending: "Saving…",
    fine: "Optional. No spam — you'll only hear from us when something changes.",
    ok: "You're in. We'll message this number only when something changes.",
    okSent: "You're in — check WhatsApp for a confirmation. We'll only message when something changes.",
    error: "Couldn't save that. Please check the number and try again.",
  },
  hi: {
    prompt:
      "क्या मैं इस पर नज़र रखूँ और ऐसा दोबारा होने पर आपको WhatsApp पर बताऊँ?",
    placeholder: "आपका WhatsApp नंबर",
    button: "हाँ, मुझे बताते रहें",
    sending: "सहेजा जा रहा है…",
    fine: "वैकल्पिक। कोई स्पैम नहीं — कुछ बदलने पर ही संदेश आएगा।",
    ok: "हो गया। हम इस नंबर पर सिर्फ़ कुछ बदलने पर ही संदेश भेजेंगे।",
    okSent: "हो गया — WhatsApp पर पुष्टि देखें। कुछ बदलने पर ही संदेश आएगा।",
    error: "सहेजा नहीं जा सका। नंबर जाँचकर दोबारा कोशिश करें।",
  },
};

type State =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "done"; confirmationSent: boolean; warning: string | null }
  | { kind: "error"; message: string };

export function WhatsAppOptIn({
  accountId,
  language,
}: {
  accountId: string;
  language: Language;
}) {
  const t = STRINGS[language];
  const [phone, setPhone] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  if (state.kind === "done") {
    return (
      <div className="rounded-xl border border-border bg-surface p-5 text-sm">
        <p className="text-foreground">
          {state.confirmationSent ? t.okSent : t.ok}
        </p>
        {state.warning && (
          <p className="mt-1 text-muted">{state.warning}</p>
        )}
      </div>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setState({ kind: "sending" });
    try {
      const res = await whatsappOptIn(accountId, phone, language);
      setState({
        kind: "done",
        confirmationSent: res.confirmation_sent,
        warning: res.warning,
      });
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof ApiError ? err.message : t.error,
      });
    }
  }

  const busy = state.kind === "sending";

  return (
    <form className="rounded-xl border border-border bg-surface p-5" onSubmit={submit}>
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
          disabled={busy}
          className="rounded-lg bg-brand px-4 py-2 text-[15px] font-medium text-white hover:opacity-90 disabled:opacity-60"
        >
          {busy ? t.sending : t.button}
        </button>
      </div>
      {state.kind === "error" && (
        <p className="mt-2 text-sm text-[var(--sev-high)]">{state.message}</p>
      )}
      <p className="mt-2 text-xs text-muted">{t.fine}</p>
    </form>
  );
}
