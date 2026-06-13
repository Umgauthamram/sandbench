"use client";

import { useState } from "react";
import type { Run } from "../lib/types";

const ACTION_SPACE = [
  "run_tests",
  "read_file",
  "edit_file(patch)",
  "restructure",
  "submit",
];

export function RolloutReplay({ rollouts }: { rollouts: Run[] }) {
  const [selectedId, setSelectedId] = useState(rollouts[0].id);
  const [shown, setShown] = useState(1);
  const [running, setRunning] = useState(false);

  const selectedRun = rollouts.find((r) => r.id === selectedId) || rollouts[0];

  const scoreBefore = selectedRun.repair?.score_before ?? 0;
  const scoreAfter = selectedRun.repair?.score_after ?? 0;
  const reward = selectedRun.repair?.reward ?? 0;
  const applied = selectedRun.repair?.applied ?? false;
  const method = selectedRun.repair?.method ?? "";

  const steps = [
    {
      t: 0,
      action: "reset",
      obs: `scored initial submission: ${Math.round(scoreBefore * 100)}%`,
      reward: 0,
    },
    {
      t: 1,
      action: applied ? "submit_patch" : `submit_patch (failed to apply)`,
      obs: applied
        ? `re-scored patched code: ${Math.round(scoreAfter * 100)}%`
        : `patch did not apply (${method})`,
      reward: reward,
    },
  ];

  const currentSteps = steps.slice(0, shown);
  const cumulative = currentSteps.reduce((sum, s) => sum + s.reward, 0);

  const patchDiff = selectedRun.suggestions.find((s) => s.patchDiff)?.patchDiff;

  async function startReplay() {
    setRunning(true);
    setShown(1);
    await new Promise((r) => setTimeout(r, 800));
    setShown(2);
    setRunning(false);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Specs Column */}
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
              {cumulative >= 0 ? "+" : ""}
              {cumulative.toFixed(2)}
            </p>
          </div>
        </div>
      </div>

      {/* Rollout list & trace Panel */}
      <div className="lg:col-span-2 grid gap-6 md:grid-cols-3 rounded-xl border border-border bg-panel p-5">
        {/* List of Rollouts */}
        <div className="md:col-span-1 border-r border-border pr-4 space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
            Rollouts ({rollouts.length})
          </h2>
          <div className="space-y-2 overflow-y-auto max-h-[400px] pr-1">
            {rollouts.map((r) => {
              const rScoreBefore = r.repair?.score_before ?? 0;
              const rScoreAfter = r.repair?.score_after ?? 0;
              const rReward = r.repair?.reward ?? 0;
              return (
                <button
                  key={r.id}
                  onClick={() => {
                    setSelectedId(r.id);
                    setShown(1);
                  }}
                  className={`w-full text-left p-3 rounded-lg border text-xs transition-colors ${
                    r.id === selectedId
                      ? "border-accent bg-accent/5"
                      : "border-border hover:bg-background"
                  }`}
                >
                  <div className="font-mono font-semibold text-zinc-300">
                    {r.id}
                  </div>
                  <div className="text-zinc-500 mt-1 truncate">
                    {r.taskTitle}
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[10px] text-zinc-400">
                      {Math.round(rScoreBefore * 100)}% → {Math.round(rScoreAfter * 100)}%
                    </span>
                    <span
                      className={`font-mono font-semibold ${
                        rReward >= 0 ? "text-clean" : "text-broken"
                      }`}
                    >
                      {rReward >= 0 ? "+" : ""}
                      {rReward.toFixed(2)}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Trace Detail & Replay */}
        <div className="md:col-span-2 flex flex-col justify-between pl-2 min-h-[400px]">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
                Rollout trace
              </h2>
              <button
                onClick={startReplay}
                disabled={running}
                className="rounded-lg bg-accent px-4 py-1.5 text-xs font-medium text-zinc-950 transition-colors hover:bg-indigo-300 disabled:opacity-60"
              >
                {running ? "Rolling out…" : "Run rollout"}
              </button>
            </div>

            <ol className="space-y-3">
              {currentSteps.map((s) => (
                <li
                  key={s.t}
                  className="rounded-lg border border-border bg-background p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-zinc-500">
                      t={s.t}
                    </span>
                    <span
                      className={`font-mono text-sm font-semibold ${
                        s.reward >= 0 ? "text-clean" : "text-broken"
                      }`}
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
          </div>

          {/* Collapsible Patch Diff */}
          {patchDiff && (
            <div className="mt-6 border-t border-border pt-4">
              <details className="group">
                <summary className="cursor-pointer text-xs font-medium text-zinc-500 hover:text-zinc-300 outline-none select-none flex items-center gap-1.5">
                  <span className="transition-transform group-open:rotate-90">▶</span>
                  Show suggested patch diff
                </summary>
                <pre className="mt-3 overflow-auto rounded-lg bg-background p-4 font-mono text-xs leading-6 max-h-[200px]">
                  {patchDiff.split("\n").map((line, i) => (
                    <div
                      key={i}
                      className={
                        line.startsWith("+")
                          ? "text-clean"
                          : line.startsWith("-")
                            ? "text-malicious"
                            : "text-zinc-500"
                      }
                    >
                      {line || " "}
                    </div>
                  ))}
                </pre>
              </details>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
