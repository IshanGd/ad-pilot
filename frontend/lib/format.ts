import type { Severity } from "./types";

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
  { text: string; bg: string; border: string; dot: string }
> = {
  HIGH: {
    text: "text-[var(--sev-high)]",
    bg: "bg-[var(--sev-high-bg)]",
    border: "border-[var(--sev-high)]",
    dot: "bg-[var(--sev-high)]",
  },
  MEDIUM: {
    text: "text-[var(--sev-medium)]",
    bg: "bg-[var(--sev-medium-bg)]",
    border: "border-[var(--sev-medium)]",
    dot: "bg-[var(--sev-medium)]",
  },
  LOW: {
    text: "text-[var(--sev-low)]",
    bg: "bg-[var(--sev-low-bg)]",
    border: "border-[var(--border)]",
    dot: "bg-[var(--sev-low)]",
  },
};
