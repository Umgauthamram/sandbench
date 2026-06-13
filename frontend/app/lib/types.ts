// Shared domain types — mirror the §4 data model in the build guide.
// The frontend speaks these shapes; the FastAPI gateway will return them.

export type SubmissionType = "code" | "files" | "api" | "model";

export type Language = "python" | "node";

export type RunStatus =
  | "queued"
  | "running"
  | "done"
  | "quarantined"
  | "error";

export type Verdict = "clean" | "malicious" | "broken";

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
  | "style";

export interface Suggestion {
  id: string;
  category: SuggestionCategory;
  message: string;
  patchDiff?: string;
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
  score?: number;
  startedAt?: string;
  finishedAt?: string;
  flags: SecurityFlag[];
  suggestions: Suggestion[];
  logs: string[];
}

export interface BenchmarkTask {
  id: string;
  title: string;
  language: Language;
  difficulty: "easy" | "medium" | "hard";
  description: string;
  scorer: string;
}

export interface LeaderboardEntry {
  rank: number;
  user: string;
  submissionId: string;
  taskId: string;
  taskTitle: string;
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
