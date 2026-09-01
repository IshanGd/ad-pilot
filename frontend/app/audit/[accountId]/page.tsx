import Link from "next/link";
import { analyze, ApiError } from "@/lib/api";
import { DEMO_ACCOUNT_ID, DEMO_AUDIT } from "@/lib/fixtures";
import { AuditResult } from "@/components/AuditResult";
import type { AnalyzeResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function AuditPage({
  params,
}: PageProps<"/audit/[accountId]">) {
  const { accountId } = await params;

  if (accountId === DEMO_ACCOUNT_ID) {
    return <AuditResult audit={DEMO_AUDIT} />;
  }

  let audit: AnalyzeResponse;
  try {
    audit = await analyze(accountId);
  } catch (err) {
    const notFound = err instanceof ApiError && err.status === 404;
    return (
      <div className="mx-auto max-w-2xl px-5 py-16">
        <h1 className="text-2xl font-bold">
          {notFound ? "That audit has expired" : "We couldn't run the audit"}
        </h1>
        <p className="mt-2 text-[15px] text-muted">
          {notFound
            ? "Audits aren't kept forever. Upload your report again to get a fresh one."
            : err instanceof Error
              ? err.message
              : "Please try uploading your report again."}
        </p>
        <Link
          href="/upload"
          className="mt-6 inline-block rounded-lg bg-brand px-5 py-2.5 text-[15px] font-medium text-white hover:opacity-90"
        >
          Upload a report
        </Link>
      </div>
    );
  }

  return <AuditResult audit={audit} />;
}
