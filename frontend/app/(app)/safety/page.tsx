import type { Metadata } from "next";
import { AlertTriangle, CheckCircle2, Radar, ShieldCheck } from "lucide-react";
import { PageHeader, Stat } from "../../components/ui";
import { listTasks } from "../../lib/store";

export const metadata: Metadata = { title: "Safety suite - SandBench" };
export const dynamic = "force-dynamic";

const CATEGORY_LABELS: Record<string, string> = {
  safety_exfiltration: "Exfiltration",
  safety_data_leakage: "Data leakage",
  safety_sandbox_escape: "Sandbox escape",
  safety_resource_abuse: "Resource abuse",
  safety_prompt_injection: "Prompt injection",
  safety_interpreter_misuse: "Interpreter misuse",
  safety_evasion: "Evasion",
  safety_supply_chain: "Supply chain",
  safety_insecure_code: "Insecure code",
};

export default async function SafetyPage() {
  const tasks = await listTasks();
  const safetyTasks = tasks.filter((task) => task.suite === "safety");
  const readyCount = safetyTasks.filter((task) => task.benchmark_ready).length;
  const categoryCounts = safetyTasks.reduce<Record<string, number>>((acc, task) => {
    const category = task.capability ?? "unknown";
    acc[category] = (acc[category] ?? 0) + 1;
    return acc;
  }, {});

  const estimatedMinutes = safetyTasks.reduce(
    (sum, task) => sum + (task.human_baseline_minutes ?? 0),
    0,
  );

  return (
    <>
      <PageHeader
        title="Safety suite"
        subtitle="First-class safety benchmark tasks for exfiltration, prompt injection, sandbox abuse, evasion, and insecure code."
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="Safety tasks" value={safetyTasks.length} />
        <Stat label="Benchmark-ready" value={`${readyCount}/${safetyTasks.length}`} />
        <Stat label="Categories" value={Object.keys(categoryCounts).length} />
        <Stat label="Human baseline" value={`${estimatedMinutes}m`} />
      </div>

      <section className="mt-8 grid gap-6 xl:grid-cols-[1fr_1.2fr]">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
              <Radar className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-50">Coverage map</h2>
              <p className="text-sm text-zinc-500">Task count by safety category</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {Object.entries(categoryCounts).map(([category, count]) => {
              const pct = safetyTasks.length ? Math.round((count / safetyTasks.length) * 100) : 0;
              return (
                <div key={category}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="text-zinc-300">
                      {CATEGORY_LABELS[category] ?? category}
                    </span>
                    <span className="text-zinc-500">{count}</span>
                  </div>
                  <div className="h-2 rounded-full bg-zinc-800">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900">
          <div className="border-b border-zinc-800 p-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-zinc-50">Task-level scorecard</h2>
                <p className="text-sm text-zinc-500">Readiness and evidence coverage for Phase 3</p>
              </div>
            </div>
          </div>

          <div className="divide-y divide-zinc-800">
            {safetyTasks.map((task) => (
              <div key={task.id} className="grid gap-4 p-5 md:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-zinc-100">{task.title}</h3>
                    <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs font-medium text-zinc-400">
                      {CATEGORY_LABELS[task.capability ?? ""] ?? task.capability}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-500">
                    {task.description}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(task.tags ?? []).slice(0, 5).map((tag) => (
                      <span
                        key={tag}
                        className="rounded-md border border-zinc-800 px-2 py-1 text-xs text-zinc-500"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-start md:justify-end">
                  {task.benchmark_ready ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Ready
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Draft
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
