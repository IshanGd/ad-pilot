import Link from "next/link";
import type { AnalyzeResponse } from "@/lib/types";
import { count, rupees } from "@/lib/format";
import { RecommendationCard } from "./RecommendationCard";
import { WhatsAppOptIn } from "./WhatsAppOptIn";

export function AuditResult({ audit }: { audit: AnalyzeResponse }) {
  const wasted = audit.total_waste_identified;
  const hasWaste = wasted > 0;

  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      {/* 1. Headline — largest thing on the page. */}
      <section>
        <p className="text-sm font-medium uppercase tracking-wide text-muted">
          Your instant audit
        </p>
        <h1 className="mt-2 text-4xl font-bold leading-tight sm:text-5xl">
          {hasWaste ? (
            <>
              You&apos;ve wasted{" "}
              <span className="text-[var(--sev-high)]">{rupees(wasted)}</span>{" "}
              this month.
            </>
          ) : (
            <>No obvious waste this month.</>
          )}
        </h1>
        <p className="mt-3 text-[15px] text-muted">
          We checked {count(audit.analyzed_keywords)} keywords and found{" "}
          {count(audit.recommendation_count)}{" "}
          {audit.recommendation_count === 1 ? "thing" : "things"} worth your
          attention.
        </p>
      </section>

      {/* 2. Ranked recommendation cards. */}
      <section className="mt-8 space-y-4">
        {audit.recommendations.map((rec, i) => (
          <RecommendationCard key={rec.id} rec={rec} rank={i + 1} />
        ))}
        {audit.recommendations.length === 0 && (
          <p className="rounded-xl border border-border bg-surface p-5 text-[15px] text-muted">
            Nothing needs changing right now. Check back after your next report.
          </p>
        )}
      </section>

      {/* 3. WhatsApp opt-in — always below the results, never required. */}
      <section className="mt-10">
        <h2 className="text-lg font-semibold">Keep an eye on it for me</h2>
        <p className="mt-1 mb-3 text-sm text-muted">
          The audit above is free and yours to keep. This part is optional.
        </p>
        <WhatsAppOptIn />
      </section>

      <div className="mt-10 text-sm text-muted">
        <Link href="/upload" className="text-brand hover:underline">
          Upload a different report
        </Link>
      </div>
    </div>
  );
}
