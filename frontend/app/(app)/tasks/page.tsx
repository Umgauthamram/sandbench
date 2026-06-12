import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "../../components/ui";
import { listTasks } from "../../lib/store";

export const metadata: Metadata = { title: "Benchmark tasks — SandBench" };

const DIFFICULTY: Record<string, string> = {
  easy: "text-clean",
  medium: "text-broken",
  hard: "text-malicious",
};

export default async function TasksPage() {
  const tasks = await listTasks();
  return (
    <>
      <PageHeader
        title="Benchmark tasks"
        subtitle="Each task defines a scorer. Submissions are scored 0–100 against it."
      />
      <div className="grid gap-4 md:grid-cols-2">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="flex flex-col rounded-xl border border-border bg-panel p-5"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-zinc-50">
                {task.title}
              </h2>
              <span
                className={`text-xs font-semibold uppercase tracking-wide ${DIFFICULTY[task.difficulty]}`}
              >
                {task.difficulty}
              </span>
            </div>
            <p className="mt-2 flex-1 text-sm leading-6 text-zinc-400">
              {task.description}
            </p>
            <div className="mt-4 flex items-center justify-between border-t border-border pt-4 text-xs text-zinc-500">
              <span>
                {task.language} · scored on{" "}
                <span className="text-zinc-300">{task.scorer}</span>
              </span>
              <Link
                href="/submit"
                className="font-medium text-accent hover:underline"
              >
                Attempt →
              </Link>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
