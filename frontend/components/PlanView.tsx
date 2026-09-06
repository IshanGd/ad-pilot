"use client";

import Link from "next/link";
import { useState } from "react";
import { ApiError, optimizeBudget } from "@/lib/api";
import { count, rupees } from "@/lib/format";
import type { BudgetOptimizeResponse, SimulationResponse } from "@/lib/types";

const REASON_STYLE: Record<string, string> = {
  SCALE_UP: "text-[var(--sev-medium)]",
  TRIM: "text-[var(--sev-low)]",
  PAUSE: "text-[var(--sev-high)]",
  AVERAGE: "text-muted",
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-0.5 text-2xl font-bold">{value}</p>
    </div>
  );
}

export function PlanView({
  accountId,
  simulation,
  initialBudget,
}: {
  accountId: string;
  simulation: SimulationResponse;
  initialBudget: BudgetOptimizeResponse;
}) {
  const s = simulation;
  const [budget, setBudget] = useState(
    String(Math.round(initialBudget.total_budget)),
  );
  const [plan, setPlan] = useState(initialBudget);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function update(e: React.FormEvent) {
    e.preventDefault();
    const value = Number(budget);
    if (!Number.isFinite(value) || value <= 0) {
      setError("Enter a monthly budget above zero.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setPlan(await optimizeBudget(accountId, value));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't update the plan.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <p className="text-sm font-medium uppercase tracking-wide text-muted">
        Projected impact
      </p>

      {/* Simulator — one headline, then the supporting pair */}
      <h1 className="mt-2 text-3xl font-bold leading-tight sm:text-4xl">
        {s.current_cpa != null && s.projected_cpa != null ? (
          <>
            Your cost per sale could go from{" "}
            <span className="text-[var(--sev-low)]">{rupees(s.current_cpa)}</span>{" "}
            to{" "}
            <span className="text-[var(--sev-medium)]">
              {rupees(s.projected_cpa)}
            </span>
            .
          </>
        ) : (
          <>Fix the waste and your cost per sale drops.</>
        )}
      </h1>

      <div className="mt-6 grid grid-cols-2 gap-6 rounded-xl border border-border bg-surface p-5 sm:grid-cols-4">
        <Stat label="Sales now" value={count(s.current_conversions)} />
        <Stat label="Projected sales" value={count(s.projected_conversions)} />
        <Stat label="Cost per sale now" value={rupees(s.current_cpa)} />
        <Stat label="Projected" value={rupees(s.projected_cpa)} />
      </div>

      <ul className="mt-4 space-y-1.5 text-sm text-muted">
        {s.assumptions.map((a, i) => (
          <li key={i} className="flex gap-2">
            <span aria-hidden>•</span>
            <span>{a}</span>
          </li>
        ))}
      </ul>

      {/* Budget optimiser */}
      <section className="mt-12">
        <h2 className="text-lg font-semibold">Where your budget should go</h2>
        <p className="mt-1 text-sm text-muted">
          You&apos;re spending {rupees(plan.current_total_spend)} a month now.
          Enter a budget and we&apos;ll split it across your campaigns.
        </p>

        <form onSubmit={update} className="mt-4 flex flex-wrap items-center gap-2">
          <div className="flex items-center rounded-lg border border-border bg-surface px-3">
            <span className="text-muted">₹</span>
            <input
              type="number"
              min={1}
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="w-32 bg-transparent px-2 py-2 text-[15px] outline-none"
              aria-label="Monthly budget"
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-brand px-4 py-2 text-[15px] font-medium text-white hover:opacity-90 disabled:opacity-60"
          >
            {busy ? "Updating…" : "Update plan"}
          </button>
        </form>
        {error && (
          <p className="mt-2 text-sm text-[var(--sev-high)]">{error}</p>
        )}

        <div className="mt-5 space-y-3">
          {plan.allocations.map((a) => (
            <div
              key={a.campaign_id}
              className="rounded-xl border border-border bg-surface p-4"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-medium">{a.name}</span>
                <span className="text-sm">
                  <span className="text-muted">{rupees(a.current_spend)}</span>
                  <span className="mx-1.5 text-muted">→</span>
                  <span className="font-semibold">
                    {rupees(a.suggested_budget)}
                  </span>
                </span>
              </div>

              <div className="mt-2 flex items-center gap-3">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
                  <div
                    className={`h-full ${
                      a.reason_code === "PAUSE"
                        ? "bg-[var(--sev-high)]"
                        : "bg-brand"
                    }`}
                    style={{ width: `${Math.round(a.suggested_share * 100)}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-xs text-muted">
                  {Math.round(a.suggested_share * 100)}%
                </span>
              </div>

              <p
                className={`mt-2 text-sm ${REASON_STYLE[a.reason_code] ?? "text-muted"}`}
              >
                {a.reason}
              </p>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-10 text-sm">
        <Link href={`/audit/${accountId}`} className="text-brand hover:underline">
          ← Back to the audit
        </Link>
      </div>
    </div>
  );
}
