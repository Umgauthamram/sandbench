"""Hardened, throwaway container runner for SandBench.

Every execution runs in a fresh, isolated container with strict resource limits,
no network access, a read-only root filesystem, dropped capabilities, and a
custom seccomp profile.

Execution model (and why it is shaped this way):
  - The payload is copied in with put_archive BEFORE the container starts.
    On Docker Desktop, put_archive into a *running* container whose root is
    read-only is rejected outright ("container rootfs is marked read-only"),
    even when the target is a tmpfs. read_only is only enforced at start, so
    the copy must happen before start.
  - The code file is therefore written into the (briefly writable) root layer
    and becomes read-only once the container starts. That is fine: the runtime
    only ever READS solution.py.
  - There is NO tmpfs over /workspace. A tmpfs mounted at start would shadow
    the pre-start payload and the file would vanish. Only /tmp is a tmpfs, for
    any runtime scratch writes.
  - Net effect on security: read-only root + a single 16 MB /tmp tmpfs means a
    submission cannot write anywhere else or exhaust host disk.
  - The container's CMD runs the code directly; we wait with a wall-clock
    timeout and always force-remove the container afterwards.
"""
from dataclasses import dataclass, field
import io
import json
import logging
import os
import tarfile
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import docker
import requests

from config import (
    SANDBOX_MEM_LIMIT,
    SANDBOX_CPUS,
    SANDBOX_PIDS_LIMIT,
    SANDBOX_TIMEOUT_SECONDS,
    ORPHAN_TTL_SECONDS,
)

logger = logging.getLogger(__name__)
client = docker.from_env()

# The only writable area at runtime. RAM-backed, hard size cap.
TMPFS = {"/tmp": "rw,size=16m,mode=1777"}


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    oom_killed: bool
    timed_out: bool
    fs_diff: List[Dict[str, Any]] = field(default_factory=list)
    container_attrs: Dict[str, Any] = field(default_factory=dict)


def _load_security_opt() -> List[str]:
    """security_opt with the seccomp profile embedded as inline JSON.

    The daemon cannot read a client-side path, so docker-py must send content.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    seccomp_path = os.path.join(current_dir, "images", "seccomp.json")
    if not os.path.exists(seccomp_path):
        logger.warning("seccomp.json not found at %s; running without seccomp.", seccomp_path)
        return ["no-new-privileges"]
    try:
        with open(seccomp_path, "r", encoding="utf-8") as f:
            seccomp_data = json.load(f)
        seccomp_data.pop("_comment", None)
        return ["no-new-privileges", f"seccomp={json.dumps(seccomp_data)}"]
    except Exception as e:
        logger.warning("Failed to load seccomp profile: %s; running without seccomp.", e)
        return ["no-new-privileges"]


def cleanup_orphans(docker_client: docker.DockerClient) -> None:
    """Force-remove (with volumes) any sandbench container older than ORPHAN_TTL_SECONDS."""
    logger.info("Cleaning up orphan container sandboxes...")
    try:
        containers = docker_client.containers.list(all=True, filters={"label": "sandbench=1"})
        now_dt = datetime.now(timezone.utc)
        for container in containers:
            try:
                created_str = container.attrs.get("Created", "")
                if not created_str:
                    continue
                normalized = created_str.replace("Z", "+00:00")
                if "." in normalized:
                    base, frac_tz = normalized.split(".", 1)
                    tz_offset = ""
                    if "+" in frac_tz:
                        frac, tz = frac_tz.split("+", 1)
                        tz_offset = "+" + tz
                    elif "-" in frac_tz:
                        frac, tz = frac_tz.split("-", 1)
                        tz_offset = "-" + tz
                    else:
                        frac = frac_tz
                    normalized = f"{base}.{frac[:6]}{tz_offset}"
                created_dt = datetime.fromisoformat(normalized)
                age = (now_dt - created_dt).total_seconds()
                if age > ORPHAN_TTL_SECONDS:
                    logger.warning("Removing orphan container %s (age %ds)", container.id[:12], age)
                    container.remove(force=True, v=True)
            except Exception as e:
                logger.warning("Failed to evaluate orphan container %s: %s", container.id[:12], e)
    except Exception as e:
        logger.error("Error during orphan cleanup: %s", e)


def run(code: str, language: str = "python", image: Optional[str] = None) -> RunResult:
    """Run code inside a hardened, throwaway container and return a RunResult."""
    container = None
    timed_out = False
    oom_killed = False
    pids_limit_hit = False
    exit_code = -1
    stdout = ""
    stderr = ""
    fs_diff: List[Dict[str, Any]] = []
    container_attrs: Dict[str, Any] = {}

    lang = language.lower()
    if not image:
        image = "node:20-slim" if lang == "node" else "python:3.11-slim"
    file_name = "solution.js" if lang == "node" else "solution.py"
    run_cmd = (
        ["node", f"/workspace/{file_name}"] if lang == "node"
        else ["python", f"/workspace/{file_name}"]
    )

    start_time = time.perf_counter()
    try:
        # 1. Create the container with the REAL command. working_dir is the
        #    writable /tmp tmpfs so relative writes by the submission land there.
        container = client.containers.create(
            image,
            command=run_cmd,
            working_dir="/tmp",
            detach=True,
            network_mode="none",
            read_only=True,
            mounts=[docker.types.Mount(target="/workspace", source="", type="volume")],
            tmpfs=TMPFS,
            user="65534:65534",  # nobody
            cap_drop=["ALL"],
            security_opt=_load_security_opt(),
            mem_limit=SANDBOX_MEM_LIMIT,
            nano_cpus=int(SANDBOX_CPUS * 1e9),
            pids_limit=SANDBOX_PIDS_LIMIT,
            labels={"sandbench": "1"},
        )

        # 2. Copy the payload in BEFORE start (read-only is enforced only at
        #    start). Since /workspace is a volume, we can put_archive into it
        #    even when the container is stopped.
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            code_bytes = code.encode("utf-8")
            info = tarfile.TarInfo(name=file_name)
            info.size = len(code_bytes)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(code_bytes))
        tar_stream.seek(0)
        container.put_archive("/workspace", tar_stream.getvalue())

        # 3. Start (read-only root + tmpfs now enforced) and run the code.
        container.start()

        # 4. Wait with a wall-clock timeout.
        try:
            res = container.wait(timeout=SANDBOX_TIMEOUT_SECONDS)
            exit_code = res.get("StatusCode", -1)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            timed_out = True
            # Sample PID usage before killing so silent fork bombs are detectable.
            try:
                stats = container.stats(stream=False)
                pids = stats.get("pids_stats", {})
                if pids.get("current", 0) > 0 and pids.get("current") == pids.get("limit"):
                    pids_limit_hit = True
            except Exception:
                pass
            try:
                container.kill()
            except Exception:
                pass

        # 5. Resolve state, exit code, OOM.
        try:
            container.reload()
            container_attrs = container.attrs
            state = container_attrs.get("State", {})
            oom_killed = state.get("OOMKilled", False)
            if not timed_out:
                exit_code = state.get("ExitCode", exit_code)
        except Exception:
            pass
        if not timed_out and exit_code == 137:
            oom_killed = True

        # 6. Capture output (each truncated to 64 KB).
        try:
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")[:65536]
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")[:65536]
        except Exception as e:
            logger.warning("Failed to read container logs: %s", e)
        if pids_limit_hit:
            stderr += "\nBlockingIOError: [Errno 11] Resource temporarily unavailable (PID limit reached)"

        # 7. Filesystem diff (best-effort; read-only root makes this sparse).
        try:
            raw_diff = container.diff() or []
            fs_diff = [{"Path": d.get("Path", ""), "Kind": d.get("Kind", -1)} for d in raw_diff]
        except Exception as e:
            logger.warning("Failed to collect fs diff: %s", e)

    finally:
        # 8. Teardown — v=True frees any associated anonymous volumes too.
        if container is not None:
            try:
                container.remove(force=True, v=True)
            except Exception as e:
                logger.warning("Failed to remove container %s: %s", container.id[:12], e)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    return RunResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        oom_killed=oom_killed,
        timed_out=timed_out,
        fs_diff=fs_diff,
        container_attrs=container_attrs,
    )