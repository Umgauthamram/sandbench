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
}

function newId(): string {
  return "run_" + crypto.randomUUID().replace(/-/g, "").slice(0, 8);
}

export async function listRuns(): Promise<Run[]> {
  if (!redisConfigured) return mem.order.map((id) => mem.runs.get(id)!);
  const ids = await redis.lrange(RUNS_INDEX, 0, 49);
  if (!ids?.length) return [];
  const runs = await Promise.all(ids.map(getRun));
  return runs.filter((r): r is Run => r !== null);
}

export async function getRun(id: string): Promise<Run | null> {
  if (!redisConfigured) return mem.runs.get(id) ?? null;
  const raw = await redis.get(RUN_KEY(id));
  return raw ? (JSON.parse(raw) as Run) : null;
}

export async function createRun(input: SubmitInput): Promise<Run> {
  const task = TASKS.find((t) => t.id === input.taskId);
  const language: Language = task?.language ?? "python";
  const id = newId();

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
    JSON.stringify({ runId: id, language, ...input }),
  );
  return run;
}

export async function listLeaderboard(): Promise<LeaderboardEntry[]> {
  if (!redisConfigured) return LEADERBOARD;
  const raw = await redis.get("leaderboard");
  return raw ? (JSON.parse(raw) as LeaderboardEntry[]) : [];
}

export async function listTasks(): Promise<BenchmarkTask[]> {
  // Benchmark tasks are part of the deployed app, not user data.
  return TASKS;
}
