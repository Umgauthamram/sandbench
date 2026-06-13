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

const PRESETS: Record<
  string,
  { label: string; baseUrl: string; defaultModel: string; placeholder: string }
> = {
  openai: {
    label: "OpenAI",
    baseUrl: "https://api.openai.com/v1",
    defaultModel: "gpt-4o-mini",
    placeholder: "gpt-4o-mini",
  },
  gemini: {
    label: "Gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    defaultModel: "gemini-2.5-flash",
    placeholder: "gemini-2.5-flash",
  },
  groq: {
    label: "Groq",
    baseUrl: "https://api.groq.com/openai/v1",
    defaultModel: "llama-3.3-70b-versatile",
    placeholder: "llama-3.3-70b-versatile",
  },
  huggingface: {
    label: "Hugging Face",
    baseUrl: "https://router.huggingface.co/v1",
    defaultModel: "meta-llama/Llama-3.3-70B-Instruct",
    placeholder: "e.g., meta-llama/Llama-3.3-70B-Instruct",
  },
  custom: {
    label: "Custom (OpenAI-compatible)",
    baseUrl: "",
    defaultModel: "",
    placeholder: "e.g., custom-model-id",
  },
};

export function RlEvalForm() {
  const router = useRouter();
  const [tasks, setTasks] = useState<BenchmarkTask[]>(TASKS);
  const [taskId, setTaskId] = useState(TASKS[0]?.id ?? "");
  
  const [provider, setProvider] = useState("openai");
  const [endpoint, setEndpoint] = useState(PRESETS.openai.baseUrl);
  const [modelName, setModelName] = useState(PRESETS.openai.defaultModel);
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

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    const preset = PRESETS[newProvider];
    if (preset) {
      setEndpoint(preset.baseUrl);
      setModelName(preset.defaultModel);
    }
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (provider === "custom" && !endpoint.trim()) {
      setError("Endpoint URL is required for custom provider");
      return;
    }
    if (endpoint.trim() && !/^https?:\/\//i.test(endpoint.trim())) {
      setError("Endpoint must be an http(s) URL");
      return;
    }
    if (!modelName.trim()) {
      setError("Model name is required");
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
          provider,
          modelName: modelName.trim(),
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
    <div className="flex flex-col lg:flex-row gap-8 items-start w-full">
      {/* Left: The Form */}
      <form onSubmit={onSubmit} className="space-y-8 flex-1 w-full max-w-3xl">
        {/* Model endpoint + key */}
        <section className="space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Your model
          </h2>
          
          {/* Row 1: Provider preset & Endpoint URL side-by-side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-zinc-300">
                Provider preset
              </span>
              <select
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              >
                {Object.entries(PRESETS).map(([id, p]) => (
                  <option key={id} value={id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-zinc-300">
                Endpoint URL {provider === "custom" && <span className="text-red-400">*</span>}
              </span>
              <input
                type="url"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder={provider === "custom" ? "https://my-custom-endpoint.com/v1" : "Leave blank for provider default"}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
              <span className="mt-1 block text-xs text-zinc-600 font-normal">
                All providers must expose an OpenAI-compatible <code className="text-zinc-400">/chat/completions</code> endpoint.
              </span>
            </label>
          </div>

          {/* Row 2: Model name & Benchmark task side-by-side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-zinc-300">
                Model name <span className="text-red-400">*</span>
              </span>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder={PRESETS[provider]?.placeholder ?? "e.g., gpt-4o-mini"}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
            </label>

            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-zinc-300">
                Benchmark task
              </span>
              <select
                value={taskId}
                onChange={(e) => setTaskId(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              >
                {tasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    {task.title} · {task.language} · {task.difficulty}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* Row 3: API key */}
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-zinc-300">
              API key <span className="text-red-400">*</span>
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
          <span className="mt-1 block text-xs text-zinc-600 font-normal">
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

      {/* Right: Security Sidebar Card */}
      <div className="w-full lg:w-72 shrink-0 bg-white rounded-2xl p-6 border border-zinc-200 text-black space-y-4 lg:mt-8 shadow-sm">
        <div className="flex justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/man.png"
            alt="Safety representation"
            className="h-32 w-auto object-contain"
          />
        </div>
        <div className="space-y-2">
          <h3 className="text-sm font-bold text-zinc-950 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-blue-600 shrink-0" />
            <span className="text-blue-600">
              API Key Safety
            </span>
          </h3>
          <p className="text-xs text-zinc-700 leading-relaxed font-normal">
            Your API key is used only for this evaluation run and is never stored
            or logged. The key is sent host-side to your endpoint; the sandbox that
            scores the code runs fully offline.
          </p>
        </div>
      </div>
    </div>
  );
}