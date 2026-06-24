"""Monitorability trace and CWE helpers for safety evaluation."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List


RULE_CWE: Dict[str, str] = {
    "NET_EGRESS_ATTEMPT": "CWE-918",
    "FS_WRITE_OUTSIDE": "CWE-22",
    "FORK_BOMB": "CWE-400",
    "OOM_KILL": "CWE-400",
    "DISK_EXHAUSTION": "CWE-400",
    "YARA_MATCH": "CWE-506",
    "BANDIT_HIGH": "CWE-693",
    "BANDIT_MEDIUM": "CWE-693",
    "SEMGREP_SECURITY": "CWE-693",
    "OBFUSCATION": "CWE-506",
    "TIMEOUT": "CWE-400",
}

RULE_CATEGORY: Dict[str, str] = {
    "NET_EGRESS_ATTEMPT": "network",
    "FS_WRITE_OUTSIDE": "filesystem",
    "FORK_BOMB": "process",
    "OOM_KILL": "resource",
    "DISK_EXHAUSTION": "resource",
    "YARA_MATCH": "malware",
    "BANDIT_HIGH": "static-analysis",
    "BANDIT_MEDIUM": "static-analysis",
    "SEMGREP_SECURITY": "static-analysis",
    "OBFUSCATION": "evasion",
    "TIMEOUT": "resource",
}


def classify_rule(rule_id: str) -> Dict[str, str]:
    return {
        "cwe": RULE_CWE.get(rule_id, ""),
        "category": RULE_CATEGORY.get(rule_id, "unknown"),
    }


def flags_to_trace(flags: Iterable[Any]) -> List[Dict[str, str]]:
    trace = []
    for flag in flags:
        rule_id = getattr(flag, "rule_id", "")
        metadata = classify_rule(rule_id)
        trace.append(
            {
                "rule_id": rule_id,
                "severity": getattr(getattr(flag, "severity", None), "value", str(getattr(flag, "severity", ""))).lower(),
                "source": getattr(flag, "source", ""),
                "location": getattr(flag, "location", ""),
                "evidence": getattr(flag, "evidence", ""),
                "cwe": metadata["cwe"],
                "category": metadata["category"],
            }
        )
    return trace


def build_monitorability_trace(
    container_attrs: Dict[str, Any],
    fs_diff: List[Dict[str, Any]],
    stdout: str,
    stderr: str,
    timed_out: bool,
) -> Dict[str, Any]:
    state = container_attrs.get("State", {}) if container_attrs else {}
    combined = f"{stdout or ''}\n{stderr or ''}"
    return {
        "network_error_lines": [
            line.strip()
            for line in combined.splitlines()
            if any(token in line for token in ("Network is unreachable", "getaddrinfo", "ECONNREFUSED", "ENOTFOUND"))
        ][:10],
        "filesystem_changes": fs_diff[:50],
        "resource_events": {
            "timed_out": timed_out,
            "oom_killed": bool(state.get("OOMKilled", False)),
            "exit_code": state.get("ExitCode"),
        },
    }
