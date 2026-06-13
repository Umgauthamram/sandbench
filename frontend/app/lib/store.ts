// Data layer shared by Server Components (read directly) and API route
// handlers (read + write). Backed by Upstash Redis when configured;
// otherwise an in-memory store seeded from mock data so the app runs locally
// with zero setup.
//
// Redis layout:
//   run:{id}            → JSON-encoded Run
//   runs:index          → list of run ids, newest first
//   sandbench:jobs      → job queue; the Python worker BRPOPs {runId}
//   leaderboard         → JSON-encoded LeaderboardEntry[]

import { redis, redisConfigured } from "./redis";
import { LEADERBOARD, RUNS, TASKS } from "./mock";
import { getCurrentUser } from "./auth";
import type {
  BenchmarkTask,
  LeaderboardEntry,
  Language,
  Run,
  SubmissionType,
} from "./types";

const RUN_KEY = (id: string) => `run:${id}`;
const RUNS_INDEX = "runs:index";
const JOB_QUEUE = "sandbench:jobs";

// ── In-memory fallback (module-scoped; resets on server restart) ──
const mem = {
  runs: new Map<string, Run>(RUNS.map((r) => [r.id, r])),
  order: RUNS.map((r) => r.id),
};

export interface SubmitInput {
  type: SubmissionType;
  taskId: string;
  payload?: string; // code text, endpoint URL, etc.
  archiveB64?: string;
  archiveKind?: string; // "zip" | "targz"
}

function newId(): string {
  return "run_" + crypto.randomUUID().replace(/-/g, "").slice(0, 8);
}

export async function listRuns(userId?: string): Promise<Run[]> {
  if (!redisConfigured) {
    const runs = mem.order.map((id) => mem.runs.get(id)!);
    if (userId) return runs.filter((r) => r.userId === userId);
    return runs;
  }
  const ids = await redis.lrange(RUNS_INDEX, 0, 99);
  if (!ids?.length) return [];
  const runs = await Promise.all(ids.map(getRun));
  const filtered = runs.filter((r): r is Run => r !== null);
  if (userId) {
    return filtered.filter((r) => r.userId === userId);
  }
  return filtered;
}

export async function getRun(id: string): Promise<Run | null> {
  if (!redisConfigured) return mem.runs.get(id) ?? null;
  const raw = await redis.get(RUN_KEY(id));
  return raw ? (JSON.parse(raw) as Run) : null;
}

export async function createRun(input: SubmitInput): Promise<Run> {
  const tasks = await listTasks();
  const task = tasks.find((t) => t.id === input.taskId);
  const language: Language = task?.language ?? "python";
  const id = newId();

  const user = await getCurrentUser();
  const userId = user?.id;
  const userName = user?.name;

  const run: Run = {
    id,
    submissionId: "sub_" + id.slice(4),
    type: input.type,
    language,
    taskId: input.taskId,
    taskTitle: task?.title ?? input.taskId,
    status: "queued",
    flags: [],
    suggestions: [],
    logs: ["[gateway] submission accepted, job enqueued"],
    startedAt: new Date().toISOString(),
    userId,
    userName,
  };

  if (!redisConfigured) {
    mem.runs.set(id, run);
    mem.order.unshift(id);
    return run;
  }

  await redis.set(RUN_KEY(id), JSON.stringify(run));
  await redis.lpush(RUNS_INDEX, id);
  // Hand the job to the worker. payload travels with the job so the worker
  // can copy it into the sandbox.
  await redis.lpush(
    JOB_QUEUE,
    JSON.stringify({ runId: id, language, userId, userName, ...input }),
  );
  return run;
}

export async function listLeaderboard(): Promise<LeaderboardEntry[]> {
  if (!redisConfigured) return LEADERBOARD;
  const raw = await redis.get("leaderboard");
  if (!raw) return [];
  const entries = JSON.parse(raw) as LeaderboardEntry[];
  // Ensure sorted by score descending with ranks assigned
  entries.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  entries.forEach((e, i) => { e.rank = i + 1; });
  return entries;
}

export async function listTasks(): Promise<BenchmarkTask[]> {
  if (redisConfigured) {
    try {
      const raw = await redis.get("tasks");
      if (raw) {
        return JSON.parse(raw) as BenchmarkTask[];
      }
    } catch (err) {
      console.error("Failed to read tasks from Redis:", err);
    }
  }
  return TASKS;
}

export async function listRepairRuns(userId?: string): Promise<Run[]> {
  const runs = await listRuns(userId);
  return runs
    .filter((r) => r.repair?.attempted === true)
    .slice(0, 20);
}
