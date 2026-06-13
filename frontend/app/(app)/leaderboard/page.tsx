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
      <div className="overflow-hidden rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900/80 text-left text-xs uppercase tracking-widest text-zinc-500 border-b border-zinc-800">
            <tr>
              <th className="px-4 py-3.5 font-medium">#</th>
              <th className="px-4 py-3.5 font-medium">User</th>
              <th className="px-4 py-3.5 font-medium">Task</th>
              <th className="hidden px-4 py-3.5 font-medium sm:table-cell">
                Verdict
              </th>
              <th className="px-4 py-3.5 text-right font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {entries.map((e, i) => (
              <tr
                key={e.submissionId}
                className={`transition-colors hover:bg-zinc-800/40 ${
                  i === 0
                    ? "bg-orange-500/5"
                    : i === 1
                    ? "bg-zinc-400/5"
                    : i === 2
                    ? "bg-amber-800/5"
                    : "bg-zinc-900/30"
                }`}
              >
                <td className="px-4 py-3.5 font-mono text-zinc-500 tabular-nums">
                  {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : e.rank}
                </td>
                <td className="px-4 py-3.5 font-semibold text-zinc-200">{e.user}</td>
                <td className="px-4 py-3.5 text-zinc-400">{e.taskTitle}</td>
                <td className="hidden px-4 py-3.5 sm:table-cell">
                  <VerdictBadge verdict={e.verdict} />
                </td>
                <td className="px-4 py-3.5 text-right font-bold text-zinc-100 tabular-nums">
                  {typeof e.score === "number"
                    ? `${Math.round(e.score * 100)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {entries.length === 0 && (
          <div className="p-12 text-center text-sm text-zinc-600">
            No scored runs yet. Submit a solution to appear here.
          </div>
        )}
      </div>
    </>
  );
}
