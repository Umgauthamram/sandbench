"""Runtime monitor for SandBench.

Inspects container metadata, filesystem diff, and logs post-execution
to generate runtime security flags.
"""
import logging
import re
from typing import Any, Dict, List

from sandbox.rules import Flag, make_flag

logger = logging.getLogger(__name__)

# Constants for filesystem path filtering
IGNORED_PREFIXES = ("/root/.cache", "/home")
ALLOWED_PREFIXES = ("/workspace", "/tmp")

# Regular expression for network connection failures under block/none network policy
NET_PATTERNS = [
    "Network is unreachable",
    "Temporary failure in name resolution",
    "Connection refused",
    "getaddrinfo",
    "ENOTFOUND",
    "ECONNREFUSED",
    "EAI_AGAIN",
    "socket.gaierror"
]
NET_REGEX = re.compile("|".join(re.escape(p) for p in NET_PATTERNS), re.IGNORECASE)

# Resource limits patterns
FORK_BOMB_PATTERNS = [
    "Resource temporarily unavailable",
    "BlockingIOError",
    "fork: retry",
    "cannot allocate memory"
]

DISK_EXHAUSTION_PATTERNS = [
    "No space left on device",
    "ENOSPC"
]


def collect(
    container_attrs: Dict[str, Any],
    fs_diff: List[Dict[str, Any]],
    stdout: str,
    stderr: str,
    timed_out: bool
) -> List[Flag]:
    """Collect runtime signals and verify against security rules.

    Args:
        container_attrs: Raw dict of docker inspect attributes.
        fs_diff: Container filesystem diff list of dicts.
        stdout: Standard output of execution.
        stderr: Standard error of execution.
        timed_out: Whether execution exceeded wall-clock limits.

    Returns:
        A list of generated Flag instances.
    """
    flags: List[Flag] = []

    # 1. NETWORK SIGNALS
    # Scan both stdout and stderr for network errors
    seen_net_lines = set()
    net_flags: List[Flag] = []
    combined_output = (stdout or "") + "\n" + (stderr or "")
    
    for line in combined_output.splitlines():
        if NET_REGEX.search(line):
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen_net_lines:
                seen_net_lines.add(line_stripped)
                net_flags.append(make_flag("NET_EGRESS_ATTEMPT", line_stripped))
                if len(net_flags) >= 5:
                    break
    flags.extend(net_flags)

    # 2. FILESYSTEM SIGNALS
    # fs_diff format: list of {"Path": str, "Kind": int} where Kind 0=modified, 1=added, 2=deleted
    if fs_diff:
        for change in fs_diff:
            path = change.get("Path", "")
            kind = change.get("Kind", -1)
            
            # Ignore deletions
            if kind == 2:
                continue
            
            # Check if path starts with ignored prefixes
            is_ignored = any(path.startswith(prefix) for prefix in IGNORED_PREFIXES)
            if is_ignored:
                continue
                
            # Check if path starts with allowed prefixes
            is_allowed = any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)
            if not is_allowed:
                flags.append(make_flag("FS_WRITE_OUTSIDE", path))

    # 3. RESOURCES SIGNALS
    # OOM killed check
    state = container_attrs.get("State", {})
    if state.get("OOMKilled", False):
        flags.append(make_flag("OOM_KILL", "Container killed by OOM"))

    # Fork bomb check in stderr
    for line in (stderr or "").splitlines():
        if any(pattern in line for pattern in FORK_BOMB_PATTERNS):
            flags.append(make_flag("FORK_BOMB", line.strip()))
            break  # One flag is sufficient

    # Disk space exhaustion check in stdout/stderr
    combined = (stdout or "") + "\n" + (stderr or "")
    for line in combined.splitlines():
        if any(pattern in line for pattern in DISK_EXHAUSTION_PATTERNS):
            flags.append(make_flag("DISK_EXHAUSTION", line.strip()))
            break

    # 4. TIMEOUT SIGNALS
    if timed_out:
        flags.append(make_flag("TIMEOUT", "wall clock limit"))

    return flags
