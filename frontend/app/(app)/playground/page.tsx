"use client";

import { useState } from "react";
import { PageHeader } from "../../components/ui";

type Step = {
  t: number;
  action: string;
  obs: string;
  reward: number;
};

// A canned rollout that mirrors what train_demo.py logs: an LLM-driven agent
// stepping the Gymnasium env (obs → action → reward) until it submits.
// TODO: stream real steps from the engine's rollout loop.
const ROLLOUT: Step[] = [
  { t: 0, action: "read_file(solution.py)", obs: "12-line stub, flatten() incomplete", reward: -0.01 },
  { t: 1, action: "run_tests", obs: "7 passed, 5 failed", reward: 0.58 },
  { t: 2, action: "edit_file(patch: handle lists)", obs: "patch applied", reward: -0.01 },
  { t: 3, action: "run_tests", obs: "12 passed", reward: 0.42 },
  { t: 4, action: "submit", obs: "episode end · score 100 · verdict clean", reward: 1.0 },
];

const ACTION_SPACE = [
  "run_tests",
  "read_file",
  "edit_file(patch)",
  "restructure",
  "submit",
];

export default function PlaygroundPage() {
  const [shown, setShown] = useState(0);
  const [running, setRunning] = useState(false);

  async function rollout() {
    setRunning(true);
    setShown(0);
    for (let i = 1; i <= ROLLOUT.length; i++) {
      await new Promise((r) => setTimeout(r, 500));
      setShown(i);
    }
    setRunning(false);
  }

  const steps = ROLLOUT.slice(0, shown);
  const cumulative = steps.reduce((s, st) => s + st.reward, 0);

  return (
    <>
      <PageHeader
        title="RL playground"
        subtitle="The sandbox exposed as a Gymnasium env: reset() → step(action) → (obs, reward). A house agent repairs the task; reward is logged per step."
        action={
          <button
            onClick={rollout}
            disabled={running}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-indigo-300 disabled:opacity-60"
          >
            {running ? "Rolling out…" : "Run rollout"}
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Env spec */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-panel p-5">
            <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
              Action space
            </h2>
            <ul className="mt-3 space-y-1.5">
              {ACTION_SPACE.map((a) => (
                <li
                  key={a}
                  className="rounded-md bg-background px-3 py-1.5 font-mono text-xs text-zinc-300"
                >
                  {a}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-border bg-panel p-5">
            <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
              Reward
            </h2>
            <ul className="mt-3 space-y-1.5 text-sm text-zinc-400">
              <li>
                <span className="text-clean">+</span> tests passing / score gain
              </li>
              <li>
                <span className="text-malicious">−</span> security flags
              </li>
              <li>
                <span className="text-broken">−</span> small step cost
              </li>
            </ul>
            <div className="mt-4 border-t border-border pt-4">
              <p className="text-xs uppercase tracking-wide text-zinc-500">
                Cumulative reward
              </p>
              <p className="mt-1 text-2xl font-semibold text-zinc-50">
                {cumulative.toFixed(2)}
              </p>
            </div>
          </div>
        </div>

        {/* Rollout trace */}
        <div className="lg:col-span-2">
          <div className="rounded-xl border border-border bg-panel p-5">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">
              Rollout trace
            </h2>
            {steps.length === 0 ? (
              <p className="py-12 text-center text-sm text-zinc-600">
                Press “Run rollout” to step the agent through one episode.
              </p>
            ) : (
              <ol className="space-y-3">
                {steps.map((s) => (
                  <li
                    key={s.t}
                    className="rounded-lg border border-border bg-background p-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs text-zinc-500">
                        t={s.t}
                      </span>
                      <span
                        className={`font-mono text-sm font-semibold ${s.reward >= 0 ? "text-clean" : "text-broken"}`}
                      >
                        {s.reward >= 0 ? "+" : ""}
                        {s.reward.toFixed(2)}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-sm text-accent">
                      → {s.action}
                    </div>
                    <div className="mt-1 text-sm text-zinc-400">{s.obs}</div>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
