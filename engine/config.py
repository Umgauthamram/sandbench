"""Configuration module for SandBench engine.

All environment variable reads must be centralized here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
# Fallback to the .env file in the engine directory itself
engine_env = Path(__file__).resolve().parent / ".env"
if engine_env.exists():
    load_dotenv(dotenv_path=engine_env)

# Redis Configuration
UPSTASH_REDIS_URL = os.environ.get("UPSTASH_REDIS_URL", "redis://localhost:6379")

# Sandbox Configuration
SANDBOX_MEM_LIMIT = os.environ.get("SANDBOX_MEM_LIMIT", "256m")
SANDBOX_CPUS = float(os.environ.get("SANDBOX_CPUS", "0.5"))
SANDBOX_PIDS_LIMIT = int(os.environ.get("SANDBOX_PIDS_LIMIT", "64"))
SANDBOX_TIMEOUT_SECONDS = int(os.environ.get("SANDBOX_TIMEOUT_SECONDS", "20"))

# Isolation runtime for the sandbox container.
#   "auto"  - use gVisor (runsc) when the daemon has it, else fall back to runc
#   "runsc" - require gVisor; also accepts any runtime name the daemon exposes
#   "runc"  - force the default shared-kernel runtime
SANDBOX_RUNTIME = os.environ.get("SANDBOX_RUNTIME", "auto").strip().lower()

# When true, a run is refused outright rather than executed on shared-kernel
# runc. Set this on any host that evaluates genuinely untrusted code.
SANDBOX_REQUIRE_HARDENED = os.environ.get(
    "SANDBOX_REQUIRE_HARDENED", "0"
).strip().lower() in ("1", "true", "yes", "on")
ORPHAN_TTL_SECONDS = int(os.environ.get("ORPHAN_TTL_SECONDS", "300"))
MAX_PAYLOAD_BYTES = int(os.environ.get("MAX_PAYLOAD_BYTES", "262144"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# LLM Configuration for Analysis Engine
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_ENDPOINT_URL = os.environ.get("MODEL_ENDPOINT_URL", "")
TRACE_LOG_PATH = os.environ.get("TRACE_LOG_PATH", "traces.jsonl")
ARTIFACT_STORAGE_DIR = os.environ.get("ARTIFACT_STORAGE_DIR", "run-artifacts")
ARTIFACT_SIGNING_SECRET = os.environ.get("ARTIFACT_SIGNING_SECRET", "sandbench-local-artifacts")

# Archive Validation Limits
MAX_UNCOMPRESSED = int(os.environ.get("MAX_UNCOMPRESSED", 5 * 1024 * 1024))
MAX_FILES = int(os.environ.get("MAX_FILES", 200))
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 1 * 1024 * 1024))
MAX_DEPTH = int(os.environ.get("MAX_DEPTH", 12))
RATIO_LIMIT = float(os.environ.get("RATIO_LIMIT", 100.0))
