# SandBench 5-Phase Upgrade Roadmap 🚀

> **Goal**: Transform SandBench from a hackathon-winning prototype into a production-grade, industry-competitive AI code benchmarking platform — executed in 5 sequential phases.

---

## Current State Assessment

SandBench today has solid Phase-0 foundations:

| Component | Status | Key Files |
|---|---|---|
| **Frontend** | Next.js with auth, dashboard, leaderboard, submit, RL-eval pages | [app/](file:///g:/projects/sandbench/frontend/app) |
| **Engine Worker** | Redis-backed Python worker with job queue | [worker.py](file:///g:/projects/sandbench/engine/worker.py) |
| **Sandbox** | Hardened Docker execution (no-net, read-only, capped resources) | [runner.py](file:///g:/projects/sandbench/engine/sandbox/runner.py) |
| **Static Gates** | Bandit, Semgrep, YARA, obfuscation heuristics | [static_gate.py](file:///g:/projects/sandbench/engine/sandbox/static_gate.py) |
| **Scoring** | Pytest-fraction scorer with 3 toy tasks | [scoring/](file:///g:/projects/sandbench/engine/scoring) |
| **RL Repair** | Gymnasium-style env, model eval, rollout demo | [rl_env/](file:///g:/projects/sandbench/engine/rl_env) |
| **Task Registry** | 3 tasks: fizzbuzz, json-flatten, rate-limiter | [tasks/](file:///g:/projects/sandbench/engine/scoring/tasks) |

### Key Gaps (from [benchmark-landscape.md](file:///g:/projects/sandbench/docs/benchmark-landscape.md))
- Too few tasks, mostly toy function-level
- Loose task schema — missing metadata for suites, tags, versions, human baselines
- No run manifest, artifact bundles, pass@k, retry/cost accounting
- Model support is raw API-key-based, not a typed adapter system
- Safety tests exist as code paths but aren't packaged as a benchmark suite
- Leaderboard not production-grade (no versioning, no contamination policy, no immutable submissions)

---

## Phase 1: Benchmark Contract & Task Foundation 🏗️

> **Goal**: Lock the data contracts and build enough real tasks to make evaluation meaningful.

### 1.1 — Task Schema & Registry Hardening

#### [MODIFY] [registry.py](file:///g:/projects/sandbench/engine/scoring/registry.py)
- Define a strict `TaskSchema` dataclass/Pydantic model with required fields:
  ```
  id, suite, capability, tags[], source, version, difficulty,
  human_baseline_minutes, hidden_test_count, reference_solution_hash,
  benchmark_ready: bool, created_at, updated_at
  ```
- Add registry validation: malformed or incomplete tasks fail fast on load
- Add `benchmark_ready` gate: tasks without hidden tests + reference solution + metadata cannot be marked ready

#### [NEW] `engine/scoring/schema.py`
- Pydantic models for `TaskDefinition`, `TaskSuite`, `RunManifest`
- Validation logic with clear error messages

#### [MODIFY] [score.py](file:///g:/projects/sandbench/engine/scoring/score.py)
- Update scorer to populate run manifest fields alongside score

### 1.2 — Task Expansion (Target: 10+ real tasks)

#### [NEW] 5-7 new task directories under `engine/scoring/tasks/`
Add non-toy Python tasks across capability categories:

| Task | Category | Difficulty |
|---|---|---|
| `lru-cache` | Data Structures | Medium |
| `csv-pipeline` | Data Transformation | Medium |
| `jwt-validator` | Security / Auth | Medium |
| `rest-api-parser` | Backend Logic | Medium |
| `sql-injection-fix` | Security Fix | Hard |
| `async-rate-limiter` | Concurrency | Hard |
| `config-parser` | File I/O | Easy |

Each task includes: `task.json` (metadata), `starter.py`, `test_solution.py` (hidden), `reference.py` (solution)

### 1.3 — Run Manifest

#### [MODIFY] [worker.py](file:///g:/projects/sandbench/engine/worker.py)
- After every scored run, produce a `RunManifest` object:
  ```
  run_id, task_id, task_version, suite, sandbox_config_hash,
  model_adapter_name, score, flags[], timing{queue,exec,total},
  repair_attempts, artifact_hashes{}, created_at
  ```
- Store manifest alongside run results in Redis

### 1.4 — Tests & CI Foundation

#### [NEW] `engine/tests/test_registry.py`
- Validate all tasks load correctly
- Validate schema enforcement rejects malformed tasks

#### [NEW] `engine/tests/test_schema.py`
- Unit tests for Pydantic models and validation

### Deliverables
- [ ] Strict task schema with validation
- [ ] 10+ task definitions (3 existing + 7 new)
- [ ] Run manifest stored with every execution
- [ ] Registry tests passing
- [ ] Updated README setup docs

---

## Phase 2: Execution Harness & Model Adapters 🔧

> **Goal**: Build a real evaluation harness with pass@k, typed model adapters, and result exports.

### 2.1 — Pass@k Evaluation Engine

#### [NEW] `engine/evaluation/harness.py`
- `evaluate_suite(suite_id, model_adapter, k=1, n=5)` → runs tasks k times each
- Implements unbiased pass@k estimator
- Handles retry accounting and timeout tracking
- Produces structured `EvaluationResult` with per-task and aggregate scores

#### [NEW] `engine/evaluation/__init__.py`
- Module initialization

#### [NEW] `engine/evaluation/export.py`
- Export `EvaluationResult` to JSONL, CSV, and summary markdown
- Include run manifests, per-task breakdowns, and aggregate statistics

### 2.2 — Model Adapter System

#### [NEW] `engine/adapters/__init__.py`
#### [NEW] `engine/adapters/base.py`
- Abstract `ModelAdapter` interface:
  ```python
  class ModelAdapter(ABC):
      name: str
      provider: str
      def generate(prompt, context) -> GenerationResult
      def get_capabilities() -> AdapterCapabilities
  ```

#### [NEW] `engine/adapters/openai_compat.py`
- OpenAI-compatible endpoint adapter (covers OpenAI, Groq, local vLLM, etc.)

#### [NEW] `engine/adapters/gemini.py`
- Google Gemini adapter using the Gemini SDK

#### [NEW] `engine/adapters/registry.py`
- Adapter discovery and registration
- Track: model name, provider, request count, duration, token/cost estimates, error categories

#### [MODIFY] [model_client.py](file:///g:/projects/sandbench/engine/sandbox/model_client.py)
- Refactor to use the new adapter system as a backend
- Maintain backward compatibility during transition

#### [MODIFY] [worker.py](file:///g:/projects/sandbench/engine/worker.py)
- Wire adapter system into the job processing pipeline
- Add per-task timeout/resource overrides while retaining safe global ceilings

### 2.3 — Frontend: Evaluation Dashboard

#### [MODIFY] Frontend dashboard pages
- Add evaluation run submission UI (select suite, model, k value)
- Display pass@k results with per-task breakdowns
- Add JSONL/CSV download buttons for results

### 2.4 — CI Pipeline

#### [NEW] `.github/workflows/ci.yml`
- Python unit tests (`pytest`)
- Frontend lint/type checks (`eslint`, `tsc`)
- Task registry validation
- Run on every PR and push to main

### Deliverables
- [ ] pass@k evaluation engine with export
- [ ] Typed model adapter system (OpenAI-compat + Gemini)
- [ ] Per-task resource overrides
- [ ] Evaluation dashboard in frontend
- [ ] CI pipeline running on GitHub Actions

---

## Phase 3: Safety Evaluation Suite 🛡️

> **Goal**: Package all security capabilities into a first-class safety benchmark suite.

### 3.1 — Safety Task Suite

#### [NEW] `engine/scoring/tasks/safety/` (new suite directory)
Create safety-specific benchmark tasks:

| Task | Category | What It Tests |
|---|---|---|
| `ssrf-exfil-attempt` | Exfiltration | Code attempts outbound requests to steal data |
| `secret-in-output` | Data Leakage | Code tries to read/print env vars or secrets |
| `filesystem-escape` | Sandbox Escape | Code attempts to write outside /work |
| `fork-bomb-detect` | Resource Abuse | Code tries to exhaust processes |
| `prompt-injection-basic` | Prompt Injection | Model manipulated to ignore safety instructions |
| `prompt-injection-indirect` | Prompt Injection | Indirect injection via task data |
| `code-interpreter-abuse` | Interpreter Misuse | Generated code tries to abuse code execution |
| `obfuscated-payload` | Evasion | Code uses encoding/obfuscation to hide malice |
| `dependency-confusion` | Supply Chain | Code tries to import malicious packages |
| `insecure-code-gen` | Code Quality | Model generates code with known CWE vulnerabilities |

#### [NEW] `engine/safety/__init__.py`
#### [NEW] `engine/safety/suite.py`
- `SafetySuite` class that orchestrates safety task evaluation
- Distinct scoring: binary pass/fail + severity rating
- Aggregate safety score per model

#### [NEW] `engine/safety/monitors.py`
- Enhanced runtime monitoring beyond static gates:
  - Syscall tracing (via seccomp audit log)
  - Network attempt detection
  - Filesystem access auditing
  - Process tree monitoring

### 3.2 — Dynamic Analysis Integration

#### [MODIFY] [static_gate.py](file:///g:/projects/sandbench/engine/sandbox/static_gate.py)
- Add CWE classification to static analysis findings
- Add severity levels (critical, high, medium, low, info)

#### [MODIFY] [monitor.py](file:///g:/projects/sandbench/engine/sandbox/monitor.py)
- Add monitorability traces: structured logs of what the sandbox agent attempted
- Store traces as part of run manifest

#### [MODIFY] [runner.py](file:///g:/projects/sandbench/engine/sandbox/runner.py)
- Integrate enhanced monitoring into sandbox execution
- Add seccomp audit profile for safety tasks

### 3.3 — Safety Dashboard

#### [NEW] Frontend safety evaluation pages
- Safety benchmark submission UI
- Per-model safety scorecard with radar chart visualization
- Task-level pass/fail with evidence details
- Safety comparison across models

### Deliverables
- [ ] 10 safety benchmark tasks across 6 categories
- [ ] Safety suite orchestrator with distinct scoring
- [ ] Enhanced runtime monitoring (syscall, network, filesystem)
- [ ] CWE classification in static analysis
- [ ] Safety dashboard in frontend
- [ ] Monitorability traces stored with every run

---

## Phase 4: Leaderboard, Artifacts & Frontend Premium Upgrade 🏆

> **Goal**: Make the leaderboard production-grade and the frontend world-class.

### 4.1 — Versioned Leaderboard

#### [MODIFY] Leaderboard API routes under [api/leaderboard/](file:///g:/projects/sandbench/frontend/app/api/leaderboard)
- Version entries by suite ID + task version
- Store peak score per user/task/suite AND full attempt history separately
- Add immutable submission records (hash-chain for integrity)
- Add suite-level aggregate rankings

#### [MODIFY] Redis data model
- New key patterns:
  ```
  sandbench:lb:{suite}:{version}:scores → sorted set
  sandbench:lb:{suite}:{version}:history:{user} → list of attempts
  sandbench:submission:{hash} → immutable submission record
  ```

### 4.2 — Replayable Artifact Bundles

#### [NEW] `engine/artifacts/__init__.py`
#### [NEW] `engine/artifacts/bundler.py`
- After every run, produce a sealed artifact bundle:
  ```
  bundle/
  ├── manifest.json        # Full run manifest
  ├── submitted_code/      # Sanitized user submission
  ├── stdout.txt           # Truncated stdout
  ├── stderr.txt           # Truncated stderr
  ├── score_breakdown.json # Per-test pass/fail
  ├── flags.json           # Security flags raised
  └── repair_patch.diff    # If repair was attempted
  ```
- Hash the bundle and store the hash in the manifest for integrity verification
- Upload bundles to object storage (S3-compatible / R2)

#### [NEW] `engine/artifacts/storage.py`
- Abstract storage backend (local filesystem for dev, S3/R2 for prod)
- Signed URL generation for artifact downloads

### 4.3 — Benchmark-Readiness Gates

#### [MODIFY] [registry.py](file:///g:/projects/sandbench/engine/scoring/registry.py)
- Enforce: tasks marked `benchmark_ready: true` MUST have:
  - ✅ Hidden tests present and passing against reference solution
  - ✅ Reference solution file with hash
  - ✅ Complete metadata (all schema fields populated)
  - ✅ Safety review flag
  - ✅ Deterministic scoring verification
- Add CLI command: `python -m scoring.registry validate --strict`

### 4.4 — Frontend Premium Redesign

#### [MODIFY] Frontend components and pages
- **Dashboard**: Real-time metrics cards (total runs, active models, suite stats) with animated counters
- **Leaderboard**: Suite/version selector, expandable rows with score history sparklines, avatar integration
- **Task Browser**: Card grid with difficulty badges, capability tags, filter/sort controls
- **Run Detail**: Timeline visualization, artifact download, score breakdown accordion, repair diff viewer
- **Safety Scorecard**: Radar chart per model, comparison mode, evidence drill-down
- Dark mode glassmorphism design system
- Micro-animations on interactions (hover, submit, score reveal)
- Responsive mobile layout

### Deliverables
- [ ] Versioned leaderboard with immutable submissions
- [ ] Replayable artifact bundles with integrity hashing
- [ ] Benchmark-readiness enforcement
- [ ] Premium frontend redesign with dark mode
- [ ] Object storage integration for artifacts
- [ ] Advanced filtering (suite, capability, difficulty, safety flags)

---

## Phase 5: Scale, Ecosystem & Public Launch 🌍

> **Goal**: Scale to production, add ecosystem tools, and launch publicly.

### 5.1 — Repository-Level Tasks

#### [NEW] `engine/scoring/tasks/repo-repair/` (new category)
- Repository-level repair tasks with multi-file fixture projects
- Tasks inspired by SWE-bench: real-world bug fixes across multiple files
- Each task bundles: repo fixture, failing tests, reference patch, metadata
- Support for git-based evaluation (apply patch → run tests)

### 5.2 — CLI Harness

#### [NEW] `cli/` (new top-level directory)
- `sandbench` CLI tool for local evaluation:
  ```bash
  sandbench run --suite core-v1 --model openai:gpt-4o --k 5
  sandbench validate-tasks --strict
  sandbench export --format jsonl --output results.jsonl
  sandbench safety-eval --model gemini:2.5-pro
  ```
- Docker-based execution (same sandbox as server)
- Local-first: no server required for basic evaluation
- Results upload to leaderboard (optional, authenticated)

### 5.3 — Contamination Policy & Data Governance

#### [NEW] `docs/contamination-policy.md`
- Task source tracking (where each task originated)
- Release date and public/hidden split documentation
- Canary markers embedded in private benchmark data
- Data governance rules for task contributions

#### [MODIFY] Task metadata
- Add fields: `source_url`, `release_date`, `visibility` (public/hidden), `canary_hash`

### 5.4 — Public API

#### [NEW] Frontend API routes for external consumers
- `POST /api/v1/evaluate` — Submit an evaluation job programmatically
- `GET /api/v1/suites` — List available task suites
- `GET /api/v1/results/{run_id}` — Fetch run results and artifacts
- `GET /api/v1/leaderboard/{suite}` — Query leaderboard
- API key authentication and rate limiting
- OpenAPI/Swagger documentation

### 5.5 — Documentation Site

#### [NEW] `docs/` expanded
- Getting started guide
- Task authoring guide (how to contribute tasks)
- Model adapter integration guide
- Safety evaluation methodology
- API reference
- Architecture deep-dive

### 5.6 — Core v1.0 Suite Freeze

- Freeze a `core-v1.0` suite with:
  - ≥ 25 benchmark-ready tasks across all capability categories
  - ≥ 10 safety benchmark tasks
  - Complete documentation
  - Reproducible evaluation commands
  - Baseline results for ≥ 3 model endpoints
- Publish results and methodology

### Deliverables
- [ ] Repository-level repair tasks
- [ ] `sandbench` CLI harness
- [ ] Contamination policy and data governance
- [ ] Public REST API with OpenAPI docs
- [ ] Comprehensive documentation site
- [ ] `core-v1.0` suite frozen with baseline results

---

## Phase Execution Summary

| Phase | Focus | Key Outcome | Est. Duration |
|---|---|---|---|
| **Phase 1** | Benchmark Contract & Tasks | Strict schema, 10+ tasks, run manifests | 1-2 weeks |
| **Phase 2** | Execution Harness & Adapters | pass@k, model adapters, CI | 2 weeks |
| **Phase 3** | Safety Evaluation Suite | 10 safety tasks, monitoring, safety dashboard | 2 weeks |
| **Phase 4** | Leaderboard & Premium Frontend | Versioned leaderboard, artifacts, redesign | 2-3 weeks |
| **Phase 5** | Scale & Public Launch | CLI, public API, repo tasks, core-v1.0 | 3-4 weeks |

---

## User Review Required

> [!IMPORTANT]
> **Phase granularity**: Each phase is designed to be independently deployable. We will execute them one-by-one. Does this breakdown feel right, or would you like to merge/split any phases?

> [!IMPORTANT]
> **Database migration**: Phase 4 introduces significant Redis schema changes. Should we plan a migration to PostgreSQL/Supabase at this point, or continue with Redis + new key patterns?

> [!IMPORTANT]
> **Task content priority**: For Phase 1, the proposed 7 new tasks focus on Python backend work. Would you prefer to include JavaScript/TypeScript tasks as well, or keep Phase 1 Python-only?

## Open Questions

1. **Object storage for artifacts (Phase 4)**: Do you have a preference? Options: Cloudflare R2 (S3-compatible, free egress), AWS S3, or Vercel Blob Storage.
2. **CLI distribution (Phase 5)**: Should the CLI be a pip-installable package, a standalone binary (via PyInstaller), or both?
3. **Public API rate limits (Phase 5)**: What tier structure are you thinking? Free / Pro / Enterprise?
4. **Hosting the worker**: Are you staying on Hetzner + Coolify, or considering a move to a different infra setup as we scale?
