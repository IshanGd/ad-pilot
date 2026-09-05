import type { AnalyzeResponse, UploadResponse } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

/** Public URL of the bundled sample report, served from /public. */
export const SAMPLE_CSV_PATH = "/sample_google_ads_report.csv";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return body.detail[0]?.msg ?? res.statusText;
  } catch {
    /* fall through */
  }
  return res.statusText || `Request failed (${res.status})`;
}

export interface UploadOptions {
  accountId?: string;
  businessName?: string;
  preferredLanguage?: string;
}

export async function uploadCsv(
  file: File,
  opts: UploadOptions = {},
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (opts.accountId) form.append("account_id", opts.accountId);
  if (opts.businessName) form.append("business_name", opts.businessName);
  if (opts.preferredLanguage)
    form.append("preferred_language", opts.preferredLanguage);

  const res = await fetch(`${API_BASE}/api/campaign/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new ApiError(await readError(res), res.status);
  return res.json();
}

export type Language = "en" | "hi";

export async function analyze(
  accountId: string,
  language?: Language,
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      account_id: accountId,
      ...(language ? { language } : {}),
    }),
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(await readError(res), res.status);
  return res.json();
}

export interface OptInResponse {
  account_id: string;
  phone_number: string;
  notify_opt_in: boolean;
  preferred_language: string;
  confirmation_sent: boolean;
  warning: string | null;
}

export async function whatsappOptIn(
  accountId: string,
  phoneNumber: string,
  language?: Language,
): Promise<OptInResponse> {
  const res = await fetch(`${API_BASE}/api/whatsapp/opt-in`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      account_id: accountId,
      phone_number: phoneNumber,
      ...(language ? { language } : {}),
    }),
  });
  if (!res.ok) throw new ApiError(await readError(res), res.status);
  return res.json();
}

export { ApiError };
