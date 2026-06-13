import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { RunList } from "../../components/run-list";
import { PageHeader, Stat } from "../../components/ui";
import { listRuns } from "../../lib/store";
import { getCurrentUser } from "../../lib/auth";

export const metadata: Metadata = { title: "Dashboard — SandBench" };
export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  const runs = await listRuns(user.id);
  const total = runs.length;
  const quarantined = runs.filter((r) => r.verdict === "malicious").length;
  const clean = runs.filter((r) => r.verdict === "clean").length;
  const scored = runs.filter((r) => typeof r.score === "number");
  const avg =
    scored.length > 0
      ? Math.round(
          (scored.reduce((s, r) => s + (r.score ?? 0), 0) / scored.length) * 100,
        )
      : 0;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Your submissions, runs, and verdicts at a glance."
        action={
          <Link
            href="/submit"
            className="inline-flex items-center gap-2 rounded-lg bg-grad-accent px-4 py-2 text-sm font-semibold text-zinc-950 transition-transform hover:scale-[1.02] shadow-sm shadow-orange-500/10"
          >
            New submission
          </Link>
        }
      />

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total runs" value={total} />
        <Stat label="Clean" value={clean} />
        <Stat label="Quarantined" value={quarantined} />
        <Stat label="Avg score" value={`${avg}%`} />
      </div>

      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">
        Recent runs
      </h2>
      <RunList runs={runs} />
    </>
  );
}
