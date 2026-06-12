import Link from "next/link";
import { SiteHeader } from "./components/site-header";

const STEPS = [
  {
    title: "Submit",
    body: "Drop in code, files, an API endpoint, or your own model's API key — then pick a benchmark task.",
  },
  {
    title: "Isolate",
    body: "Every run gets a fresh, hardened, throwaway container from a clean golden image. Destroyed after. Never reused.",
  },
  {
    title: "Branch",
    body: "Malicious or compromised → killed, quarantined, reported. Clean but messy → static analysis + an LLM review with a patch.",
  },
  {
    title: "Score",
    body: "Each run is scored against the task and lands on the leaderboard.",
  },
];

const FEATURES = [
  {
    tag: "Subsystem A",
    title: "Benchmark platform",
    body: "Submit and get scored + analyzed in full isolation. Hardened Docker with --network none, read-only root, dropped caps, seccomp, and hard resource + wall-clock limits.",
  },
  {
    tag: "Subsystem B",
    title: "RL environment",
    body: "The same sandbox exposed as a Gymnasium-style obs → action → reward env. A house agent runs and repairs tasks; reward is logged every step.",
  },
  {
    tag: "The core branch",
    title: "Malicious vs. messy",
    body: "Any high-severity flag — egress attempt, filesystem escape, YARA hit, OOM/fork-bomb — quarantines the run. Everything else routes to analysis for concrete fixes.",
  },
];

export default function LandingPage() {
  return (
    <>
      <SiteHeader />
      <main className="flex-1">
        {/* Hero */}
        <section className="grid-backdrop relative border-b border-border">
          <div className="mx-auto w-full max-w-6xl px-6 py-24 sm:py-32">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-panel px-3 py-1 text-xs text-zinc-400">
              <span className="h-1.5 w-1.5 rounded-full bg-clean" />
              Run untrusted code without trusting it
            </span>
            <h1 className="mt-6 max-w-3xl text-balance text-4xl font-semibold leading-tight tracking-tight text-zinc-50 sm:text-6xl">
              Benchmark anything in a{" "}
              <span className="text-accent">throwaway sandbox</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-400">
              Submit code, files, an API, or your own model. SandBench runs it
              in a fresh hardened container, watches its behaviour, kills
              anything malicious, reviews what&apos;s messy, and scores it on a
              leaderboard.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/signup"
                className="rounded-lg bg-zinc-50 px-5 py-3 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200"
              >
                Get started
              </Link>
              <Link
                href="/dashboard"
                className="rounded-lg border border-border bg-panel px-5 py-3 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-800"
              >
                Open the demo dashboard →
              </Link>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="mx-auto w-full max-w-6xl px-6 py-20">
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
            One pipe, end to end
          </h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <div
                key={s.title}
                className="rounded-xl border border-border bg-panel p-5"
              >
                <div className="text-sm font-mono text-accent">
                  0{i + 1}
                </div>
                <h3 className="mt-3 text-lg font-semibold text-zinc-50">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-zinc-400">{s.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Subsystems */}
        <section className="border-t border-border bg-panel/40">
          <div className="mx-auto grid w-full max-w-6xl gap-4 px-6 py-20 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-xl border border-border bg-panel p-6"
              >
                <span className="text-xs font-medium uppercase tracking-wide text-accent">
                  {f.tag}
                </span>
                <h3 className="mt-3 text-xl font-semibold text-zinc-50">
                  {f.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-zinc-400">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="mx-auto w-full max-w-6xl px-6 py-24 text-center">
          <h2 className="text-3xl font-semibold tracking-tight text-zinc-50">
            Treat every submission as hostile.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-zinc-400">
            Clone if affected: never repair a dirty container. Spawn a clean one
            from the golden snapshot, run, score, destroy.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link
              href="/signup"
              className="rounded-lg bg-accent px-5 py-3 text-sm font-medium text-zinc-950 transition-colors hover:bg-indigo-300"
            >
              Create an account
            </Link>
            <Link
              href="/leaderboard"
              className="rounded-lg border border-border bg-panel px-5 py-3 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-800"
            >
              View leaderboard
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-zinc-500">
          <span>SandBench — isolated code benchmarking & RL environment</span>
          <span>Built for a 30-hour sprint. MVP isolation: hardened Docker.</span>
        </div>
      </footer>
    </>
  );
}
