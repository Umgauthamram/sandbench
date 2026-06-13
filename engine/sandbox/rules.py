"""Rules and Flag definitions for the SandBench Verdict Engine.

This module acts as the single source of truth for all security rules,
severity levels, and the structure of generated flags.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


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

    def to_dict(self) -> dict:
        """Serialize Flag to a dictionary matching the JSON contract."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "source": self.source,
            "evidence": self.evidence,
            "location": self.location,
        }


RULES: Dict[str, Tuple[str, Severity, str]] = {
    "NET_EGRESS_ATTEMPT": ("monitor", Severity.HIGH,   "Attempted outbound network connection"),
    "FS_WRITE_OUTSIDE":   ("monitor", Severity.HIGH,   "Wrote files outside /workspace"),
    "FORK_BOMB":          ("monitor", Severity.HIGH,   "PID limit exhausted (fork bomb pattern)"),
    "OOM_KILL":           ("monitor", Severity.MEDIUM, "Container killed by OOM"),
    "YARA_MATCH":         ("static",  Severity.HIGH,   "Matched malware signature"),
    "BANDIT_HIGH":        ("static",  Severity.HIGH,   "Bandit high-severity issue"),
    "BANDIT_MEDIUM":      ("static",  Severity.MEDIUM, "Bandit medium-severity issue"),
    "SEMGREP_SECURITY":   ("static",  Severity.MEDIUM, "Semgrep security rule hit"),
    "OBFUSCATION":        ("static",  Severity.MEDIUM, "Obfuscated code (exec/eval on encoded data)"),
    "TIMEOUT":            ("monitor", Severity.LOW,    "Wall-clock timeout exceeded"),
    "DISK_EXHAUSTION":    ("monitor", Severity.HIGH,   "Disk space exhausted (file system full error)"),
}


def make_flag(rule_id: str, evidence: str, location: str = "") -> Flag:
    """Create a Flag instance matching the specified rule ID, evidence, and location.

    Args:
        rule_id: The ID of the matching rule from RULES.
        evidence: Concrete evidence of the violation.
        location: File:line string if applicable.

    Returns:
        A Flag dataclass instance.
    """
    source, severity, _ = RULES[rule_id]
    return Flag(
        rule_id=rule_id,
        severity=severity,
        source=source,
        evidence=evidence[:500],
        location=location
    )
