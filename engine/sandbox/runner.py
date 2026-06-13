"""Hardened, throwaway container runner for SandBench.

Every execution runs in a fresh, isolated container with strict resource limits,
no network access, a read-only root filesystem, dropped capabilities, and a
custom seccomp profile.

Execution model (important):
  1. Create a hardened container whose entrypoint just BLOCKS (`sleep`).
  2. Start it — this is when the tmpfs mounts attach.
  3. put_archive the payload INTO the now-mounted tmpfs (so it is visible).
  4. exec the real command inside the container, streaming output, with a
     wall-clock timeout enforced in a watcher thread.
  5. Always force-remove the container (tmpfs is freed automatically).

This avoids the classic bug where a mount attached at start shadows a payload
written before start, and it keeps the workspace on a size-capped tmpfs so a
submission cannot fill the host disk.
"""
from dataclasses import dataclass, field
import io
import json
import logging
import os
import tarfile
import threading
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import docker

from config import (
    SANDBOX_MEM_LIMIT,
    SANDBOX_CPUS,
    SANDBOX_PIDS_LIMIT,
    SANDBOX_TIMEOUT_SECONDS,
    ORPHAN_TTL_SECONDS,
)

logger = logging.getLogger(__name__)
client = docker.from_env()

# Writable areas inside the otherwise read-only container. Both are RAM-backed
# tmpfs with hard size caps, so a runaway submission cannot exhaust host disk.
WORKSPACE = "/workspace"
TMPFS = {
    "/workspace": "rw,size=64m,mode=1777",
    "/tmp": "rw,size=16m,mode=1777",
}


# WORKSPACE = "/workspace"
# TMPFS = {
#     "/workspace": "rw,size=64m,mode=1777",
#     "/tmp": "rw,size=16m,mode=1777",
# }
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
    """Build the security_opt list, embedding the seccomp profile as inline JSON.

    The Docker daemon cannot read a client-side file path, so docker-py must
    send the profile *content*, not a path.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    seccomp_path = os.path.join(current_dir, "images", "seccomp.json")
    if not os.path.exists(seccomp_path):
        logger.warning("seccomp.json not found at %s; running without seccomp.", seccomp_path)
        return ["no-new-privileges"]
    try:
        with open(seccomp_path, "r", encoding="utf-8") as f:
            seccomp_data = json.load(f)
        seccomp_data.pop("_comment", None)  # comments are not valid in a real profile
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
    exit_code = -1
    fs_diff: List[Dict[str, Any]] = []
    container_attrs: Dict[str, Any] = {}
    out_buf: Dict[str, bytes] = {"stdout": b"", "stderr": b""}

    lang = language.lower()
    if not image:
        image = "node:20-slim" if lang == "node" else "python:3.11-slim"
    file_name = "solution.js" if lang == "node" else "solution.py"
    run_cmd = (
        ["node", f"{WORKSPACE}/solution.js"] if lang == "node"
        else ["python", f"{WORKSPACE}/solution.py"]
    )

    start_time = time.perf_counter()
    try:
        # 1. Create a container that just blocks; the real command runs via exec.
        container = client.containers.create(
            image,
            command=["sleep", str(SANDBOX_TIMEOUT_SECONDS + 10)],
            working_dir=WORKSPACE,
            detach=True,
            network_mode="none",
            read_only=True,
            mounts=[docker.types.Mount(target=WORKSPACE, source="", type="volume")],
            tmpfs=TMPFS,
            user="65534:65534",  # nobody
            cap_drop=["ALL"],
            security_opt=_load_security_opt(),
            mem_limit=SANDBOX_MEM_LIMIT,
            nano_cpus=int(SANDBOX_CPUS * 1e9),
            pids_limit=SANDBOX_PIDS_LIMIT,
            labels={"sandbench": "1"},
        )

        # 2. Start so the tmpfs mounts attach.
        container.start()

        # 3. Inject the payload INTO the mounted tmpfs (now visible at runtime).
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            code_bytes = code.encode("utf-8")
            info = tarfile.TarInfo(name=file_name)
            info.size = len(code_bytes)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(code_bytes))
        tar_stream.seek(0)
        container.put_archive(WORKSPACE, tar_stream.getvalue())

        # 4. Exec the real command, streaming demuxed output, with a watchdog timeout.
        exec_id = client.api.exec_create(
            container.id, cmd=run_cmd, user="65534:65534",
            workdir=WORKSPACE, stdout=True, stderr=True,
        )["Id"]

        def _pump():
            try:
                for stdout_chunk, stderr_chunk in client.api.exec_start(
                    exec_id, demux=True, stream=True
                ):
                    if stdout_chunk:
                        out_buf["stdout"] += stdout_chunk
                    if stderr_chunk:
                        out_buf["stderr"] += stderr_chunk
            except Exception as e:  # killed mid-stream on timeout, etc.
                logger.debug("exec stream ended: %s", e)

        worker = threading.Thread(target=_pump, daemon=True)
        worker.start()
        worker.join(timeout=SANDBOX_TIMEOUT_SECONDS)

        if worker.is_alive():
            timed_out = True
            # Sample PID usage before killing so silent fork bombs are detectable.
            try:
                stats = container.stats(stream=False)
                pids = stats.get("pids_stats", {})
                if pids.get("current", 0) > 0 and pids.get("current") == pids.get("limit"):
                    out_buf["stderr"] += (
                        b"\nBlockingIOError: [Errno 11] Resource temporarily "
                        b"unavailable (PID limit reached)"
                    )
            except Exception:
                pass
            try:
                container.kill()
            except Exception:
                pass
            worker.join(timeout=3)

        # 5. Resolve exit code and OOM state.
        try:
            info = client.api.exec_inspect(exec_id)
            exit_code = info.get("ExitCode")
            if exit_code is None:
                exit_code = -1
        except Exception:
            exit_code = -1

        try:
            container.reload()
            container_attrs = container.attrs
            oom_killed = container_attrs.get("State", {}).get("OOMKilled", False)
        except Exception:
            pass
        # exit 137 outside a timeout kill is a strong OOM/SIGKILL signal.
        if not timed_out and exit_code == 137:
            oom_killed = True

        try:
            raw_diff = container.diff() or []
            fs_diff = [{"Path": d.get("Path", ""), "Kind": d.get("Kind", -1)} for d in raw_diff]
        except Exception as e:
            logger.warning("Failed to collect fs diff: %s", e)

    finally:
        # 6. Teardown — v=True frees any associated anonymous volumes too.
        if container is not None:
            try:
                container.remove(force=True, v=True)
            except Exception as e:
                logger.warning("Failed to remove container %s: %s", container.id[:12], e)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    return RunResult(
        exit_code=exit_code,
        stdout=out_buf["stdout"].decode("utf-8", errors="replace")[:65536],
        stderr=out_buf["stderr"].decode("utf-8", errors="replace")[:65536],
        duration_ms=duration_ms,
        oom_killed=oom_killed,
        timed_out=timed_out,
        fs_diff=fs_diff,
        container_attrs=container_attrs,
    )
