import type { Metadata } from "next";
import { VerdictBadge } from "../../components/badges";
import { PageHeader } from "../../components/ui";
import { listLeaderboard } from "../../lib/store";

export const metadata: Metadata = { title: "Leaderboard — SandBench" };
export const dynamic = "force-dynamic";

export default async function LeaderboardPage() {
  const entries = await listLeaderboard();
  return (
    <>
      <PageHeader
        title="Leaderboard"
        subtitle="Top submissions per task. Quarantined runs score 0."
      />
      <div className="overflow-hidden rounded-xl border border-border">
        <table className="w-full text-sm">
          <thead className="bg-panel text-left text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-4 py-3 font-medium">#</th>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="hidden px-4 py-3 font-medium sm:table-cell">
                Verdict
              </th>
              <th className="px-4 py-3 text-right font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {entries.map((e) => (
              <tr key={e.submissionId} className="bg-background">
                <td className="px-4 py-3 font-mono text-zinc-500">{e.rank}</td>
                <td className="px-4 py-3 font-medium text-zinc-200">{e.user}</td>
                <td className="px-4 py-3 text-zinc-300">{e.taskTitle}</td>
                <td className="hidden px-4 py-3 sm:table-cell">
                  <VerdictBadge verdict={e.verdict} />
                </td>
                <td className="px-4 py-3 text-right font-semibold text-zinc-100">
                  {e.score}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
