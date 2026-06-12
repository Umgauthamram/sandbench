"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { PageHeader } from "../../components/ui";
import { TASKS } from "../../lib/mock";
import type { SubmissionType } from "../../lib/types";

const TYPES: { id: SubmissionType; label: string; hint: string }[] = [
  { id: "code", label: "Code", hint: "Paste a single source file" },
  { id: "files", label: "Files / repo", hint: "Upload an archive" },
  { id: "api", label: "API endpoint", hint: "We probe a URL you provide" },
  { id: "model", label: "Model", hint: "Bring your own API key" },
];

const SAMPLE = `def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out
`;

export default function SubmitPage() {
  const router = useRouter();
  const [type, setType] = useState<SubmissionType>("code");
  const [taskId, setTaskId] = useState(TASKS[0].id);
  const [code, setCode] = useState(SAMPLE);
  const [endpoint, setEndpoint] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const payload =
      type === "code" ? code : type === "files" ? "" : endpoint;

    try {
      const res = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, taskId, payload }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Submission failed");
      router.push(`/runs/${data.runId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="New submission"
        subtitle="Pick what you're submitting and a benchmark task. Every run executes in a fresh, hardened, throwaway container."
      />

      <form onSubmit={onSubmit} className="space-y-8">
        {/* Type picker */}
        <section>
          <h2 className="mb-3 text-sm font-medium text-zinc-300">
            Submission type
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {TYPES.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setType(t.id)}
                className={`rounded-xl border p-4 text-left transition-colors ${
                  type === t.id
                    ? "border-accent bg-accent/10"
                    : "border-border bg-panel hover:border-zinc-600"
                }`}
              >
                <div className="font-medium text-zinc-100">{t.label}</div>
                <div className="mt-1 text-xs text-zinc-500">{t.hint}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Task picker */}
        <section>
          <h2 className="mb-3 text-sm font-medium text-zinc-300">
            Benchmark task
          </h2>
          <select
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            className="w-full max-w-md rounded-lg border border-border bg-background px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          >
            {TASKS.map((task) => (
              <option key={task.id} value={task.id}>
                {task.title} · {task.language} · {task.difficulty}
              </option>
            ))}
          </select>
        </section>

        {/* Payload */}
        <section>
          <h2 className="mb-3 text-sm font-medium text-zinc-300">Payload</h2>
          {type === "code" && (
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              spellCheck={false}
              rows={16}
              className="w-full rounded-xl border border-border bg-background p-4 font-mono text-sm text-zinc-100 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          )}

          {type === "files" && (
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-border bg-panel p-12 text-center text-sm text-zinc-400 transition-colors hover:border-zinc-600">
              <span className="text-2xl text-zinc-600">↥</span>
              <span className="mt-2">
                Drop a <code className="text-zinc-300">.zip</code> /{" "}
                <code className="text-zinc-300">.tar.gz</code> or click to browse
              </span>
              <span className="mt-1 text-xs text-zinc-600">
                Size-limited and validated server-side.
              </span>
              <input type="file" className="hidden" accept=".zip,.tar,.gz,.tgz" />
            </label>
          )}

          {type === "api" && (
            <input
              type="url"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="https://api.example.com/echo"
              className="w-full max-w-md rounded-lg border border-border bg-background px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          )}

          {type === "model" && (
            <div className="max-w-md space-y-3">
              <input
                type="url"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="Model base URL (e.g. https://api.anthropic.com)"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="API key (stored encrypted, used only for this run)"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
              <p className="text-xs text-zinc-600">
                Keys are never logged and are scoped to a single isolated run.
              </p>
            </div>
          )}
        </section>

        <div className="flex items-center gap-3 border-t border-border pt-6">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-zinc-50 px-5 py-2.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200 disabled:opacity-60"
          >
            {submitting ? "Enqueuing…" : "Submit & run"}
          </button>
          <span className="text-xs text-zinc-500">
            Enqueues a job → ephemeral container → monitored run → verdict.
          </span>
          {error && <span className="text-sm text-malicious">{error}</span>}
        </div>
      </form>
    </>
  );
}
