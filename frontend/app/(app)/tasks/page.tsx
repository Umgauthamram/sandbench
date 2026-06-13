import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "../../components/ui";
import { listTasks } from "../../lib/store";
import { ArrowRight, Code2, FlaskConical, Swords } from "lucide-react";

export const metadata: Metadata = { title: "Benchmark tasks — SandBench" };
export const dynamic = "force-dynamic";

const DIFFICULTY_STYLES: Record<string, { text: string; bg: string; icon: typeof Code2 }> = {
  easy:   { text: "text-emerald-400", bg: "bg-emerald-400/10",   icon: Code2 },
  medium: { text: "text-amber-400",   bg: "bg-amber-400/10",     icon: FlaskConical },
  hard:   { text: "text-red-400",     bg: "bg-red-400/10",       icon: Swords },
};

export default async function TasksPage() {
  const tasks = await listTasks();
  return (
    <>
      <PageHeader
        title="Benchmark tasks"
        subtitle="Each task defines a scorer. Submissions are scored 0–100 against it."
      />
      <div className="grid gap-5 md:grid-cols-2">
        {tasks.map((task) => {
          const diff = DIFFICULTY_STYLES[task.difficulty] ?? DIFFICULTY_STYLES.easy;
          const DiffIcon = diff.icon;
          return (
            <div
              key={task.id}
              className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900 p-6 hover:border-zinc-700 transition-all duration-150 group"
            >
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-lg font-semibold text-zinc-50 leading-snug">
                  {task.title}
                </h2>
                <span
                  className={`inline-flex items-center gap-1.5 shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${diff.text} ${diff.bg}`}
                >
                  <DiffIcon className="h-3 w-3" />
                  {task.difficulty}
                </span>
              </div>
              <p className="mt-3 flex-1 text-sm leading-relaxed text-zinc-400">
                {task.description}
              </p>
              <div className="mt-5 flex items-center justify-between border-t border-zinc-800 pt-4 text-xs text-zinc-500">
                <span>
                  {task.language} · scored on{" "}
                  <span className="text-zinc-300 font-medium">{task.scorer}</span>
                </span>
                <Link
                  href="/submit"
                  className="inline-flex items-center gap-1 font-semibold text-blue-400 hover:text-blue-300 transition-colors group-hover:gap-2"
                >
                  Attempt <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
