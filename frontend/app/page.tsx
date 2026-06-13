import Link from "next/link";
import { SiteHeader } from "./components/site-header";
import { ShieldCheck, Trophy, Sparkles, Bot, ListTodo, ArrowRight } from "lucide-react";
import { FluidParticlesBackground } from "../components/ui/fluid-particles-background";

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Hardened sandbox verdict",
    body: "Every run gets executed inside an ephemeral, hardened container. We drop capabilities, enforce read-only roots, set CPU/Memory limits, and monitor for egress or escape attempts.",
  },
  {
    icon: Trophy,
    title: "Real hidden-test scoring",
    body: "Submissions that complete successfully are scored against a private, hidden test suite. Get an accurate score represented as a fraction of tests passed.",
  },
  { 
    icon: Sparkles,
    title: "LLM review & patch suggestions",
    body: "Clean but failing submissions are automatically reviewed by an LLM model, producing suggestions and a concrete patch diff to fix the bug.",
  },
  {
    icon: Bot,
    title: "RL repair-and-rescore loop",
    body: "Our repair pipeline automatically applies the suggested patches, re-runs the code in the sandbox, and computes the exact reward/improvement score.",
  },
  {
    icon: ListTodo,
    title: "Live leaderboard & playground",
    body: "Deduplicated scores are posted to a live leaderboard. Visualize repair trajectories, step-by-step rollout animations, and cumulative rewards in the RL playground.",
  },
];

export default function LandingPage() {
  return (
    <>
      <SiteHeader />
      <main className="flex-1 bg-zinc-950">
        {/* Hero — full viewport width, no max-width cap */}
        <section className="relative border-b border-border overflow-hidden">
          <FluidParticlesBackground className="h-auto min-h-screen py-24 sm:py-0 sm:flex sm:items-center grid-backdrop">
            {/* Full-width inner layout */}
            <div className="w-full px-8 sm:px-16 lg:px-24 xl:px-32 flex flex-col lg:flex-row items-center justify-center gap-16 py-24 sm:py-20">
              {/* Text block */}
              <div className="max-w-2xl space-y-7 text-center">
                <h1 className="text-5xl font-extrabold leading-tight tracking-tight text-zinc-50 sm:text-6xl xl:text-7xl">
                  Benchmark untrusted code in a
                  <span className="text-grad-accent"> throwaway sandbox</span>.
                </h1>
                <p className="text-xl leading-relaxed text-zinc-400">
                  Submit untrusted code. Get a verdict, a score, and an automatic repair — all in a hardened sandbox.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
                  <Link
                    href="/dashboard"
                    className="inline-flex items-center gap-2 rounded-xl bg-grad-accent px-8 py-3.5 text-base font-semibold text-white transition-transform hover:scale-[1.02] shadow-lg shadow-orange-500/20"
                  >
                    Enter platform <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    href="/signup"
                    className="rounded-xl border border-border bg-zinc-900/60 px-8 py-3.5 text-base font-semibold text-white transition-colors hover:bg-zinc-800 backdrop-blur-sm"
                  >
                    Create account
                  </Link>
                </div>
              </div>
            </div>
          </FluidParticlesBackground>
        </section>

        {/* Features — full width with controlled padding */}
        <section className="w-full px-8 sm:px-16 lg:px-24 xl:px-32 py-24 bg-zinc-950">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-blue-400">
              Core Capabilities
            </h2>
            <p className="mt-3 text-3xl font-bold tracking-tight text-zinc-50">
              One secure pipeline, from evaluation to repair
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="rounded-xl border border-border bg-zinc-900 p-6 space-y-4 hover:border-zinc-700 hover:bg-zinc-900/80 transition-all duration-200 group"
                >
                  <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20 transition-colors">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-zinc-50">
                    {f.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-zinc-400">
                    {f.body}
                  </p>
                </div>
              );
            })}
          </div>
        </section>

        {/* Stats bar */}
        <section className="border-t border-border bg-zinc-900/30">
          <div className="w-full px-8 sm:px-16 lg:px-24 xl:px-32 py-12 grid grid-cols-2 sm:grid-cols-4 gap-8 text-center">
            {[
              { label: "Sandbox isolation", value: "Docker + seccomp" },
              { label: "Scoring method", value: "Hidden test suite" },
              { label: "Repair loop", value: "LLM + RL reward" },
              { label: "Leaderboard", value: "Real-time" },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-2xl font-bold text-zinc-50">{s.value}</p>
                <p className="mt-1 text-xs uppercase tracking-wide text-zinc-500">{s.label}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-zinc-950">
        <div className="w-full px-8 sm:px-16 lg:px-24 xl:px-32 flex flex-col sm:flex-row items-center justify-between gap-4 py-10 text-sm text-zinc-500">
          <span>SandBench — isolated code benchmarking & RL environment</span>
          <span>Built for evaluation of untrusted agentic actions. Hardened Docker sandbox.</span>
        </div>
      </footer>
    </>
  );
}
