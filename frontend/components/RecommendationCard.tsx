import type { Language } from "@/lib/api";
import type { RecommendationOut, RecommendationType } from "@/lib/types";
import { SEVERITY_STYLES, rupees } from "@/lib/format";

const SEVERITY_LABEL: Record<Language, Record<string, string>> = {
  en: { HIGH: "Urgent", MEDIUM: "Worth doing", LOW: "Have a look" },
  hi: { HIGH: "ज़रूरी", MEDIUM: "करने लायक", LOW: "एक नज़र डालें" },
};

const ACTION: Record<Language, Record<RecommendationType, string>> = {
  en: {
    PAUSE_KEYWORD: "Turn this off",
    ADD_NEGATIVE: "Block this search",
    INCREASE_BUDGET: "Give this more budget",
    REVIEW_LOW_CTR: "Review this keyword",
  },
  hi: {
    PAUSE_KEYWORD: "इसे बंद करें",
    ADD_NEGATIVE: "यह खोज ब्लॉक करें",
    INCREASE_BUDGET: "इस पर ज़्यादा बजट दें",
    REVIEW_LOW_CTR: "यह कीवर्ड जाँचें",
  },
};

const IMPACT = {
  en: { stake: "Money at stake", upside: "Possible upside: about" },
  hi: { stake: "दाँव पर पैसा", upside: "संभावित लाभ: लगभग" },
};

export function RecommendationCard({
  rec,
  rank,
  language,
}: {
  rec: RecommendationOut;
  rank: number;
  language: Language;
}) {
  const sev = SEVERITY_STYLES[rec.severity];
  const impact = IMPACT[language];

  return (
    <article
      className={`rounded-xl border p-5 ${sev.bg} ${sev.border}`}
      aria-label={`Recommendation ${rank}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${sev.dot}`} aria-hidden />
        <span className={`text-xs font-semibold uppercase tracking-wide ${sev.text}`}>
          {SEVERITY_LABEL[language][rec.severity]}
        </span>
        <span className="ml-auto text-xs text-muted">{rec.campaign_name}</span>
      </div>

      <h3 className="mt-3 text-lg font-semibold text-foreground">
        {ACTION[language][rec.type]}: “{rec.label}”
      </h3>

      {rec.explanation && (
        <p className="mt-2 text-[15px] leading-relaxed text-foreground/80">
          {rec.explanation}
        </p>
      )}

      {rec.estimated_impact != null && (
        <p className="mt-3 text-sm font-medium text-foreground">
          {rec.type === "INCREASE_BUDGET"
            ? `${impact.upside} ${rupees(rec.estimated_impact)}`
            : `${impact.stake}: ${rupees(rec.estimated_impact)}`}
        </p>
      )}
    </article>
  );
}
