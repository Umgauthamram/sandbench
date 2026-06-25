import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Code2,
  Filter,
  FlaskConical,
  ShieldCheck,
  Swords,
} from "lucide-react";
import { PageHeader } from "../../components/ui";
import { listTasks } from "../../lib/store";
import type { BenchmarkTask } from "../../lib/types";

export const metadata: Metadata = { title: "Benchmark tasks - SandBench" };
export const dynamic = "force-dynamic";

type TaskFilters = {
  suite?: string;
  capability?: string;
  difficulty?: string;
  ready?: string;
};

const DIFFICULTY_STYLES: Record<string, { text: string; bg: string; icon: typeof Code2 }> = {
  easy: { text: "text-emerald-400", bg: "bg-emerald-400/10", icon: Code2 },
  medium: { text: "text-amber-400", bg: "bg-amber-400/10", icon: FlaskConical },
  hard: { text: "text-red-400", bg: "bg-red-400/10", icon: Swords },
};

export default async function TasksPage({
  searchParams,
}: {
  searchParams?: Promise<TaskFilters>;
}) {
  const params = (await searchParams) ?? {};
  const tasks = await listTasks();

  const suites = unique(tasks.map((task) => task.suite ?? "core"));
  const capabilities = unique(tasks.map((task) => task.capability).filter(Boolean));
  const difficulties = unique(tasks.map((task) => task.difficulty));
  const filteredTasks = tasks.filter((task) => {
    if (params.suite && (task.suite ?? "core") !== params.suite) return false;
    if (params.capability && task.capability !== params.capability) return false;
    if (params.difficulty && task.difficulty !== params.difficulty) return false;
    if (params.ready === "yes" && !task.benchmark_ready) return false;
    if (params.ready === "reviewed" && (!task.safety_reviewed || !task.deterministic_scoring)) return false;
    return true;
  });

  return (
    <>
      <PageHeader
        title="Benchmark tasks"
        subtitle="Filter by suite, capability, difficulty, and benchmark readiness before submitting a run."
      />

      <section className="mb-6 rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Filter className="h-4 w-4 text-blue-400" />
          Filters
          <span className="ml-auto text-xs font-medium text-zinc-500">
            {filteredTasks.length}/{tasks.length} tasks
          </span>
        </div>
        <FilterGroup label="Suite">
          <FilterChip href={filterHref(params, "suite", undefined)} active={!params.suite}>
            All
          </FilterChip>
          {suites.map((suite) => (
            <FilterChip
              key={suite}
              href={filterHref(params, "suite", suite)}
              active={params.suite === suite}
            >
              {suite}
            </FilterChip>
          ))}
        </FilterGroup>
        <FilterGroup label="Capability">
          <FilterChip href={filterHref(params, "capability", undefined)} active={!params.capability}>
            All
          </FilterChip>
          {capabilities.map((capability) => (
            <FilterChip
              key={capability}
              href={filterHref(params, "capability", capability)}
              active={params.capability === capability}
            >
              {labelize(capability)}
            </FilterChip>
          ))}
        </FilterGroup>
        <FilterGroup label="Difficulty">
          <FilterChip href={filterHref(params, "difficulty", undefined)} active={!params.difficulty}>
            All
          </FilterChip>
          {difficulties.map((difficulty) => (
            <FilterChip
              key={difficulty}
              href={filterHref(params, "difficulty", difficulty)}
              active={params.difficulty === difficulty}
            >
              {difficulty}
            </FilterChip>
          ))}
        </FilterGroup>
        <FilterGroup label="Readiness">
          <FilterChip href={filterHref(params, "ready", undefined)} active={!params.ready}>
            All
          </FilterChip>
          <FilterChip href={filterHref(params, "ready", "yes")} active={params.ready === "yes"}>
            Benchmark-ready
          </FilterChip>
          <FilterChip
            href={filterHref(params, "ready", "reviewed")}
            active={params.ready === "reviewed"}
          >
            Reviewed
          </FilterChip>
        </FilterGroup>
      </section>

      <div className="grid gap-5 md:grid-cols-2">
        {filteredTasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </>
  );
}

function TaskCard({ task }: { task: BenchmarkTask }) {
  const diff = DIFFICULTY_STYLES[task.difficulty] ?? DIFFICULTY_STYLES.easy;
  const DiffIcon = diff.icon;
  const reviewed = Boolean(task.safety_reviewed && task.deterministic_scoring);

  return (
    <div className="group flex flex-col rounded-xl border border-zinc-800 bg-zinc-900 p-6 transition-all duration-150 hover:border-zinc-700">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex flex-wrap gap-2">
            <span className="rounded-md border border-zinc-800 px-2 py-1 text-xs font-medium text-zinc-400">
              {task.suite ?? "core"}
            </span>
            {task.benchmark_ready && (
              <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                Ready
              </span>
            )}
            {reviewed && (
              <span className="inline-flex items-center gap-1 rounded-md bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-300">
                <ShieldCheck className="h-3 w-3" />
                Reviewed
              </span>
            )}
          </div>
          <h2 className="text-lg font-semibold leading-snug text-zinc-50">
            {task.title}
          </h2>
        </div>
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold uppercase ${diff.text} ${diff.bg}`}
        >
          <DiffIcon className="h-3 w-3" />
          {task.difficulty}
        </span>
      </div>
      <p className="mt-3 flex-1 text-sm leading-relaxed text-zinc-400">
        {task.description}
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <span className="rounded-md bg-zinc-800 px-2 py-1 text-xs text-zinc-400">
          {labelize(task.capability ?? "code_generation")}
        </span>
        {(task.tags ?? []).slice(0, 4).map((tag) => (
          <span
            key={tag}
            className="rounded-md border border-zinc-800 px-2 py-1 text-xs text-zinc-500"
          >
            {tag}
          </span>
        ))}
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-zinc-800 pt-4 text-xs text-zinc-500">
        <span>
          {task.language} - scored on{" "}
          <span className="font-medium text-zinc-300">{task.scorer}</span>
        </span>
        <Link
          href={`/submit?task=${task.id}`}
          className="inline-flex items-center gap-1 font-semibold text-blue-400 transition-colors hover:text-blue-300 group-hover:gap-2"
        >
          Attempt <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
    </div>
  );
}

function FilterGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-2 border-t border-zinc-800 py-3 md:grid-cols-[110px_1fr]">
      <div className="text-xs font-semibold uppercase text-zinc-500">{label}</div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

function FilterChip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors ${
        active
          ? "border-blue-500/40 bg-blue-500/10 text-blue-300"
          : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:text-zinc-200"
      }`}
    >
      {children}
    </Link>
  );
}

function filterHref(params: TaskFilters, key: keyof TaskFilters, value: string | undefined) {
  const next = new URLSearchParams();
  (Object.entries(params) as [keyof TaskFilters, string | undefined][]).forEach(([name, current]) => {
    if (current && name !== key) next.set(name, current);
  });
  if (value) next.set(key, value);
  const query = next.toString();
  return query ? `/tasks?${query}` : "/tasks";
}

function unique(values: (string | undefined)[]) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function labelize(value: string) {
  return value.replace(/_/g, " ");
}
