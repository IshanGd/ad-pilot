import Link from "next/link";
import { DEMO_AUDIT } from "@/lib/fixtures";
import { rupees, SEVERITY_STYLES } from "@/lib/format";

const PREVIEW_ACTION: Record<string, string> = {
  PAUSE_KEYWORD: "Turn off",
  ADD_NEGATIVE: "Block",
  INCREASE_BUDGET: "Scale up",
  REVIEW_LOW_CTR: "Review",
};

const STEPS = [
  {
    n: 1,
    t: "Upload one report",
    d: "Export your campaign report from Google Ads and drop the file in. No login, no phone number.",
  },
  {
    n: 2,
    t: "See what's wrong",
    d: "One number for what you're wasting this month, and a short ranked list of what to do about it.",
  },
  {
    n: 3,
    t: "We keep watching",
    d: "Opt in afterwards and we message you on WhatsApp — only when something actually changes.",
  },
];

export default function LandingPage() {
  const preview = DEMO_AUDIT.recommendations.slice(0, 3);

  return (
    <div className="mx-auto max-w-5xl px-5 py-16 sm:py-24">
      <section className="grid items-start gap-12 lg:grid-cols-2">
        {/* Hero copy */}
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-muted">
            Free instant audit
          </p>
          <h1 className="mt-3 text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl">
            Stop wasting money on Google Ads.
          </h1>
          <p className="mt-4 max-w-md text-lg text-muted">
            Upload your ads report and see exactly where your money is going —
            free, no signup.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/upload"
              className="rounded-lg bg-brand px-6 py-3 text-base font-medium text-white hover:opacity-90"
            >
              Check my campaign
            </Link>
            <Link
              href="/audit/demo"
              className="text-base font-medium text-brand hover:underline"
            >
              See a sample audit →
            </Link>
          </div>
        </div>

        {/* Audit preview — the payoff, shown before you commit anything */}
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            What you&apos;ll see
          </p>
          <p className="mt-2 text-3xl font-bold leading-tight">
            You&apos;ve wasted{" "}
            <span className="text-[var(--sev-high)]">
              {rupees(DEMO_AUDIT.total_waste_identified)}
            </span>{" "}
            this month.
          </p>

          <ul className="mt-5 space-y-3">
            {preview.map((rec) => {
              const sev = SEVERITY_STYLES[rec.severity];
              return (
                <li key={rec.id} className="flex items-start gap-3 text-sm">
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${sev.dot}`}
                    aria-hidden
                  />
                  <span className="flex-1">
                    <span className="font-medium text-foreground">
                      {PREVIEW_ACTION[rec.type] ?? "Review"}
                    </span>{" "}
                    <span className="text-muted">
                      “{rec.label}”
                      {rec.estimated_impact != null &&
                        ` — ${rupees(rec.estimated_impact)}`}
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>

          <p className="mt-5 text-xs text-muted">
            Sample data. Your report is analysed the same way in a few seconds.
          </p>
        </div>
      </section>

      {/* How it works */}
      <section className="mt-24">
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted">
          How it works
        </h2>
        <div className="mt-6 grid gap-6 sm:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="rounded-xl border border-border bg-surface p-5">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand/10 text-sm font-semibold text-brand">
                {s.n}
              </span>
              <h3 className="mt-3 text-base font-semibold">{s.t}</h3>
              <p className="mt-1.5 text-sm text-muted">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Closing */}
      <section className="mt-20 rounded-2xl border border-border bg-surface p-8 text-center">
        <p className="text-xl font-semibold">
          Find out what your ads are wasting — in about a minute.
        </p>
        <Link
          href="/upload"
          className="mt-5 inline-block rounded-lg bg-brand px-6 py-3 text-base font-medium text-white hover:opacity-90"
        >
          Check my campaign
        </Link>
      </section>
    </div>
  );
}
