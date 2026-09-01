import type { Metadata } from "next";
import { UploadForm } from "@/components/UploadForm";

export const metadata: Metadata = {
  title: "Upload your report — AdPilot",
};

export default function UploadPage() {
  return (
    <div className="mx-auto max-w-2xl px-5 py-14">
      <h1 className="text-2xl font-bold">Upload your Google Ads report</h1>
      <p className="mt-2 text-[15px] text-muted">
        In Google Ads: open a campaign report with Campaign, Keyword, Search
        Term, Impressions, Clicks, Cost, Conversions and Conv. Value columns, then
        download it as a CSV.
      </p>

      <div className="mt-8">
        <UploadForm />
      </div>
    </div>
  );
}
