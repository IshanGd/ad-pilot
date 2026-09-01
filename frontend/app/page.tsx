import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-20">
      <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
        Stop wasting money on Google Ads.
      </h1>
      <p className="mt-4 max-w-xl text-lg text-muted">
        Upload your ads report and see exactly where your money is going — free,
        no signup.
      </p>

      <Link
        href="/upload"
        className="mt-8 inline-block rounded-lg bg-brand px-6 py-3 text-base font-medium text-white hover:opacity-90"
      >
        Check my campaign
      </Link>

      <div className="mt-16 grid gap-6 sm:grid-cols-3">
        {[
          {
            t: "Nothing to set up",
            d: "Export one report from Google Ads. That's the whole setup.",
          },
          {
            t: "Plain answers",
            d: "One number for what you're wasting, and a short list of what to do.",
          },
          {
            t: "We watch it for you",
            d: "Opt in afterwards and we text you on WhatsApp only when it matters.",
          },
        ].map((c) => (
          <div key={c.t} className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-base font-semibold">{c.t}</h2>
            <p className="mt-1.5 text-sm text-muted">{c.d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
