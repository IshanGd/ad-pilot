"use client";

import { useState } from "react";

/*
 * 05_DESIGN.md section 4 — the confidence ladder, step 2. Shown only after the
 * audit result is visible, never pre-checked, no urgency language.
 *
 * Phase 5 wires the submit to POST /api/whatsapp/opt-in. Until then it just
 * acknowledges so the screen layout and copy are locked in.
 */
export function WhatsAppOptIn() {
  const [phone, setPhone] = useState("");
  const [done, setDone] = useState(false);

  if (done) {
    return (
      <div className="rounded-xl border border-border bg-surface p-5 text-sm text-muted">
        Thanks — WhatsApp updates aren&apos;t switched on in this build yet, but
        your number is noted for when they are.
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
      <p className="text-[15px] text-foreground">
        Want me to keep watching this and text you on WhatsApp if something like
        this happens again?
      </p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          type="tel"
          inputMode="tel"
          required
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="Your WhatsApp number"
          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-[15px] outline-none focus:border-brand"
        />
        <button
          type="submit"
          className="rounded-lg bg-brand px-4 py-2 text-[15px] font-medium text-white hover:opacity-90"
        >
          Yes, keep me posted
        </button>
      </div>
      <p className="mt-2 text-xs text-muted">
        Optional. No spam — you&apos;ll only hear from us when something changes.
      </p>
    </form>
  );
}
