"""Configuration module for SandBench engine.

All environment variable reads must be centralized here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Redis Configuration
UPSTASH_REDIS_URL = os.environ.get("UPSTASH_REDIS_URL", "redis://localhost:6379")

# Sandbox Configuration
SANDBOX_MEM_LIMIT = os.environ.get("SANDBOX_MEM_LIMIT", "256m")
SANDBOX_CPUS = float(os.environ.get("SANDBOX_CPUS", "0.5"))
SANDBOX_PIDS_LIMIT = int(os.environ.get("SANDBOX_PIDS_LIMIT", "64"))
SANDBOX_TIMEOUT_SECONDS = int(os.environ.get("SANDBOX_TIMEOUT_SECONDS", "20"))
ORPHAN_TTL_SECONDS = int(os.environ.get("ORPHAN_TTL_SECONDS", "300"))
MAX_PAYLOAD_BYTES = int(os.environ.get("MAX_PAYLOAD_BYTES", "262144"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# LLM Configuration for Analysis Engine
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6Lpzx8J_8mE5hI4tqOudTZvjHXUtHphWhewX1Anik5UyA")
MODEL_ENDPOINT_URL = os.environ.get("MODEL_ENDPOINT_URL", "")
TRACE_LOG_PATH = os.environ.get("TRACE_LOG_PATH", "traces.jsonl")
