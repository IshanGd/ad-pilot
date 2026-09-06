import Link from "next/link";
import { ApiError, optimizeBudget, runSimulation } from "@/lib/api";
import { PlanView } from "@/components/PlanView";
import type { BudgetOptimizeResponse, SimulationResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function PlanPage({
  params,
}: PageProps<"/plan/[accountId]">) {
  const { accountId } = await params;

  let simulation: SimulationResponse;
  let budget: BudgetOptimizeResponse;
  try {
    simulation = await runSimulation(accountId);
    const seed = Math.max(1000, Math.round(simulation.current_spend || 10000));
    budget = await optimizeBudget(accountId, seed);
  } catch (err) {
    const notFound = err instanceof ApiError && err.status === 404;
    return (
      <div className="mx-auto max-w-2xl px-5 py-16">
        <h1 className="text-2xl font-bold">
          {notFound ? "That audit has expired" : "We couldn't build the plan"}
        </h1>
        <p className="mt-2 text-[15px] text-muted">
          {notFound
            ? "Upload your report again to get a fresh audit and plan."
            : err instanceof Error
              ? err.message
              : "Please try again."}
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

  return (
    <PlanView
      accountId={accountId}
      simulation={simulation}
      initialBudget={budget}
    />
  );
}
