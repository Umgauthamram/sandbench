// Placeholder data so every screen renders before the backend exists.
// TODO: replace each export with a fetch() against the FastAPI gateway
//       (GET /runs, GET /runs/{id}, GET /leaderboard, GET /tasks).

import type {
  BenchmarkTask,
  LeaderboardEntry,
  Run,
} from "./types";

export const TASKS: BenchmarkTask[] = [
  {
    id: "fizzbuzz",
    title: "FizzBuzz",
    language: "python",
    difficulty: "easy",
    description:
      "Print numbers 1–100, replacing multiples of 3 with Fizz, 5 with Buzz, and 15 with FizzBuzz.",
    scorer: "fraction of unit tests passed",
    broken_code: `def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(i)  # bug: should be str(i)
    return out
`,
  },
  {
    id: "json-flatten",
    title: "Flatten nested JSON",
    language: "python",
    difficulty: "medium",
    description:
      "Implement flatten(obj) that collapses a nested dict into dot-delimited keys.",
    scorer: "fraction of unit tests passed",
    broken_code: `def flatten(obj, prefix="", sep="."):
    result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            result[prefix + k] = v  # bug: doesn't recurse into nested dicts/lists
    return result
`,
  },
];


export const RUNS: Run[] = [
  {
    id: "run_8f2a",
    submissionId: "sub_8f2a",
    type: "code",
    language: "python",
    taskId: "fizzbuzz",
    taskTitle: "FizzBuzz",
    status: "done",
    verdict: "clean",
    score: 1.0,
    startedAt: "2026-06-12T08:41:02Z",
    finishedAt: "2026-06-12T08:41:09Z",
    flags: [],
    suggestions: [],
    logs: [
      "[orchestrator] pulled job run_8f2a",
      "[sandbox] spawning python:3.11-slim (--network none, --read-only, --cap-drop ALL)",
      "[sandbox] copying payload (412 bytes)",
      "[run] pytest -q",
      "[run] 12 passed in 0.31s",
      "[monitor] no egress attempts, no fs escape, exit 0",
      "[verdict] CLEAN — score 100",
      "[sandbox] container destroyed",
    ],
  },
  {
    id: "run_3c7d",
    submissionId: "sub_3c7d",
    type: "code",
    language: "python",
    taskId: "json-flatten",
    taskTitle: "Flatten nested JSON",
    status: "done",
    verdict: "broken",
    score: 0.58,
    startedAt: "2026-06-12T08:30:00Z",
    finishedAt: "2026-06-12T08:30:11Z",
    flags: [],
    suggestions: [
      {
        id: "sug_1",
        category: "tests",
        message:
          "7 of 12 tests pass. flatten() does not handle arrays nested inside objects.",
      },
      {
        id: "sug_2",
        category: "style",
        message: "ruff: 3 unused imports, 1 line over 100 chars.",
      },
      {
        id: "sug_3",
        category: "imports",
        message: "Proposed patch recurses into list items by index.",
        patchDiff: `--- a/solution.py
+++ b/solution.py
@@ -3,6 +3,11 @@ def flatten(obj, prefix=""):
     out = {}
     for k, v in obj.items():
         key = f"{prefix}.{k}" if prefix else k
-        if isinstance(v, dict):
+        if isinstance(v, list):
+            for i, item in enumerate(v):
+                out.update(flatten({str(i): item}, key))
+        elif isinstance(v, dict):
             out.update(flatten(v, key))
         else:
             out[key] = v
     return out`,
      },
    ],
    logs: [
      "[run] pytest -q",
      "[run] 7 passed, 5 failed in 0.44s",
      "[verdict] CLEAN but failing — routing to analysis engine",
      "[analysis] ruff + bandit + LLM review complete",
    ],
  },
  {
    id: "run_b91e",
    submissionId: "sub_b91e",
    type: "code",
    language: "python",
    taskId: "fizzbuzz",
    taskTitle: "FizzBuzz",
    status: "quarantined",
    verdict: "malicious",
    score: 0.0,
    startedAt: "2026-06-12T07:58:20Z",
    finishedAt: "2026-06-12T07:58:22Z",
    flags: [
      {
        id: "flag_1",
        source: "monitor",
        rule: "egress.denied",
        severity: "high",
        detail:
          "Outbound connection to 185.234.x.x:4444 blocked by --network none.",
      },
      {
        id: "flag_2",
        source: "static",
        rule: "yara:reverse_shell",
        severity: "high",
        detail: "YARA signature matched socket+subprocess reverse-shell pattern.",
      },
    ],
    suggestions: [],
    logs: [
      "[sandbox] spawning python:3.11-slim (hardened)",
      "[monitor] EGRESS ATTEMPT blocked: 185.234.x.x:4444",
      "[static] yara hit: reverse_shell",
      "[verdict] MALICIOUS — quarantine + destroy",
      "[sandbox] container force-removed, run quarantined, score 0",
    ],
  },
  {
    id: "run_d44f",
    submissionId: "sub_d44f",
    type: "code" /* "model" */,
    language: "python",
    taskId: "rate-limiter",
    taskTitle: "Token-bucket rate limiter",
    status: "running",
    startedAt: "2026-06-12T08:45:00Z",
    flags: [],
    suggestions: [],
    logs: [
      "[orchestrator] pulled job run_d44f",
      "[sandbox] spawning node:20-slim (hardened)",
      "[run] npm test --silent",
    ],
  },
];

export const LEADERBOARD: LeaderboardEntry[] = [
  {
    rank: 1,
    user: "ada",
    submissionId: "sub_8f2a",
    taskId: "fizzbuzz",
    taskTitle: "FizzBuzz",
    score: 1.0,
    verdict: "clean",
    createdAt: "2026-06-12T08:41:09Z",
  },
  {
    rank: 2,
    user: "linus",
    submissionId: "sub_22a1",
    taskId: "fizzbuzz",
    taskTitle: "FizzBuzz",
    score: 0.92,
    verdict: "clean",
    createdAt: "2026-06-11T19:02:00Z",
  },
  {
    rank: 3,
    user: "grace",
    submissionId: "sub_3c7d",
    taskId: "json-flatten",
    taskTitle: "Flatten nested JSON",
    score: 0.58,
    verdict: "broken",
    createdAt: "2026-06-12T08:30:11Z",
  },
];

export function getRun(id: string): Run | undefined {
  return RUNS.find((r) => r.id === id);
}
