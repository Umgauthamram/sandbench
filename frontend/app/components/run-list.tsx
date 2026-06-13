import Link from "next/link";
import type { Run } from "../lib/types";
import { StatusPill, VerdictBadge } from "./badges";

export function RunList({ runs }: { runs: Run[] }) {
  if (runs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-zinc-500">
        No runs yet.{" "}
        <Link href="/submit" className="text-accent hover:underline">
          Submit something
        </Link>{" "}
        to get started.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead className="bg-panel text-left text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-4 py-3 font-medium">Run</th>
            <th className="px-4 py-3 font-medium">Task</th>
            <th className="hidden px-4 py-3 font-medium sm:table-cell">Type</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Verdict</th>
            <th className="px-4 py-3 text-right font-medium">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {runs.map((run) => (
            <tr
              key={run.id}
              className="bg-background transition-colors hover:bg-panel/60"
            >
              <td className="px-4 py-3">
                <Link
                  href={`/runs/${run.id}`}
                  className="font-mono text-accent hover:underline"
                >
                  {run.id}
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-300">{run.taskTitle}</td>
              <td className="hidden px-4 py-3 text-zinc-400 sm:table-cell">
                {run.type}
              </td>
              <td className="px-4 py-3">
                <StatusPill status={run.status} />
              </td>
              <td className="px-4 py-3">
                <VerdictBadge verdict={run.verdict} />
              </td>
              <td className="px-4 py-3 text-right font-medium text-zinc-200">
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
