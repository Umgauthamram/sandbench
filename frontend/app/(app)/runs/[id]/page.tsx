import Link from "next/link";
import { notFound } from "next/navigation";
import { SeverityTag, StatusPill, VerdictBadge } from "../../../components/badges";
import { Card } from "../../../components/ui";
import { getRun } from "../../../lib/store";
import type { Verdict } from "../../../lib/types";
import { RunPoller } from "../../../components/run-poller";

export const dynamic = "force-dynamic";

const VERDICT_COPY: Record<Verdict, { title: string; tone: string; body: string }> = {
  clean: {
    title: "Clean",
    tone: "text-clean",
    body: "No high-severity flags fired. Tests and analysis below.",
  },
  malicious: {
    title: "Malicious — quarantined",
    tone: "text-malicious",
    body: "A high-severity flag fired. The container was force-destroyed and the run quarantined with score 0.",
  },
  broken: {
    title: "Broken",
    tone: "text-broken",
    body: "Clean but failing. Routed to the analysis engine for concrete fixes.",
  },
};

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const run = await getRun(id);
  if (!run) notFound();

  const copy = run.verdict ? VERDICT_COPY[run.verdict] : null;

  return (
    <>
      <RunPoller id={run.id} initialStatus={run.status} />
      <div className="mb-6">
        <Link href="/runs" className="text-sm text-zinc-500 hover:text-zinc-300">
          ← All runs
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="font-mono text-2xl font-semibold text-zinc-50">
            {run.id}
          </h1>
          <StatusPill status={run.status} />
          <VerdictBadge verdict={run.verdict} />
        </div>
        <p className="mt-1 text-sm text-zinc-400">
          {run.taskTitle} · {run.type} · {run.language}
          {run.score !== undefined && (
            <>
              {" · "}
              <span className="text-zinc-200">score {run.score}</span>
            </>
          )}
        </p>
      </div>

      {/* Verdict banner */}
      {copy && (
        <div
          className={`mb-6 rounded-xl border border-border bg-panel p-5 ${run.verdict === "malicious" ? "ring-1 ring-malicious/40" : ""}`}
        >
          <h2 className={`text-lg font-semibold ${copy.tone}`}>{copy.title}</h2>
          <p className="mt-1 text-sm text-zinc-400">{copy.body}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Live logs */}
        <Card className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
              Run logs
            </h2>
            {run.status === "running" && (
              <span className="flex items-center gap-1.5 text-xs text-accent">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                streaming
              </span>
            )}
          </div>
          {/* TODO: replace static logs with an SSE subscription to
                    GET /runs/{id} (text/event-stream) when running. */}
          <pre className="max-h-80 overflow-auto rounded-lg bg-background p-4 font-mono text-xs leading-6 text-zinc-300">
            {run.logs.join("\n")}
            {run.status === "running" && (
              <span className="text-accent">{"\n▍"}</span>
            )}
          </pre>
        </Card>

        {/* Security flags */}
        {run.flags.length > 0 && (
          <Card className="lg:col-span-2">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-malicious">
              Security flags
            </h2>
            <ul className="space-y-3">
              {run.flags.map((flag) => (
                <li
                  key={flag.id}
                  className="rounded-lg border border-malicious/30 bg-malicious/5 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityTag severity={flag.severity} />
                    <code className="font-mono text-sm text-zinc-200">
                      {flag.rule}
                    </code>
                    <span className="text-xs text-zinc-500">({flag.source})</span>
                  </div>
                  <p className="mt-1.5 text-sm text-zinc-400">{flag.detail}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* Suggestions + patches */}
        {run.suggestions.length > 0 && (
          <Card className="lg:col-span-2">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">
              Analysis & suggestions
            </h2>
            <ul className="space-y-4">
              {run.suggestions.map((s) => (
                <li key={s.id}>
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-400">
                      {s.category}
                    </span>
                    <p className="text-sm text-zinc-300">{s.message}</p>
                  </div>
                  {s.patchDiff && (
                    <pre className="mt-2 overflow-auto rounded-lg bg-background p-4 font-mono text-xs leading-6">
                      {s.patchDiff.split("\n").map((line, i) => (
                        <div
                          key={i}
                          className={
                            line.startsWith("+")
                              ? "text-clean"
                              : line.startsWith("-")
                                ? "text-malicious"
                                : "text-zinc-500"
                          }
                        >
                          {line || " "}
                        </div>
                      ))}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* Clean + nothing to suggest */}
        {run.verdict === "clean" && run.suggestions.length === 0 && (
          <Card className="lg:col-span-2">
            <p className="text-sm text-zinc-400">
              ✓ Tests pass and linters are clean. Nothing to suggest — looks good.
            </p>
          </Card>
        )}
      </div>
    </>
  );
}
