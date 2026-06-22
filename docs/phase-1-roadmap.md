# SandBench Phase 1 Roadmap

This plan assumes a 2-4 week push. The near-term goal is to turn the current prototype into a benchmark platform foundation: not fully mature, but structured enough that new tasks, model adapters, and safety checks can be added without rewiring everything.

## Week 1: Benchmark Contract And Safety Baseline

- Lock the task schema: suite, capability, tags, source, version, human baseline, hidden test count, benchmark readiness.
- Add registry tests so malformed tasks fail fast.
- Add 3-5 more non-toy Python tasks: stateful backend logic, data transformation, dependency-light algorithms, and security-fix tasks.
- Add safety benchmark tasks for SSRF, secret exfiltration, filesystem writes, process abuse, and obfuscation.
- Add a run manifest shape for every scored run: task version, sandbox config, model/adapter name, score, flags, timing, repair data, and artifact hashes.
- Make README setup truthful for local Redis, Docker image building, and non-integration tests.

## Week 2: Real Evaluation Harness

- Add pass@k and repeated-run evaluation for a task suite.
- Add JSONL/CSV export for benchmark results.
- Add model adapter abstraction around OpenAI-compatible endpoints, Gemini, Groq, Hugging Face, and local/custom endpoints.
- Track model name, provider, request count, duration, token/cost estimates when available, and error categories.
- Add per-task timeout/resource overrides while retaining safe global ceilings.
- Add CI for Python unit tests, frontend lint/type checks, and task registry validation.

## Week 3: Leaderboard And Artifacts

- Version leaderboard entries by suite and task version.
- Store peak score per user/task/suite and full attempt history separately.
- Add replayable artifact bundles: sanitized submitted files, run manifest, stdout/stderr excerpts, flags, score breakdown, and repair patch.
- Add benchmark-readiness gates: tasks marked `benchmark_ready: true` must have hidden tests, reference solution, metadata, safety review, and deterministic scoring.
- Add UI filters for suite, capability, difficulty, benchmark readiness, and safety flags.

## Week 4: Scale And Safety Review

- Add repository-level repair tasks with fixture projects, not just single-file entrypoints.
- Add defensive cyber/security-fix tasks while avoiding uncontrolled offensive execution.
- Add prompt-injection and code-interpreter abuse tasks inspired by safety benchmark suites.
- Add contamination policy: task source, release date, public/hidden split, and canary markers for private benchmark data.
- Run a baseline evaluation across at least two real model endpoints and one dummy/local adapter.
- Freeze a `core-v0.1` suite with docs, artifacts, and reproducible commands.

## Current Sprint Decisions

- SandBench should stay sandbox-first. Model calls happen host-side only, and sandboxed task execution remains network-disabled by default.
- Redis remains acceptable for phase 1, but the data contract must be explicit and versioned before the leaderboard is treated as authoritative.
- The first credible benchmark suite should favor deterministic Python/backend tasks and safety checks before adding expensive repository-level tasks.
- A task is not benchmark-ready until it has metadata, hidden tests, reference solution, and deterministic scoring.
