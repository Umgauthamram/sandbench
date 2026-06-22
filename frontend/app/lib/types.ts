// Shared domain types — mirror the §4 data model in the build guide.
// The frontend speaks these shapes; the FastAPI gateway will return them.

// "model_eval" is a JOB type (Phase 2 RL eval), enqueued via /api/rl-eval.
// The submit page still only offers "code" and "files".
export type SubmissionType = "code" | "files" | "model_eval" /* | "api" | "model" */;

export type Language = "python" | "node";

export type RunStatus =
  | "queued"
  | "running"
  | "done"
  | "quarantined"
  | "error";

export type Verdict = "clean" | "suspicious" | "malicious" | "broken";

export type FlagSource = "monitor" | "static";
export type Severity = "low" | "medium" | "high";

export interface SecurityFlag {
  id: string;
  source: FlagSource;
  rule: string;
  severity: Severity;
  detail: string;
}

export type SuggestionCategory =
  | "layout"
  | "imports"
  | "security"
  | "tests"
  | "style"
  | "system";

export interface Suggestion {
  id: string;
  category: SuggestionCategory;
  message: string;
  patchDiff?: string;
}

export interface RunRepair {
  attempted: boolean;
  applied: boolean;
  method: string;
  score_before: number;
  score_after: number | null;
  reward: number | null;
}

export interface Run {
  id: string;
  submissionId: string;
  type: SubmissionType;
  language: Language;
  taskId: string;
  taskTitle: string;
  status: RunStatus;
  verdict?: Verdict;
  /** Score as a fraction in [0.0, 1.0]. 1.0 = all tests passed. Display as percentage (×100). */
  score?: number;
  startedAt?: string;
  finishedAt?: string;
  flags: SecurityFlag[];
  suggestions: Suggestion[];
  logs: string[];
  repair?: RunRepair;
  userId?: string;
  userName?: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  passwordHash: string; // never sent to client
  createdAt: string;
}

// Safe projection (no passwordHash):
export type SafeUser = Omit<User, "passwordHash">;

export interface BenchmarkTask {
  id: string;
  title: string;
  language: Language;
  difficulty: "easy" | "medium" | "hard";
  description: string;
  entrypoint?: string;
  scorer: string;
  broken_code?: string; // intentionally buggy seed for RL eval
  suite?: string;
  capability?: string;
  tags?: string[];
  source?: string;
  version?: string;
  human_baseline_minutes?: number | null;
  hidden_test_files?: number;
  benchmark_ready?: boolean;
}

export interface LeaderboardEntry {
  rank: number;
  user: string;
  submissionId: string;
  taskId: string;
  taskTitle: string;
  /** Score as a fraction in [0.0, 1.0]. Display as percentage (×100). */
  score: number;
  verdict: Verdict;
  createdAt: string;
}

export interface SSEMessage {
  status: string;
  verdict: string | null;
  score: number | null;
  logLines: string[];
}

export interface SSEError {
  error: string;
}
