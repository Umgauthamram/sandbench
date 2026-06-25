import type { Metadata } from "next";
import Link from "next/link";
import { Award, Box, GitCommitHorizontal, History, ShieldCheck } from "lucide-react";
import { VerdictBadge } from "../../components/badges";
import { Card, PageHeader } from "../../components/ui";
import { listLeaderboard, listTasks } from "../../lib/store";

export const metadata: Metadata = { title: "Leaderboard - SandBench" };
export const dynamic = "force-dynamic";

export default async function LeaderboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ suite?: string; version?: string }>;
}) {
  const params = (await searchParams) ?? {};
  const tasks = await listTasks();
  const suites = Array.from(new Set(tasks.map((task) => task.suite ?? "core"))).sort();
  const selectedSuite = params.suite || suites[0] || "core";
  const selectedVersion =
    params.version ||
    tasks.find((task) => (task.suite ?? "core") === selectedSuite)?.version ||
    "0.1.0";
  const versions = Array.from(
    new Set(
      tasks
        .filter((task) => (task.suite ?? "core") === selectedSuite)
        .map((task) => task.version ?? "0.1.0"),
    ),
  ).sort();

  const entries = await listLeaderboard({ suite: selectedSuite, version: selectedVersion });
  const topScore = entries[0]?.score ?? 0;

  return (
    <>
      <PageHeader
        title="Leaderboard"
        subtitle="Versioned peak scores with immutable submission hashes and artifact provenance."
      />

      <div className="mb-6 flex flex-wrap gap-2">
        {suites.map((suite) => (
          <Link
            key={suite}
            href={`/leaderboard?suite=${suite}&version=${
              tasks.find((task) => (task.suite ?? "core") === suite)?.version ?? "0.1.0"
            }`}
            className={`rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
              suite === selectedSuite
                ? "border-blue-500/40 bg-blue-500/10 text-blue-300"
                : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {suite}
          </Link>
        ))}
        {versions.length > 1 && (
          <div className="ml-0 flex flex-wrap gap-2 md:ml-3">
            {versions.map((version) => (
              <Link
                key={version}
                href={`/leaderboard?suite=${selectedSuite}&version=${version}`}
                className={`rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
                  version === selectedVersion
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                v{version}
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/60">
          <div className="grid grid-cols-[64px_1fr_auto] gap-3 border-b border-zinc-800 px-4 py-3 text-xs font-semibold uppercase tracking-widest text-zinc-500 md:grid-cols-[64px_1fr_1fr_110px_110px]">
            <div>Rank</div>
            <div>User</div>
            <div className="hidden md:block">Task</div>
            <div className="hidden md:block">Version</div>
            <div className="text-right">Score</div>
          </div>

          <div className="divide-y divide-zinc-800/70">
            {entries.map((entry) => {
              const scorePct = Math.round(entry.score * 100);
              const barWidth = topScore > 0 ? Math.max(6, Math.round((entry.score / topScore) * 100)) : scorePct;
              return (
                <div key={entry.submissionHash || entry.submissionId} className="px-4 py-4 hover:bg-zinc-800/30">
                  <div className="grid grid-cols-[64px_1fr_auto] items-center gap-3 md:grid-cols-[64px_1fr_1fr_110px_110px]">
                    <div className="font-mono text-sm text-zinc-500">#{entry.rank}</div>
                    <div>
                      <div className="font-semibold text-zinc-100">{entry.user}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                        <VerdictBadge verdict={entry.verdict} />
                        {entry.runId && <span>{entry.runId}</span>}
                      </div>
                    </div>
                    <div className="hidden text-sm text-zinc-300 md:block">{entry.taskTitle}</div>
                    <div className="hidden text-sm text-zinc-500 md:block">
                      {entry.suite ?? selectedSuite} / {entry.taskVersion ?? selectedVersion}
                    </div>
                    <div className="text-right font-mono text-lg font-bold text-zinc-50">{scorePct}%</div>
                  </div>
                  <div className="mt-3 h-1.5 rounded-full bg-zinc-800">
                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${barWidth}%` }} />
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-zinc-500 md:grid-cols-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <GitCommitHorizontal className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">
                        submission {entry.submissionHash || entry.submissionId}
                      </span>
                    </div>
                    <div className="flex min-w-0 items-center gap-2 md:justify-end">
                      <Box className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">
                        bundle {entry.artifactBundleHash || "pending"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {entries.length === 0 && (
            <div className="p-12 text-center text-sm text-zinc-600">
              No scored runs for {selectedSuite} v{selectedVersion} yet.
            </div>
          )}
        </div>

        <div className="space-y-5">
          <Card>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
                <Award className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-zinc-100">Ranking model</h2>
                <p className="text-xs text-zinc-500">Peak score per user and task</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-zinc-400">
              Phase 4 stores full attempt history separately from the ranked peak score, scoped by suite and task version.
            </p>
          </Card>

          <Card>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-zinc-100">Integrity</h2>
                <p className="text-xs text-zinc-500">Hash-chained submissions</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-zinc-400">
              Each ranked attempt receives an immutable submission hash and links to a sealed artifact bundle.
            </p>
          </Card>

          <Card>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-amber-500/10 p-2 text-amber-400">
                <History className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-zinc-100">Current slice</h2>
                <p className="text-xs text-zinc-500">
                  {selectedSuite} / v{selectedVersion}
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
