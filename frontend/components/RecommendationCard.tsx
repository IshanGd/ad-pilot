import type { RecommendationOut } from "@/lib/types";
import {
  RECOMMENDATION_ACTION,
  SEVERITY_STYLES,
  rupees,
} from "@/lib/format";

export function RecommendationCard({
  rec,
  rank,
}: {
  rec: RecommendationOut;
  rank: number;
}) {
  const sev = SEVERITY_STYLES[rec.severity];

  return (
    <article
      className={`rounded-xl border p-5 ${sev.bg} ${sev.border}`}
      aria-label={`Recommendation ${rank}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${sev.dot}`} aria-hidden />
        <span className={`text-xs font-semibold uppercase tracking-wide ${sev.text}`}>
          {sev.label}
        </span>
        <span className="ml-auto text-xs text-muted">{rec.campaign_name}</span>
      </div>

      <h3 className="mt-3 text-lg font-semibold text-foreground">
        {RECOMMENDATION_ACTION[rec.type]}: “{rec.label}”
      </h3>

      {rec.explanation && (
        <p className="mt-2 text-[15px] leading-relaxed text-foreground/80">
          {rec.explanation}
        </p>
      )}

      {rec.estimated_impact != null && (
        <p className="mt-3 text-sm font-medium text-foreground">
          {rec.type === "INCREASE_BUDGET"
            ? `Possible upside: about ${rupees(rec.estimated_impact)}`
            : `Money at stake: ${rupees(rec.estimated_impact)}`}
        </p>
      )}
    </article>
  );
}
