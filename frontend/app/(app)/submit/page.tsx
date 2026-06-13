"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { PageHeader } from "../../components/ui";
import { TASKS } from "../../lib/mock";
import type { SubmissionType } from "../../lib/types";
import { UploadCloud, Code, Globe, Brain, Cpu } from "lucide-react";

const TYPES: { id: SubmissionType; label: string; hint: string; icon: typeof Code }[] = [
  { id: "code",  label: "Code",          hint: "Paste a single source file", icon: Code },
  { id: "files", label: "Files / repo",  hint: "Upload an archive",          icon: UploadCloud },
  { id: "api",   label: "API endpoint",  hint: "We probe a URL you provide", icon: Globe },
  { id: "model", label: "Model",         hint: "Bring your own API key",     icon: Brain },
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
  const [tasks, setTasks] = useState(TASKS);
  const [taskId, setTaskId] = useState(TASKS[0]?.id ?? "");
  const [code, setCode] = useState(SAMPLE);
  const [endpoint, setEndpoint] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/tasks")
      .then((res) => res.json())
      .then((data) => {
        if (data?.tasks?.length) {
          setTasks(data.tasks);
          setTaskId(data.tasks[0].id);
        }
      })
      .catch((err) => console.error("Failed to load tasks:", err));
  }, []);

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

      <form onSubmit={onSubmit} className="space-y-8 max-w-5xl">
        {/* Type picker */}
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Submission type
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {TYPES.map((t) => {
              const Icon = t.icon;
              const active = type === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setType(t.id)}
                  className={`rounded-xl border p-4 text-left transition-all duration-150 group ${
                    active
                      ? "border-blue-500/50 bg-blue-500/10 ring-1 ring-blue-500/20"
                      : "border-zinc-800 bg-zinc-900 hover:border-zinc-700 hover:bg-zinc-800/60"
                  }`}
                >
                  <Icon
                    className={`h-5 w-5 mb-2 ${active ? "text-blue-400" : "text-zinc-500"}`}
                  />
                  <div className={`font-semibold text-sm ${active ? "text-zinc-50" : "text-zinc-300"}`}>
                    {t.label}
                  </div>
                  <div className="mt-0.5 text-xs text-zinc-600">{t.hint}</div>
                </button>
              );
            })}
          </div>
        </section>

        {/* Task picker */}
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Benchmark task
          </h2>
          <select
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            className="w-full max-w-md rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          >
            {tasks.map((task) => (
              <option key={task.id} value={task.id}>
                {task.title} · {task.language} · {task.difficulty}
              </option>
            ))}
          </select>
        </section>

        {/* Payload */}
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Payload
          </h2>
          {type === "code" && (
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              spellCheck={false}
              rows={16}
              className="w-full rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 leading-relaxed"
            />
          )}

          {type === "files" && (
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-zinc-700 bg-zinc-900/50 p-14 text-center text-sm text-zinc-500 transition-colors hover:border-zinc-600 hover:bg-zinc-900">
              <UploadCloud className="h-10 w-10 text-zinc-600 mb-3" />
              <span>
                Drop a <code className="text-zinc-300">.zip</code> /{" "}
                <code className="text-zinc-300">.tar.gz</code> or click to browse
              </span>
              <span className="mt-1.5 text-xs text-zinc-700">
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
              className="w-full max-w-md rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
          )}

          {type === "model" && (
            <div className="max-w-md space-y-3">
              <input
                type="url"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="Model base URL (e.g. https://api.anthropic.com)"
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="API key (stored encrypted, used only for this run)"
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
              <p className="text-xs text-zinc-600">
                Keys are never logged and are scoped to a single isolated run.
              </p>
            </div>
          )}
        </section>

        <div className="flex items-center gap-4 border-t border-zinc-800 pt-6">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-grad-accent px-6 py-2.5 text-sm font-semibold text-zinc-950 transition-transform hover:scale-[1.02] shadow-md shadow-orange-500/10 cursor-pointer disabled:opacity-60"
          >
            <Cpu className="h-4 w-4" />
            {submitting ? "Enqueuing…" : "Submit & run"}
          </button>
          <span className="text-xs text-zinc-600">
            Enqueues a job → ephemeral container → monitored run → verdict.
          </span>
          {error && <span className="text-sm text-red-400">{error}</span>}
        </div>
      </form>
    </>
  );
}
