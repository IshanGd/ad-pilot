"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Language } from "@/lib/api";

const OPTIONS: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी" },
];

export function LanguageToggle({ current }: { current: Language }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  function choose(lang: Language) {
    if (lang === current) return;
    const next = new URLSearchParams(params);
    if (lang === "en") next.delete("lang");
    else next.set("lang", lang);
    router.push(`${pathname}?${next.toString()}`);
  }

  return (
    <div className="inline-flex rounded-lg border border-border bg-surface p-0.5 text-sm">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => choose(o.value)}
          className={`rounded-md px-3 py-1 ${
            o.value === current
              ? "bg-brand text-white"
              : "text-muted hover:text-foreground"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
