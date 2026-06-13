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
      <div className="flex flex-col lg:flex-row gap-8 items-start w-full">
        {/* Left: Leaderboard Table */}
        <div className="flex-1 w-full overflow-hidden rounded-xl border border-zinc-800">
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

        {/* Right: Info Sidebar */}
        <div className="w-full lg:w-80 shrink-0 bg-white rounded-2xl p-6 border border-zinc-200 text-black space-y-4">
          <div className="flex justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/important.png"
              alt="Leaderboard criteria"
              className="h-32 w-auto object-contain"
            />
          </div>
          <div className="space-y-3">
            <h3 className="text-base font-bold text-zinc-900">Leaderboard Criteria</h3>
            <p className="text-xs text-zinc-700 leading-relaxed font-normal">
              <strong>Ranking Metric:</strong> The leaderboard ranks users based on their 
              <strong> peak (highest) score</strong> achieved for each benchmark task.
            </p>
            <p className="text-xs text-zinc-700 leading-relaxed font-normal">
              <strong>Score Calculation:</strong> Every clean submission runs against a suite of 
              hidden tests in our isolated sandbox. Your score is the percentage of passing test cases. 
              Only your best-performing run per task is registered on the leaderboard.
            </p>
            <p className="text-xs text-zinc-700 leading-relaxed font-normal">
              <strong>Quarantined Runs:</strong> Submissions flagged as malicious by static or dynamic scans 
              are quarantined and score 0%.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
