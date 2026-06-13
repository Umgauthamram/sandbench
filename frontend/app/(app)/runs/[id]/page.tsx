import Link from "next/link";
import { notFound } from "next/navigation";
import { SeverityTag, StatusPill, VerdictBadge } from "../../../components/badges";
import { Card } from "../../../components/ui";
import { getRun } from "../../../lib/store";
import type { Verdict } from "../../../lib/types";
import { RunStream } from "../../../components/run-poller";
import { MarkdownRenderer } from "../../../components/markdown-renderer";
import { ArrowLeft, CheckCircle2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { getCurrentUser } from "../../../lib/auth";

export const dynamic = "force-dynamic";

const VERDICT_BASE: Record<Verdict, { title: string; tone: string; border: string }> = {
  clean: {
    title: "Clean",
    tone: "text-emerald-400",
    border: "border-emerald-500/20 ring-emerald-500/10",
  },
  suspicious: {
    title: "Suspicious",
    tone: "text-amber-400",
    border: "border-amber-500/20 ring-amber-500/10",
  },
  malicious: {
    title: "Malicious — quarantined",
    tone: "text-red-400",
    border: "border-red-500/30 ring-red-500/20",
  },
  broken: {
    title: "Broken",
    tone: "text-amber-400",
    border: "border-amber-500/20 ring-amber-500/10",
  },
};

function getVerdictCopy(
  verdict: Verdict,
  flags: { severity: string }[],
  score: number | null | undefined
): { title: string; tone: string; border: string; body: string } {
  let base = VERDICT_BASE[verdict];

  let body: string;
  if (verdict === "malicious") {
    body =
      "A high-severity flag fired. The container was force-destroyed and the run quarantined with score 0.";
  } else if (verdict === "suspicious") {
    const flagCount = flags.filter(
      (f) => f.severity === "medium" || f.severity === "high"
    ).length;
    body = `${flagCount} security flag(s) were raised (medium severity). The code ran but contains potentially dangerous patterns. Review the flags below.`;
  } else if (verdict === "broken") {
    body = "The code ran but exited non-zero or timed out. Routed to the analysis engine for concrete fixes.";
  } else {
    // clean
    if (typeof score === "number" && score === 0) {
      body = "No security flags fired. Code executed cleanly but failed all hidden tests — check your logic.";
      base = {
        title: "Clean (Failing Tests)",
        tone: "text-amber-400",
        border: "border-amber-500/20 ring-amber-500/10",
      };
    } else if (typeof score === "number" && score < 1.0) {
      body = "No security flags fired. Code executed cleanly but failed some hidden tests — check your logic.";
      base = {
        title: "Clean (Failing Tests)",
        tone: "text-amber-400",
        border: "border-amber-500/20 ring-amber-500/10",
      };
    } else if (typeof score === "number" && score === 1.0) {
      body = "No security flags fired. Code executed cleanly and passed all tests.";
      base = {
        title: "Clean & Passed",
        tone: "text-emerald-400",
        border: "border-emerald-500/20 ring-emerald-500/10",
      };
    } else {
      body = "No security flags fired. Tests and analysis below.";
      base = {
        title: "Clean (No score)",
        tone: "text-zinc-400",
        border: "border-zinc-500/20 ring-zinc-500/10",
      };
    }
  }

  return { ...base, body };
}

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) {
    notFound();
  }

  const { id } = await params;
  const run = await getRun(id);
  if (!run) notFound();

  // Secure horizontal access check
  if (run.userId && run.userId !== user.id) {
    notFound();
  }

  const copy = run.verdict ? getVerdictCopy(run.verdict, run.flags, run.score) : null;

  return (
    <>
      <div className="mb-6">
        <Link href="/runs" className="inline-flex items-center gap-1.5 text-sm text-zinc-600 hover:text-zinc-300 transition-colors select-none">
          <ArrowLeft className="h-3.5 w-3.5" /> All runs
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="font-mono text-2xl font-bold text-zinc-50">
            {run.id}
          </h1>
          <StatusPill status={run.status} />
          <VerdictBadge verdict={run.verdict} />
        </div>
        <p className="mt-1.5 text-sm text-zinc-500">
          {run.taskTitle} · {run.type} · {run.language}
          {typeof run.score === "number" && (
            <>
              {" · "}
              <span className="text-zinc-200 font-semibold tabular-nums">
                score {Math.round(run.score * 100)}%
              </span>
            </>
          )}
        </p>
      </div>

      {/* Verdict banner */}
      {copy && (
        <div
          className={`mb-6 rounded-xl border bg-zinc-900 p-5 ring-1 ${copy.border}`}
        >
          <h2 className={`text-base font-semibold ${copy.tone}`}>{copy.title}</h2>
          <p className="mt-1 text-sm text-zinc-400">{copy.body}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Live logs */}
        <RunStream id={run.id} initialLogs={run.logs} initialStatus={run.status} />

        {/* Security flags */}
        {run.flags.length > 0 && (
          <Card className="lg:col-span-2">
            <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-red-400">
              Security flags
            </h2>
            <ul className="space-y-3">
              {run.flags.map((flag) => (
                <li
                  key={flag.id}
                  className="rounded-lg border border-red-500/20 bg-red-500/5 p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityTag severity={flag.severity} />
                    <code className="font-mono text-sm text-zinc-200">
                      {flag.rule}
                    </code>
                    <span className="text-xs text-zinc-600">({flag.source})</span>
                  </div>
                  <p className="mt-2 text-sm text-zinc-400">{flag.detail}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* Suggestions + patches */}
        {run.suggestions.length > 0 && (
          <Card className="lg:col-span-2">
            <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-zinc-500">
              Analysis &amp; suggestions
            </h2>
            <ul className="space-y-6">
              {run.suggestions.map((s) => {
                const isSystem = s.category === "system";
                return (
                  <li key={s.id} className={isSystem ? "rounded-lg border border-red-500/20 bg-red-500/5 p-4" : ""}>
                    <div className="mb-3 flex items-center gap-2">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                        isSystem
                          ? "bg-red-500/25 text-red-200"
                          : "bg-zinc-800 text-zinc-400"
                      }`}>
                        {s.category}
                      </span>
                    </div>
                    <MarkdownRenderer content={s.message} />
                    {s.patchDiff && (
                      <pre className="mt-3 overflow-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs leading-6 border border-zinc-800">
                        {s.patchDiff.split("\n").map((line, i) => (
                          <div
                            key={i}
                            className={
                              line.startsWith("+")
                                ? "text-emerald-400"
                                : line.startsWith("-")
                                ? "text-red-400"
                                : "text-zinc-500"
                            }
                          >
                            {line || " "}
                          </div>
                        ))}
                      </pre>
                    )}
                  </li>
                );
              })}
            </ul>
          </Card>
        )}

        {/* Repair attempt */}
        {run.repair && run.repair.attempted && (
          <Card className="lg:col-span-2">
            <h2 className="mb-5 text-xs font-semibold uppercase tracking-widest text-zinc-500">
              Repair attempt
            </h2>
            <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
              <div className="rounded-lg bg-zinc-800/50 p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Applied</p>
                <p className={`mt-2 text-sm font-semibold ${run.repair.applied ? "text-emerald-400" : "text-red-400"}`}>
                  {run.repair.applied ? "Yes" : "No"}
                </p>
              </div>
              <div className="rounded-lg bg-zinc-800/50 p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Method</p>
                <p className="mt-2 text-sm font-semibold text-zinc-200">
                  {run.repair.method}
                </p>
              </div>
              <div className="rounded-lg bg-zinc-800/50 p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Score Change</p>
                <p className="mt-2 text-sm font-semibold text-zinc-200 tabular-nums">
                  {Math.round(run.repair.score_before * 100)}% →{" "}
                  {run.repair.score_after !== null
                    ? `${Math.round(run.repair.score_after * 100)}%`
                    : "—"}
                </p>
              </div>
              <div className="rounded-lg bg-zinc-800/50 p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Reward</p>
                <div className="mt-2 flex items-center gap-1.5">
                  {run.repair.reward === null ? (
                    <Minus className="h-4 w-4 text-amber-400" />
                  ) : run.repair.reward > 0 ? (
                    <TrendingUp className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-400" />
                  )}
                  <p
                    className={`text-lg font-mono font-bold tabular-nums ${
                      run.repair.reward === null
                        ? "text-amber-400"
                        : run.repair.reward > 0
                        ? "text-emerald-400"
                        : run.repair.reward === 0
                        ? "text-zinc-400"
                        : "text-red-400"
                    }`}
                  >
                    {run.repair.reward !== null
                      ? run.repair.reward > 0
                        ? `+${run.repair.reward.toFixed(2)}`
                        : run.repair.reward.toFixed(2)
                      : "—"}
                  </p>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Clean + perfect score/no score + nothing to suggest + no security flags */}
        {run.verdict === "clean" && (run.score === null || run.score === undefined || run.score === 1.0) && run.suggestions.length === 0 && run.flags.length === 0 && (
          <Card className="lg:col-span-2">
            <p className="flex items-center gap-2.5 text-sm text-zinc-400">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
              Tests pass and linters are clean. Nothing to suggest — looks good.
            </p>
          </Card>
        )}

        {/* Clean/Suspicious + failed tests + nothing to suggest */}
        {(run.verdict === "clean" || run.verdict === "suspicious") && typeof run.score === "number" && run.score < 1.0 && run.suggestions.length === 0 && (
          <Card className="lg:col-span-2">
            <p className="flex items-center gap-2.5 text-sm text-zinc-400">
              <CheckCircle2 className="h-5 w-5 text-amber-400 shrink-0" />
              Some tests failed, but no suggestions are available. Check test stdout/stderr in the logs.
            </p>
          </Card>
        )}
      </div>
    </>
  );
}
