import type { RunStatus, Severity, Verdict } from "../lib/types";

const VERDICT_STYLES: Record<Verdict, string> = {
  clean: "bg-clean/15 text-clean ring-clean/30",
  malicious: "bg-malicious/15 text-malicious ring-malicious/30",
  broken: "bg-broken/15 text-broken ring-broken/30",
};

const VERDICT_LABELS: Record<Verdict, string> = {
  clean: "Clean",
  malicious: "Malicious",
  broken: "Broken",
};

export function VerdictBadge({ verdict }: { verdict?: Verdict }) {
  if (!verdict) {
    return (
      <span className="inline-flex items-center rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700">
        Pending
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${VERDICT_STYLES[verdict]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {VERDICT_LABELS[verdict]}
    </span>
  );
}

const STATUS_STYLES: Record<RunStatus, string> = {
  queued: "bg-zinc-800 text-zinc-400 ring-zinc-700",
  running: "bg-accent/15 text-accent ring-accent/30",
  done: "bg-clean/15 text-clean ring-clean/30",
  quarantined: "bg-malicious/15 text-malicious ring-malicious/30",
  error: "bg-broken/15 text-broken ring-broken/30",
};

export function StatusPill({ status }: { status: RunStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${STATUS_STYLES[status]}`}
    >
      {status === "running" && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {status}
    </span>
  );
}

const SEVERITY_STYLES: Record<Severity, string> = {
  low: "bg-zinc-800 text-zinc-300 ring-zinc-700",
  medium: "bg-broken/15 text-broken ring-broken/30",
  high: "bg-malicious/15 text-malicious ring-malicious/30",
};

export function SeverityTag({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ${SEVERITY_STYLES[severity]}`}
    >
      {severity}
    </span>
  );
}
