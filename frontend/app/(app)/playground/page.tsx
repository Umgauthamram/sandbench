import Link from "next/link";
import { redirect } from "next/navigation";
import { listRepairRuns } from "../../lib/store";
import { PageHeader } from "../../components/ui";
import { RolloutReplay } from "../../components/rollout-replay";
import { getCurrentUser } from "../../lib/auth";

export const dynamic = "force-dynamic";

const ACTION_SPACE = [
  "run_tests",
  "read_file",
  "edit_file(patch)",
  "restructure",
  "submit",
];

export default async function PlaygroundPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  const rollouts = await listRepairRuns(user.id);

  return (
    <>
      <PageHeader
        title="RL playground"
        subtitle="The sandbox exposed as a Gymnasium env: reset() → step(action) → (obs, reward). A house agent repairs the task; reward is logged per step."
      />

      {rollouts.length === 0 ? (
        <div className="grid gap-6 lg:grid-cols-3">
          {/*specs*/}
          <div className="space-y-4">
            <div className="rounded-xl border border-border bg-panel p-5">
              <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
                Action space
              </h2>
              <ul className="mt-3 space-y-1.5">
                {ACTION_SPACE.map((a) => (
                  <li
                    key={a}
                    className="rounded-md bg-background px-3 py-1.5 font-mono text-xs text-zinc-300"
                  >
                    {a}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-border bg-panel p-5">
              <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
                Reward
              </h2>
              <ul className="mt-3 space-y-1.5 text-sm text-zinc-400">
                <li>
                  <span className="text-clean">+</span> tests passing / score gain
                </li>
                <li>
                  <span className="text-malicious">−</span> security flags
                </li>
                <li>
                  <span className="text-broken">−</span> small step cost
                </li>
              </ul>
              <div className="mt-4 border-t border-border pt-4">
                <p className="text-xs uppercase tracking-wide text-zinc-500">
                  Cumulative reward
                </p>
                <p className="mt-1 text-2xl font-semibold text-zinc-50">
                  0.00
                </p>
              </div>
            </div>
          </div>

          {/*empty state*/}
          <div className="lg:col-span-2">
            <div className="rounded-xl border border-border bg-panel p-8 text-center h-full flex flex-col items-center justify-center min-h-[300px]">
              <p className="text-zinc-400">
                No repair rollouts yet. Submit a partial or broken solution to a benchmark task to generate one.
              </p>
              <Link
                href="/submit"
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-grad-accent px-4 py-2 text-sm font-semibold text-zinc-950 transition-transform hover:scale-[1.02] shadow-sm shadow-orange-500/10"
              >
                Submit a run
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <RolloutReplay rollouts={rollouts} />
      )}
    </>
  );
}
