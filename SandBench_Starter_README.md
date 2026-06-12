# SandBench — Starter Kit (Spine Slice)

Goal of this kit: prove the vertical slice end-to-end.
**Submit code (Next.js) → job in Upstash → Python worker runs it in a hardened
throwaway container → result back in the UI.**

Once this is green, everything else in the build guide bolts onto it.

```
sandbench/
├── engine/                 # Python service
│   ├── sandbox/runner.py   # hardened docker runner (always destroys container)
│   ├── worker.py           # BRPOPs jobs from Upstash, runs them, writes result
│   └── app/main.py         # optional /health endpoint
└── frontend/               # Next.js + TypeScript
    ├── app/page.tsx        # submit form + live polling
    ├── app/api/submit      # LPUSH job to Upstash
    ├── app/api/runs/[id]   # read status + result
    └── lib/redis.ts        # Upstash REST client
```

## 0. Prerequisites
- Docker daemon running (`docker run hello-world` must work)
- Python 3.11+, Node 18+
- An Upstash Redis database (free tier). You need BOTH connection methods:
  - REST URL + token  → for Next.js  (`.env.local`)
  - Standard rediss:// → for the worker (`engine/.env`)

## 1. Engine (terminal A)
```bash
cd engine
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # paste your rediss:// URL
docker pull python:3.11-slim  # pre-pull so first run isn't slow
python worker.py              # -> "worker up, waiting for jobs..."
```

## 2. Frontend (terminal B)
```bash
cd frontend
npm install
cp .env.local.example .env.local   # paste your Upstash REST url + token
npm run dev                        # -> http://localhost:3000
```

## 3. Prove the spine
Open http://localhost:3000, click **Run**. You should see:
status `queued → running → done`, verdict `clean`, and `hello from the sandbox`.

Then try malicious/broken inputs to watch the verdict change:
- `while True: pass`            → times out, verdict `broken`
- `import os; os.system("ls")`  → runs (network is off; next session we flag/quarantine this)
- `1/0`                          → non-zero exit, verdict `broken`

## What's NOT here yet (next sessions, in order)
1. Real malicious-vs-messy verdict: monitor + bandit/semgrep/yara  (the §7 branch)
2. Analysis engine: linters + LLM review + patch diff
3. File/repo + API + model submission types
4. Benchmark tasks + scoring + leaderboard
5. RL env wrapper + the Colab training loop
