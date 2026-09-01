import type { RecommendationType, Severity } from "./types";

const inr0 = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const num = new Intl.NumberFormat("en-IN");

/** "₹2,200" — Indian digit grouping, no paise. */
export function rupees(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return inr0.format(Math.round(value));
}

export function count(value: number): string {
  return num.format(Math.round(value));
}

export const SEVERITY_STYLES: Record<
  Severity,
  { label: string; text: string; bg: string; border: string; dot: string }
> = {
  HIGH: {
    label: "Urgent",
    text: "text-[var(--sev-high)]",
    bg: "bg-[var(--sev-high-bg)]",
    border: "border-[var(--sev-high)]",
    dot: "bg-[var(--sev-high)]",
  },
  MEDIUM: {
    label: "Worth doing",
    text: "text-[var(--sev-medium)]",
    bg: "bg-[var(--sev-medium-bg)]",
    border: "border-[var(--sev-medium)]",
    dot: "bg-[var(--sev-medium)]",
  },
  LOW: {
    label: "Have a look",
    text: "text-[var(--sev-low)]",
    bg: "bg-[var(--sev-low-bg)]",
    border: "border-[var(--border)]",
    dot: "bg-[var(--sev-low)]",
  },
};

/** Short, jargon-free action label. Never shows the raw enum. */
export const RECOMMENDATION_ACTION: Record<RecommendationType, string> = {
  PAUSE_KEYWORD: "Turn this off",
  ADD_NEGATIVE: "Block this search",
  INCREASE_BUDGET: "Give this more budget",
  REVIEW_LOW_CTR: "Review this keyword",
};
