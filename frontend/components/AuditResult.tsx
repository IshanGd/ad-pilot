import Link from "next/link";
import type { Language } from "@/lib/api";
import type { AnalyzeResponse } from "@/lib/types";
import { count, rupees } from "@/lib/format";
import { RecommendationCard } from "./RecommendationCard";
import { WhatsAppOptIn } from "./WhatsAppOptIn";
import { LanguageToggle } from "./LanguageToggle";

const STRINGS = {
  en: {
    kicker: "Your instant audit",
    wastedPre: "You've wasted ",
    wastedPost: " this month.",
    noWaste: "No obvious waste this month.",
    checked: (kw: string, n: string, one: boolean) =>
      `We checked ${kw} keywords and found ${n} ${one ? "thing" : "things"} worth your attention.`,
    nothing:
      "Nothing needs changing right now. Check back after your next report.",
    watchTitle: "Keep an eye on it for me",
    watchSub: "The audit above is free and yours to keep. This part is optional.",
    plan: "See a budget plan",
    another: "Upload a different report",
  },
  hi: {
    kicker: "आपका तुरंत ऑडिट",
    wastedPre: "इस महीने आपके ",
    wastedPost: " बर्बाद हुए।",
    noWaste: "इस महीने कोई साफ़ बर्बादी नहीं दिखी।",
    checked: (kw: string, n: string) =>
      `हमने ${kw} कीवर्ड देखे और ${n} बातें मिलीं जिन पर ध्यान देना चाहिए।`,
    nothing: "अभी कुछ बदलने की ज़रूरत नहीं। अगली रिपोर्ट के बाद फिर देखें।",
    watchTitle: "मेरे लिए इस पर नज़र रखें",
    watchSub: "ऊपर का ऑडिट मुफ़्त है और आपका है। यह हिस्सा वैकल्पिक है।",
    plan: "बजट योजना देखें",
    another: "दूसरी रिपोर्ट अपलोड करें",
  },
};

export function AuditResult({
  audit,
  language,
  initialPhone,
}: {
  audit: AnalyzeResponse;
  language: Language;
  initialPhone?: string;
}) {
  const t = STRINGS[language];
  const wasted = audit.total_waste_identified;
  const hasWaste = wasted > 0;
  const one = audit.recommendation_count === 1;

  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <section>
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm font-medium uppercase tracking-wide text-muted">
            {t.kicker}
          </p>
          <LanguageToggle current={language} />
        </div>
        <h1 className="mt-2 text-4xl font-bold leading-tight sm:text-5xl">
          {hasWaste ? (
            <>
              {t.wastedPre}
              <span className="text-[var(--sev-high)]">{rupees(wasted)}</span>
              {t.wastedPost}
            </>
          ) : (
            t.noWaste
          )}
        </h1>
        <p className="mt-3 text-[15px] text-muted">
          {t.checked(count(audit.analyzed_keywords), count(audit.recommendation_count), one)}
        </p>
      </section>

      <section className="mt-8 space-y-4">
        {audit.recommendations.map((rec, i) => (
          <RecommendationCard
            key={rec.id}
            rec={rec}
            rank={i + 1}
            language={language}
          />
        ))}
        {audit.recommendations.length === 0 && (
          <p className="rounded-xl border border-border bg-surface p-5 text-[15px] text-muted">
            {t.nothing}
          </p>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">{t.watchTitle}</h2>
        <p className="mt-1 mb-3 text-sm text-muted">{t.watchSub}</p>
        <WhatsAppOptIn
          accountId={audit.account_id}
          language={language}
          initialPhone={initialPhone}
        />
      </section>

      <div className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        {audit.recommendations.length > 0 && (
          <Link
            href={`/plan/${audit.account_id}`}
            className="font-medium text-brand hover:underline"
          >
            {t.plan} →
          </Link>
        )}
        <Link href="/upload" className="text-muted hover:underline">
          {t.another}
        </Link>
      </div>
    </div>
  );
}
