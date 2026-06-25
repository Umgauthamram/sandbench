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
client: docker.DockerClient | None = None

# The only writable area at runtime. RAM-backed, hard size cap.
TMPFS = {"/tmp": "rw,size=16m,mode=1777"}


def _get_client() -> docker.DockerClient:
    """Create the Docker client only when a sandbox run actually needs it."""
    global client
    if client is None:
        client = docker.from_env()
    return client


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


def _load_security_opt(audit: bool = False) -> List[str]:
    """security_opt with the seccomp profile embedded as inline JSON.

    The daemon cannot read a client-side path, so docker-py must send content.
    When audit=True the audit profile is used: dangerous syscalls are logged
    rather than blocked so safety-task tests can observe real attempt evidence.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    profile_name = "seccomp_audit.json" if audit else "seccomp.json"
    seccomp_path = os.path.join(current_dir, "images", profile_name)
    if not os.path.exists(seccomp_path):
        logger.warning("%s not found at %s; running without seccomp.", profile_name, seccomp_path)
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


def _parse_mem_to_bytes(mem_str: str) -> int:
    import re
    match = re.match(r"^(\d+)([bkmg])$", mem_str.lower())
    if not match:
        return 256 * 1024 * 1024  # default fallback
    val, unit = int(match.group(1)), match.group(2)
    if unit == 'k':
        return val * 1024
    if unit == 'm':
        return val * 1024 * 1024
    if unit == 'g':
        return val * 1024 * 1024 * 1024
    return val

def _clamp_mem(override: str, ceiling: str = "1024m") -> str:
    override_bytes = _parse_mem_to_bytes(override)
    ceiling_bytes = _parse_mem_to_bytes(ceiling)
    if override_bytes > ceiling_bytes:
        return ceiling
    return override


def _ensure_golden_image(docker_client: docker.DockerClient, image: str) -> None:
    """Ensure the required golden image exists, building it locally if needed."""
    try:
        docker_client.images.get(image)
    except docker.errors.ImageNotFound:
        if image in ("sandbench/python:golden", "sandbench/node:golden"):
            logger.info("Golden image %s not found. Building locally from Dockerfile...", image)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dockerfile_name = "python.Dockerfile" if "python" in image else "node.Dockerfile"
            docker_client.images.build(
                path=os.path.join(current_dir, "images"),
                dockerfile=dockerfile_name,
                tag=image,
                rm=True
            )
        else:
            logger.info("Pulling image %s...", image)
            docker_client.images.pull(image)


def run(
    code: str,
    language: str = "python",
    image: Optional[str] = None,
    extra_files: Optional[Dict[str, str]] = None,
    command: Optional[List[str]] = None,
    timeout_seconds: Optional[int] = None,
    mem_limit: Optional[str] = None,
    cpus: Optional[float] = None,
    is_safety_task: bool = False,
) -> RunResult:
    """Run code inside a hardened, throwaway container and return a RunResult.

    Args:
        code: Source code to execute.
        language: Language identifier ("python" or "node").
        image: Docker image override. Defaults by language.
        extra_files: Optional mapping of {container_abs_path: file_contents}
            to copy into the container alongside the solution file. Keys are
            absolute container paths like "/workspace/tests/test_solution.py".
        command: Optional command override. If None, uses the default
            language-specific run command.
        timeout_seconds: Optional timeout override in seconds (clamped to [1, 60]).
        mem_limit: Optional memory limit override (clamped to max 1024m).
        cpus: Optional cpu cores limit override (clamped to [0.1, 2.0]).
        is_safety_task: When True, uses the audit seccomp profile so dangerous
            syscalls are logged rather than blocked, providing kernel-level
            evidence for safety benchmark evaluation.
    """
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
    run_cmd = command if command is not None else (
        ["node", f"/workspace/{file_name}"] if lang == "node"
        else ["python", f"/workspace/{file_name}"]
    )

    # Apply and clamp resource limits
    timeout_val = SANDBOX_TIMEOUT_SECONDS
    if timeout_seconds is not None:
        timeout_val = min(max(1, timeout_seconds), 60)

    mem_val = SANDBOX_MEM_LIMIT
    if mem_limit is not None:
        mem_val = _clamp_mem(mem_limit, "1024m")

    cpus_val = SANDBOX_CPUS
    if cpus is not None:
        cpus_val = min(max(0.1, cpus), 2.0)

    start_time = time.perf_counter()
    try:
        docker_client = _get_client()
        _ensure_golden_image(docker_client, image)
        
        container = docker_client.containers.create(
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
            security_opt=_load_security_opt(audit=is_safety_task),
            mem_limit=mem_val,
            nano_cpus=int(cpus_val * 1e9),
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

            # Add any extra files (e.g. hidden test suites for scoring).
            if extra_files:
                for container_path, contents in extra_files.items():
                    # put_archive extracts relative to /workspace, so strip
                    # that prefix. e.g. "/workspace/tests/foo.py" -> "tests/foo.py"
                    member_name = container_path.lstrip("/")
                    if member_name.startswith("workspace/"):
                        member_name = member_name[len("workspace/"):]
                    file_bytes = contents.encode("utf-8")
                    ti = tarfile.TarInfo(name=member_name)
                    ti.size = len(file_bytes)
                    ti.mode = 0o644
                    tar.addfile(ti, io.BytesIO(file_bytes))

        tar_stream.seek(0)
        container.put_archive("/workspace", tar_stream.getvalue())

        # 3. Start (read-only root + tmpfs now enforced) and run the code.
        container.start()

        # 4. Wait with a wall-clock timeout.
        try:
            res = container.wait(timeout=timeout_val)
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
