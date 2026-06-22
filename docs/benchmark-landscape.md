# SandBench Benchmark Landscape

Research date: 2026-06-22 (Asia/Calcutta)

This note compares SandBench against related agent, code, and safety benchmark projects. The goal is not to clone every feature, but to identify the combined feature set SandBench should grow toward.

## Projects Reviewed

| Project | Relevant features | What SandBench should learn |
| --- | --- | --- |
| SWE-bench | Real GitHub issue tasks, patch-based scoring, Docker-based reproducible evaluation, Lite/Verified/Multimodal/Multilingual variants, leaderboards, cloud runners. | Add repository-level repair tasks, versioned task suites, official run artifacts, and stricter patch contracts. |
| Terminal-Bench | Terminal sandbox tasks with English instruction, test script, oracle solution, versioned datasets, CLI harness, public dashboard/leaderboard. | Make each SandBench task include instruction, hidden tests, reference solution, task version, tags, and reproducible run manifest. |
| Inspect AI | Composable tasks/datasets/solvers/scorers, model providers, agents, tools, sandbox backends, log viewer, analysis utilities, ready-to-run evals. | Separate task definition, solver/model adapter, scorer, sandbox backend, and analysis logs as first-class interfaces. |
| AgentBench | Multi-environment agent evaluation across OS, DB, KG, WebShop, ALFWorld, etc.; containerized task workers and controller/worker orchestration. | Add environment categories beyond single-file code: OS, database, web/API, security-defense, and multi-step backend tasks. |
| OpenAI Evals | Eval registry, private/custom evals, completion function protocol, dashboard support, JSON/YAML eval templates. | Add a clean eval authoring format and model adapter contract so users can bring any agent or model endpoint. |
| Cybench | Professional CTF tasks, subtasks for partial progress, Kali/task-server environment, leaderboard metrics like guided/unguided solve rate. | Add graded subtasks and safety-aware cyber tasks, but keep them strictly sandboxed and defensive by default. |
| PurpleLlama CybersecurityBenchmarks | Prompt injection, insecure code generation, code interpreter, vulnerability exploitation, autonomous offensive cyber, AutoPatch, SOC eval categories. | Build a safety test suite: prompt injection, secret exfiltration, insecure code, code interpreter misuse, and auto-patch quality. |
| BigCodeBench | 1,140 practical code tasks, diverse library/function calls, Complete/Instruct splits, pass@k output files, local/remote/E2B execution. | Add larger task inventory, pass@k/batch eval support, result JSONL artifacts, and deterministic sampling controls. |
| METR/HCAST-style work | Human-calibrated task durations, time-horizon metrics, monitorability evaluations, agent evaluation at scale. | Store human-baseline minutes, task duration class, autonomy level, and monitorability signals in task metadata. |

## SandBench Today

SandBench already has useful phase-1 foundations:

- Next.js frontend with Redis-backed runs, tasks, leaderboard, auth, and queue submission.
- Python worker that consumes `sandbench:jobs`.
- Hardened Docker execution with no network, read-only root, dropped caps, PID/memory/CPU limits, seccomp, and cleanup.
- Static gates with Bandit, Semgrep, YARA, and obfuscation heuristics.
- SSRF guard for host-side model endpoint calls.
- Pytest-fraction scorer and a basic repair/eval loop.
- Small task registry and leaderboard updates.

The main gaps are benchmark quality and operational rigor:

- Too few tasks, and current tasks are mostly toy function-level checks.
- Task schema was loose; metadata for suites, tags, source, versions, human baselines, and benchmark readiness was missing.
- No official run manifest, artifact bundle, pass@k, retry accounting, or cost accounting.
- Model support is endpoint/API-key based, not a typed adapter system with provider capabilities and limits.
- Safety tests exist as code paths but are not packaged as an explicit safety benchmark suite.
- Leaderboard is useful for a demo but not leaderboard-grade: no suite versions, no contamination policy, no replayable artifacts, no signed/immutable submissions.
- CI and deployment checks need to become stricter before task scale-up.

## Target Combined Feature Set

For the next phase, SandBench should become a secure benchmark gateway with four clear surfaces:

1. **Task suites**: versioned task packs with metadata, hidden tests, reference solutions, tags, human-baseline estimates, and benchmark-readiness flags.
2. **Execution harness**: strict sandbox runner, task-specific environments, deterministic scoring, retries, pass@k, artifacts, and audit logs.
3. **Model/agent adapters**: OpenAI-compatible endpoint support plus named providers, external CLI agents, local models, cost/token tracking, and safe secrets handling.
4. **Safety evaluation**: static/dynamic security gates, prompt-injection tasks, code-interpreter abuse checks, exfiltration/SSRF tests, insecure-code tests, and monitorability traces.

## Source Links

- SWE-bench: https://github.com/swe-bench/SWE-bench
- SWE-bench site: https://www.swebench.com/
- Terminal-Bench: https://github.com/harbor-framework/terminal-bench
- Terminal-Bench site: https://www.tbench.ai/
- Inspect AI: https://inspect.aisi.org.uk/
- AgentBench: https://github.com/THUDM/AgentBench
- OpenAI Evals: https://github.com/openai/evals
- Cybench: https://cybench.github.io/
- PurpleLlama CybersecurityBenchmarks: https://github.com/meta-llama/PurpleLlama/tree/main/CybersecurityBenchmarks
- BigCodeBench: https://github.com/bigcode-project/bigcodebench
- SWE-Lancer: https://github.com/openai/SWELancer-Benchmark
- METR: https://metr.org/
