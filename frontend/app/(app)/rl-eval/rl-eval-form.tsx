"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ShieldCheck, FlaskConical } from "lucide-react";
import { TASKS } from "../../lib/mock";
import type { BenchmarkTask } from "../../lib/types";

const SAMPLE_BROKEN = `def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(i)
    return out
`;

export function RlEvalForm() {
  const router = useRouter();
  const [tasks, setTasks] = useState<BenchmarkTask[]>(TASKS);
  const [taskId, setTaskId] = useState(TASKS[0]?.id ?? "");
  const [endpoint, setEndpoint] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [code, setCode] = useState(SAMPLE_BROKEN);
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
    setError(null);

    if (!/^https?:\/\//i.test(endpoint.trim())) {
      setError("Endpoint must be an http(s) URL");
      return;
    }
    if (!apiKey.trim()) {
      setError("API key is required");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch("/api/rl-eval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          taskId,
          modelEndpoint: endpoint.trim(),
          modelApiKey: apiKey,
          payload: code,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Evaluation failed to start");
      router.push(`/runs/${data.runId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed to start");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-8 max-w-3xl">
      {/* Key-safety notice */}
      <div className="flex items-start gap-3 rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
        <ShieldCheck className="h-5 w-5 shrink-0 text-blue-400 mt-0.5" />
        <p className="text-sm text-zinc-300">
          Your API key is used only for this evaluation run and is never stored
          or logged. The key is sent host-side to your endpoint; the sandbox that
          scores the code runs fully offline.
        </p>
      </div>

      {/* Model endpoint + key */}
      <section className="space-y-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
          Your model
        </h2>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-zinc-300">
            Endpoint URL
          </span>
          <input
            type="url"
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            placeholder="https://api.openai.com/v1/chat/completions"
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
          <span className="mt-1 block text-xs text-zinc-600">
            OpenAI-compatible. <code className="text-zinc-400">/v1/chat/completions</code> is appended if missing.
          </span>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-zinc-300">
            API key
          </span>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-…"
            autoComplete="off"
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
        </label>
      </section>

      {/* Task */}
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

      {/* Broken seed code */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">
          Broken / partial solution
        </h2>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          rows={14}
          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 leading-relaxed"
        />
        <span className="mt-1 block text-xs text-zinc-600">
          Your model receives this and proposes a patch. Reward = score after −
          score before.
        </span>
      </section>

      <div className="flex items-center gap-4 border-t border-zinc-800 pt-6">
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded-lg bg-grad-accent px-6 py-2.5 text-sm font-semibold text-zinc-950 transition-transform hover:scale-[1.02] shadow-md shadow-orange-500/10 cursor-pointer disabled:opacity-60"
        >
          <FlaskConical className="h-4 w-4" />
          {submitting ? "Starting…" : "Run evaluation"}
        </button>
        {error && <span className="text-sm text-red-400">{error}</span>}
      </div>
    </form>
  );
}