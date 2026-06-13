# SandBench — Work Package 1: Build Prompt + Verification Checklist

This file has three parts:

1. **PART A** — the exact prompt to paste into Gemini (copy the whole fenced block)
2. **PART B** — your verification checklist after Gemini delivers
3. **PART C** — environment variables, next work packages, and fine-tuning prep notes

---

## PART A — Prompt for Gemini (copy everything inside the block)

```
You are implementing Work Package 1 (the Verdict Engine) for SandBench, an
existing project. Follow this specification EXACTLY. Do not invent new
dependencies, do not rename fields, do not change the JSON contract, and do
not restructure existing folders. If something in the spec is impossible or
ambiguous, STOP and ask one clarifying question instead of guessing.

## PROJECT CONTEXT

SandBench runs untrusted user code inside hardened, throwaway Docker
containers and returns a verdict. Current repo layout (relevant parts):

engine/
  app/                  # optional FastAPI health endpoint
  sandbox/
    runner.py           # spawns container, runs code, tears down (EXISTS — modify)
    images/             # python.Dockerfile, node.Dockerfile, seccomp.json (EXIST)
  worker.py             # BRPOP jobs from Redis (Upstash rediss://), runs pipeline (EXISTS — modify)
  requirements.txt
frontend/               # Next.js — DO NOT TOUCH in this work package

Current behavior: worker pops a job {run_id, code, task_id} from Redis list
"sandbench:jobs", runs it in a container, writes result JSON to key
"sandbench:run:{run_id}". Verdict today is naive (exit code / timeout only).

## YOUR TASK

Build a multi-signal verdict engine. Every verdict must be explainable via
structured flags. Architecture: a STATIC GATE that runs before any container
is created, and a MONITOR that collects signals during/after execution.

### File 1 (NEW): engine/sandbox/rules.py

Single source of truth for all rules. Exactly this structure:

    from dataclasses import dataclass
    from enum import Enum

    class Severity(str, Enum):
        HIGH = "HIGH"      # any HIGH flag => verdict MALICIOUS
        MEDIUM = "MEDIUM"  # recorded, does not flip verdict
        LOW = "LOW"

    @dataclass
    class Flag:
        rule_id: str
        severity: Severity
        source: str        # "static" | "monitor"
        evidence: str      # the actual matched string / path / address
        location: str = "" # file:line where applicable

    RULES = {
      "NET_EGRESS_ATTEMPT": ("monitor", Severity.HIGH,   "Attempted outbound network connection"),
      "FS_WRITE_OUTSIDE":   ("monitor", Severity.HIGH,   "Wrote files outside /workspace"),
      "FORK_BOMB":          ("monitor", Severity.HIGH,   "PID limit exhausted (fork bomb pattern)"),
      "OOM_KILL":           ("monitor", Severity.MEDIUM, "Container killed by OOM"),
      "YARA_MATCH":         ("static",  Severity.HIGH,   "Matched malware signature"),
      "BANDIT_HIGH":        ("static",  Severity.HIGH,   "Bandit high-severity issue"),
      "BANDIT_MEDIUM":      ("static",  Severity.MEDIUM, "Bandit medium-severity issue"),
      "SEMGREP_SECURITY":   ("static",  Severity.HIGH,   "Semgrep security rule hit"),
      "OBFUSCATION":        ("static",  Severity.MEDIUM, "Obfuscated code (exec/eval on encoded data)"),
      "TIMEOUT":            ("monitor", Severity.LOW,    "Wall-clock timeout exceeded"),
    }

    def make_flag(rule_id: str, evidence: str, location: str = "") -> Flag:
        source, severity, _ = RULES[rule_id]
        return Flag(rule_id=rule_id, severity=severity, source=source,
                    evidence=evidence[:500], location=location)

### File 2 (NEW): engine/sandbox/static_gate.py

Runs BEFORE any container is created. Public API:

    def scan(code: str, language: str, workdir: str) -> list[Flag]

Implementation requirements:
- Write the code to a temp file inside workdir, then run:
  a) bandit: subprocess `bandit -f json -q <file>` (python only).
     Map issue_severity HIGH -> BANDIT_HIGH flag, MEDIUM -> BANDIT_MEDIUM.
     evidence = issue_text, location = "<filename>:<line_number>".
  b) semgrep: subprocess `semgrep --config p/security-audit --json --quiet <file>`.
     Every finding with severity ERROR -> SEMGREP_SECURITY flag.
     If semgrep binary is missing or times out (30s), log a warning and skip
     (do NOT crash the pipeline).
  c) YARA via yara-python, with rules compiled from an inline RULES_SOURCE
     string constant containing these starter rules:
       - reverse_shell: strings "/dev/tcp/", "sh -i", "nc -e", "bash -i >&"
       - crypto_miner: strings "stratum+tcp://", "xmrig", "minerd", "cryptonight"
       - b64_exec_combo: BOTH "base64" AND ("exec(" OR "eval(") present
       - env_exfil: BOTH "os.environ" AND ("requests.post" OR "urllib" OR "socket")
     Any match -> YARA_MATCH flag, evidence = rule name + matched strings.
  d) OBFUSCATION heuristic in plain Python (no subprocess): flag if the code
     contains exec( or eval( applied to a decode/decompress call
     (base64/zlib/codecs/marshal), or hex/unicode-escape blobs longer than
     200 chars. evidence = the matched snippet (truncated to 200 chars).
- All subprocess calls: timeout=30, capture_output=True, never raise to caller;
  on tool failure return what you have and log.
- Return the combined list[Flag]. Deduplicate identical (rule_id, location) pairs.

### File 3 (NEW): engine/sandbox/monitor.py

Runs on the result of a container execution. Public API:

    def collect(container_attrs: dict, fs_diff: list[dict],
                stdout: str, stderr: str, timed_out: bool) -> list[Flag]

Implementation requirements:
- NETWORK: the container runs with network_mode="none", so any socket attempt
  fails loudly. Scan stderr+stdout for these patterns (regex, case-insensitive):
    "Network is unreachable", "Temporary failure in name resolution",
    "Connection refused", "getaddrinfo", "ENOTFOUND", "ECONNREFUSED",
    "EAI_AGAIN", "socket.gaierror"
  On match -> NET_EGRESS_ATTEMPT. evidence = the full matching line (it often
  contains the target host/port). One flag per distinct matching line, max 5.
- FILESYSTEM: fs_diff is the output of container.diff() — a list of
  {"Path": str, "Kind": int} where Kind 0=modified,1=added,2=deleted.
  Allowed prefixes: "/workspace", "/tmp". Anything added/modified outside
  those prefixes -> FS_WRITE_OUTSIDE, evidence = the path. Ignore deletions.
  Ignore known-noise paths: "/root/.cache", "/home" (list them in one
  IGNORED_PREFIXES constant so it is tunable).
- RESOURCES: from container_attrs["State"]: if OOMKilled is true -> OOM_KILL.
  Scan stderr for "Resource temporarily unavailable", "BlockingIOError",
  "fork: retry", "cannot allocate memory" -> FORK_BOMB.
- TIMEOUT: if timed_out -> TIMEOUT flag, evidence = "wall clock limit".
- Return list[Flag].

### File 4 (MODIFY): engine/sandbox/runner.py

Keep the existing hardened run, ensure ALL of the following flags are set on
container creation (docker SDK):
    network_mode="none"
    read_only=True
    tmpfs={"/workspace": "rw,size=64m", "/tmp": "rw,size=16m"}
    user="65534:65534"            # nobody
    cap_drop=["ALL"]
    security_opt=["no-new-privileges", "seccomp=<path to images/seccomp.json>"]
    mem_limit=ENV SANDBOX_MEM_LIMIT (default "256m")
    nano_cpus=int(float(ENV SANDBOX_CPUS default "0.5") * 1e9)
    pids_limit=int(ENV SANDBOX_PIDS_LIMIT default "64")
    labels={"sandbench": "1"}
Code is injected by writing it into the tmpfs workdir via
container.put_archive (tar in memory) — NEVER bind-mount host paths.
Hard wall-clock timeout from ENV SANDBOX_TIMEOUT_SECONDS (default 20):
implement with container.wait(timeout=...) wrapped so that on expiry you
container.kill() and mark timed_out=True.

Return a RunResult dataclass:
    exit_code: int, stdout: str, stderr: str, duration_ms: int,
    oom_killed: bool, timed_out: bool, fs_diff: list[dict],
    container_attrs: dict
stdout/stderr each truncated to 64 KB.
Capture fs_diff via container.diff() BEFORE removal.
Teardown: container.remove(force=True) in a finally block — must run on every
code path including exceptions.
Add cleanup_orphans(client): force-remove every container with label
sandbench=1 created more than ORPHAN_TTL_SECONDS (default 300) ago.

### File 5 (MODIFY): engine/worker.py

Pipeline per job (pseudocode — implement exactly this control flow):

    flags = static_gate.scan(code, language, tmpdir)
    if any(f.severity == HIGH for f in flags):
        result = quarantined(run_id, flags)          # container NEVER created
    else:
        run = runner.run(code, language)             # hardened container
        flags += monitor.collect(run.container_attrs, run.fs_diff,
                                 run.stdout, run.stderr, run.timed_out)
        if any(f.severity == HIGH for f in flags):
            verdict, status, score = "malicious", "quarantined", 0
        elif run.exit_code != 0 or run.timed_out:
            verdict, status, score = "broken", "done", None   # scorer fills later
        else:
            verdict, status, score = "clean", "done", None
    write result JSON to "sandbench:run:{run_id}"

Call runner.cleanup_orphans(client) once at worker startup.
Wrap the entire job handling in try/except: on unexpected exception write
status="error" with the exception string in stderr — a job must NEVER leave
a run stuck without a terminal status.

### RESULT JSON CONTRACT (do not deviate, the frontend depends on it)

    {
      "run_id": "...",
      "status": "done" | "quarantined" | "error",
      "verdict": "clean" | "broken" | "malicious" | null,
      "score": 0 | null,
      "flags": [
        {"rule_id": "...", "severity": "HIGH|MEDIUM|LOW", "source": "static|monitor",
         "evidence": "...", "location": "file:line or empty string"}
      ],
      "stdout": "...", "stderr": "...",
      "duration_ms": 0, "exit_code": 0,
      "finished_at": "<ISO 8601 UTC>"
    }

### DEPENDENCIES

Add to engine/requirements.txt: bandit, semgrep, yara-python.
Use ONLY these plus what is already in the file (docker, redis, python-dotenv,
fastapi/uvicorn if present). No other new packages.

### ACCEPTANCE TESTS

Create engine/tests/test_verdict.py with these five integration tests
(mark them with pytest -m integration; they need the Docker daemon):

1. print-based FizzBuzz            -> verdict "clean", flags == []
2. "1/0"                           -> verdict "broken", no HIGH flags
3. socket.create_connection(("1.2.3.4", 4444), timeout=3)
                                   -> verdict "malicious", NET_EGRESS_ATTEMPT present
4. import base64; exec(base64.b64decode("cHJpbnQoMSk="))
                                   -> verdict "malicious" from the STATIC GATE,
                                      and assert no container was created
                                      (assert via docker client: no container
                                      with label sandbench=1 ran for this test)
5. os.fork() in a while True loop  -> verdict "malicious", FORK_BOMB present,
                                      and the container no longer exists after

### QUALITY BAR

- Type hints on every public function. Docstrings on every module.
- No print() — use the logging module, logger per module.
- Every env variable read in ONE config module (engine/config.py) with the
  defaults stated above; nothing reads os.environ elsewhere.
- Deliver complete files, not fragments. List every file you created or
  modified at the end with a one-line summary each.
```

---

## PART B — Your verification checklist (run after Gemini delivers)

Paste the delivered files back to Claude for review, and check these yourself:

**Security non-negotiables (read the code, line by line):**
- [ ] `network_mode="none"` actually present in container creation
- [ ] No `volumes=` / no bind mounts anywhere — code goes in via `put_archive`
- [ ] `user="65534:65534"`, `cap_drop=["ALL"]`, `no-new-privileges`, seccomp path correct
- [ ] `mem_limit`, `nano_cpus`, `pids_limit` all set from config
- [ ] `container.remove(force=True)` inside `finally` — trace every exception path
- [ ] Static gate HIGH flag → container is **never created** (this is test 4)
- [ ] `cleanup_orphans` exists and is called at worker startup

**Pipeline correctness:**
- [ ] All 5 acceptance tests pass: `pytest -m integration engine/tests/`
- [ ] Result JSON matches the contract exactly (paste one real result and diff it)
- [ ] A crashed worker job still writes `status: "error"` (kill the tool mid-run to test)
- [ ] stdout/stderr truncated (submit code that prints 10 MB; result stays small)
- [ ] semgrep missing/broken → pipeline still completes with a logged warning

**Manual smoke tests through the UI:**
- [ ] Submit clean FizzBuzz → Clean badge, score
- [ ] Submit the socket sample → Malicious badge, flag visible with evidence
- [ ] Submit `1/0` → Broken
- [ ] `docker ps -a` after each: zero leftover sandbench containers

**Common Gemini failure modes to watch for (from experience):**
- Invents a different flags schema or renames `rule_id` → reject, re-prompt with "follow the contract"
- Puts bandit/semgrep INSIDE the container instead of on the host before it
- Uses `container.exec_run` with a host-mounted file instead of `put_archive`
- Catches exceptions around teardown so `finally` never runs the remove
- Writes unit tests with mocked Docker instead of real integration tests

---

## PART C — Next steps, env variables, fine-tuning prep

### Environment variables to add now

**`engine/.env`** (Python worker — Hetzner/Coolify later, local now):

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | — | Upstash `rediss://` connection string |
| `SANDBOX_TIMEOUT_SECONDS` | `20` | Hard wall-clock kill |
| `SANDBOX_MEM_LIMIT` | `256m` | Container memory cap |
| `SANDBOX_CPUS` | `0.5` | CPU quota |
| `SANDBOX_PIDS_LIMIT` | `64` | Fork-bomb defense |
| `ORPHAN_TTL_SECONDS` | `300` | Janitor threshold |
| `MAX_PAYLOAD_BYTES` | `262144` | Reject oversized submissions (256 KB) |
| `LOG_LEVEL` | `INFO` | Logging |
| `ANTHROPIC_API_KEY` | — | Needed in WP3 (analysis engine) — add the slot now |
| `MODEL_ENDPOINT_URL` | — | Your fine-tuned model's URL later (llama.cpp/Ollama on Hetzner) |

**`frontend/.env.local`** (Next.js — Vercel later):

| Variable | Purpose |
|---|---|
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | Queue + result reads |
| `AUTH_SECRET` | Session signing (generate: `openssl rand -base64 32`) |
| `ENCRYPTION_KEY` | AES key for encrypting stored user API keys at rest — never store keys plaintext |
| `NEXT_PUBLIC_APP_URL` | Absolute URL for links/SSE |
| `RATE_LIMIT_RUNS_PER_HOUR` | Abuse defense on /api/submit (start: 30) |

Rule: every variable has a documented default or fails loudly at startup. Both `.env.example` files updated in the same commit.

### Work package order after WP1

| WP | Scope | Definition of done |
|---|---|---|
| **WP2 — Run detail page** | Flags rendered with severity color + evidence + location; diff-style log viewer; verdict explanation panel; polling → SSE | Clicking any run shows WHY it got its verdict |
| **WP3 — Analysis engine** | ruff + LLM review (Claude API) on clean/broken runs; unified-diff patch; suggestions persisted and rendered | Messy code returns concrete suggestions + a patch diff |
| **WP4 — Scoring + tasks-as-data** | Each task = folder with `task.yaml` + tests; scorer runs in a second container; leaderboard reads real scores | Adding a 5th task requires zero code changes |
| **WP5 — Reliability + auth hardening** | Heartbeat + stuck-run reaper, retry-once on infra errors, idempotent job IDs, per-user rate limit, encrypted API keys | Kill the worker mid-run → run ends in `error`, never stuck |
| **WP6 — Deploy** | Frontend → Vercel; engine → Hetzner via Coolify (worker + Docker socket access); Upstash prod DB | Public URL, full demo flow works remotely |
| **WP7 — Trace logging** | Log every repair interaction (see below) | Training data accumulates automatically |

### Fine-tuning prep — do these THREE things now, train LATER

1. **Start logging traces immediately (WP7 is cheap — build it alongside WP3).** Every time the analysis engine reviews code, store one JSON record:

   ```json
   {
     "trace_id": "...", "task_id": "...",
     "broken_code": "...", "error_output": "...",
     "test_results_before": {"passed": 2, "failed": 5},
     "patch": "unified diff", "model_used": "claude-sonnet-4-6",
     "test_results_after": {"passed": 7, "failed": 0},
     "accepted": true, "created_at": "..."
   }
   ```

   The `test_results_after` field is your reward label — it is what makes the dataset trainable. Without it you have prompts, not training data.

2. **Hold out an eval set.** Reserve 50–100 broken-code samples that NEVER go into training. Your fine-tune claim ("beats zero-shot") is only credible against a held-out set.

3. **Decide the target now so traces are formatted for it:** Qwen2.5-Coder-7B-Instruct, LoRA (r=16, alpha=32) via Unsloth on Colab T4/A100, chat-format dataset (`system: repair instructions / user: broken code + error / assistant: patch`). Export merged → quantize GGUF `Q4_K_M` → serve with llama.cpp or Ollama on the Hetzner CPU box via Coolify, behind `MODEL_ENDPOINT_URL`. CPU reality check: 7B Q4 ≈ 3–6 tokens/sec on a typical Hetzner VPS — fine for an async patch-suggestion queue, not for live chat. Design the analysis engine to call the model asynchronously from day one.

   **Trigger to start training:** ≥500 traces where `accepted=true` AND tests improved. At your expected early traffic this is weeks away — exactly the time to finish WP2–WP6.

### Business-model checkpoints to keep in mind while building

- Every run already has a cost (container seconds) — log `duration_ms` per user from day one; it becomes your usage-billing meter.
- Keep the verdict JSON contract stable — it becomes your public API response when you launch the paid API tier.
- The tasks-as-data design (WP4) is what later lets paying customers define **private benchmark tasks** — that is the first thing companies will pay for.
