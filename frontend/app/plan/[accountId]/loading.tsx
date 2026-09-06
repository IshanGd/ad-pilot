export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-16">
      <div className="h-4 w-32 animate-pulse rounded bg-border" />
      <div className="mt-4 h-10 w-3/4 animate-pulse rounded bg-border" />
      <div className="mt-6 h-28 animate-pulse rounded-xl bg-border" />
      <div className="mt-8 space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-border" />
        ))}
      </div>
      <p className="mt-6 text-sm text-muted">Building your plan…</p>
    </div>
  );
}
