import Link from "next/link";
import type { Run } from "../lib/types";
import { StatusPill, VerdictBadge } from "./badges";

export function RunList({ runs }: { runs: Run[] }) {
  if (runs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-800 p-12 text-center text-sm text-zinc-600">
        No runs yet.{" "}
        <Link href="/submit" className="text-blue-400 hover:underline">
          Submit something
        </Link>{" "}
        to get started.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900/80 text-left text-xs uppercase tracking-widest text-zinc-500 border-b border-zinc-800">
          <tr>
            <th className="px-4 py-3.5 font-medium">Run</th>
            <th className="px-4 py-3.5 font-medium">Task</th>
            <th className="hidden px-4 py-3.5 font-medium sm:table-cell">Type</th>
            <th className="px-4 py-3.5 font-medium">Status</th>
            <th className="px-4 py-3.5 font-medium">Verdict</th>
            <th className="px-4 py-3.5 text-right font-medium">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/60">
          {runs.map((run) => (
            <tr
              key={run.id}
              className="bg-zinc-900/30 transition-colors hover:bg-zinc-800/40"
            >
              <td className="px-4 py-3.5">
                <Link
                  href={`/runs/${run.id}`}
                  className="font-mono text-blue-400 hover:text-blue-300 hover:underline transition-colors"
                >
                  {run.id}
                </Link>
              </td>
              <td className="px-4 py-3.5 text-zinc-300">{run.taskTitle}</td>
              <td className="hidden px-4 py-3.5 text-zinc-500 sm:table-cell">
                {run.type}
              </td>
              <td className="px-4 py-3.5">
                <StatusPill status={run.status} />
              </td>
              <td className="px-4 py-3.5">
                <VerdictBadge verdict={run.verdict} />
              </td>
              <td className="px-4 py-3.5 text-right font-semibold text-zinc-100 tabular-nums">
                {typeof run.score === "number"
                  ? `${Math.round(run.score * 100)}%`
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
