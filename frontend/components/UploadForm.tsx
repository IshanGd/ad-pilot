"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { SAMPLE_CSV_PATH, uploadCsv } from "@/lib/api";

type State =
  | { kind: "idle" }
  | { kind: "uploading"; name: string }
  | { kind: "error"; message: string };

export function UploadForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<State>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);

  async function handleFile(file: File) {
    const name = file.name.toLowerCase();
    if (!name.endsWith(".csv") && !name.endsWith(".tsv") && !name.endsWith(".txt")) {
      setState({ kind: "error", message: "Please choose the .csv file you exported from Google Ads." });
      return;
    }
    setState({ kind: "uploading", name: file.name });
    try {
      const res = await uploadCsv(file);
      router.push(`/audit/${res.account_id}`);
    } catch (err) {
      setState({
        kind: "error",
        message:
          err instanceof Error
            ? err.message
            : "Something went wrong reading that file.",
      });
    }
  }

  const busy = state.kind === "uploading";

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-disabled={busy}
        onClick={() => !busy && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!busy && (e.key === "Enter" || e.key === " ")) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file && !busy) handleFile(file);
        }}
        className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-colors ${
          dragging
            ? "border-brand bg-brand/5"
            : "border-border bg-surface hover:border-brand/50"
        } ${busy ? "cursor-wait opacity-70" : "cursor-pointer"}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.tsv,.txt,text/csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        {busy ? (
          <p className="text-[15px] font-medium">Reading “{state.name}”…</p>
        ) : (
          <>
            <p className="text-[15px] font-medium text-foreground">
              Drop your Google Ads report here
            </p>
            <p className="mt-1 text-sm text-muted">or click to choose the file</p>
          </>
        )}
      </div>

      {state.kind === "error" && (
        <p className="mt-3 rounded-lg border border-[color:var(--sev-high)]/30 bg-[var(--sev-high-bg)] px-3 py-2 text-sm text-[var(--sev-high)]">
          {state.message}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
        <a
          href={SAMPLE_CSV_PATH}
          download
          className="text-brand hover:underline"
        >
          Download a sample report
        </a>
        <span>to see how it works before using your own.</span>
      </div>

      <p className="mt-6 text-sm text-muted">
        No login. No phone number. The report never leaves this audit.
      </p>
    </div>
  );
}
