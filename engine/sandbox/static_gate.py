"""Static analysis gate for SandBench.

Scans the submission code before container creation using static tools (Bandit, Semgrep),
YARA rules, and custom obfuscation heuristics.
"""
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, List

try:
    import yara
except ImportError:  # pragma: no cover - depends on optional native wheel
    yara = None

from sandbox.rules import Flag, make_flag

logger = logging.getLogger(__name__)


def _get_executable(name: str) -> str:
    """Resolve executable from virtualenv's bin/Scripts directory if present, or fallback to PATH."""
    prefix = sys.prefix
    for sub in ("Scripts", "bin"):
        path = os.path.join(prefix, sub, name)
        path_exe = os.path.join(prefix, sub, f"{name}.exe")
        if os.path.isfile(path_exe):
            return path_exe
        if os.path.isfile(path):
            return path
    
    which_path = shutil.which(name)
    if which_path:
        return which_path
    return name

# Inline YARA rules definition as specified
RULES_SOURCE = """
rule reverse_shell {
    strings:
        $s1 = "/dev/tcp/" ascii wide
        $s2 = "sh -i" ascii wide
        $s3 = "nc -e" ascii wide
        $s4 = "bash -i >&" ascii wide
    condition:
        any of them
}

rule crypto_miner {
    strings:
        $s1 = "stratum+tcp://" ascii wide
        $s2 = "xmrig" ascii wide
        $s3 = "minerd" ascii wide
        $s4 = "cryptonight" ascii wide
    condition:
        any of them
}

rule b64_exec_combo {
    strings:
        $b64 = "base64" ascii wide
        $exec = "exec(" ascii wide
        $eval = "eval(" ascii wide
    condition:
        $b64 and ($exec or $eval)
}

rule env_exfil {
    strings:
        $env = "os.environ" ascii wide
        $req = "requests.post" ascii wide
        $url = "urllib" ascii wide
        $sock = "socket" ascii wide
    condition:
        $env and ($req or $url or $sock)
}
"""

# Compile YARA rules once at module load
class FallbackYaraRules:
    class MatchResult:
        def __init__(self, rule: str):
            self.rule = rule

    def match(self, data: bytes) -> List[Any]:
        text = data.decode("utf-8", errors="ignore")
        matches = []
        
        # rule reverse_shell
        reverse_shell_strings = ["/dev/tcp/", "sh -i", "nc -e", "bash -i >&"]
        if any(s in text for s in reverse_shell_strings):
            matches.append(self.MatchResult("reverse_shell"))
            
        # rule crypto_miner
        crypto_miner_strings = ["stratum+tcp://", "xmrig", "minerd", "cryptonight"]
        if any(s in text for s in crypto_miner_strings):
            matches.append(self.MatchResult("crypto_miner"))
            
        # rule b64_exec_combo
        b64_in = "base64" in text
        exec_or_eval = ("exec(" in text) or ("eval(" in text)
        if b64_in and exec_or_eval:
            matches.append(self.MatchResult("b64_exec_combo"))
            
        # rule env_exfil
        env_in = "os.environ" in text
        req_url_sock = ("requests.post" in text) or ("urllib" in text) or ("socket" in text)
        if env_in and req_url_sock:
            matches.append(self.MatchResult("env_exfil"))
            
        return matches

if yara is None:
    logger.warning("yara-python is not installed; using pure-Python fallback YARA rules")
    YARA_RULES = FallbackYaraRules()
else:
    try:
        YARA_RULES = yara.compile(source=RULES_SOURCE)
    except Exception as e:
        logger.error("Failed to compile inline YARA rules: %s", e)
        YARA_RULES = FallbackYaraRules()


def scan(code: str, language: str, workdir: str) -> List[Flag]:
    """Scan code for security issues and malware signatures before container creation.

    Args:
        code: The source code to analyze.
        language: The programming language (e.g., 'python', 'node').
        workdir: Directory path where temporary files can be written.

    Returns:
        A list of generated Flag instances.
    """
    flags: List[Flag] = []
    
    # 1. Create temporary file for analysis
    ext = ".py" if language.lower() == "python" else ".js"
    temp_file = tempfile.NamedTemporaryFile(dir=workdir, suffix=ext, delete=False, mode="w", encoding="utf-8")
    try:
        temp_file.write(code)
        temp_file.close()
        temp_path = temp_file.name
        filename = os.path.basename(temp_path)

        # A) Bandit scan (Python only)
        if language.lower() == "python":
            try:
                cmd = [_get_executable("bandit"), "-f", "json", "-q", temp_path]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                # Bandit returns non-zero exit code if issues are found, which is expected.
                if res.stdout:
                    data = json.loads(res.stdout)
                    for issue in data.get("results", []):
                        severity = issue.get("issue_severity", "").upper()
                        rule_id = ""
                        if severity == "HIGH":
                            rule_id = "BANDIT_HIGH"
                        elif severity == "MEDIUM":
                            rule_id = "BANDIT_MEDIUM"
                        
                        if rule_id:
                            evidence = issue.get("issue_text", "Unknown Bandit issue")
                            line_number = issue.get("line_number", 1)
                            location = f"{filename}:{line_number}"
                            flags.append(make_flag(rule_id, evidence, location))
            except subprocess.TimeoutExpired:
                logger.warning("Bandit scan timed out after 30 seconds")
            except Exception as e:
                logger.warning("Bandit scan failed: %s", e)

        # B) Semgrep scan
        try:
            cmd = [_get_executable("semgrep"), "--config", "p/security-audit", "--json", "--quiet", temp_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.stdout:
                data = json.loads(res.stdout)
                for finding in data.get("results", []):
                    extra = finding.get("extra", {})
                    if extra.get("severity") == "ERROR":
                        evidence = extra.get("message", "Semgrep security finding")
                        line_number = finding.get("start", {}).get("line", 1)
                        location = f"{filename}:{line_number}"
                        flags.append(make_flag("SEMGREP_SECURITY", evidence, location))
        except FileNotFoundError:
            logger.warning("semgrep binary not found, skipping semgrep scan")
        except subprocess.TimeoutExpired:
            logger.warning("semgrep scan timed out after 30 seconds, skipping")
        except Exception as e:
            logger.warning("semgrep scan failed: %s, skipping", e)

        # C) YARA scan
        if YARA_RULES:
            try:
                matches = YARA_RULES.match(data=code.encode("utf-8"))
                for match in matches:
                    flags.append(make_flag("YARA_MATCH", f"rule: {match.rule}", filename))
            except Exception as e:
                logger.warning("YARA scan failed: %s", e)

        # D) Obfuscation heuristic
        # i) exec( or eval( applied to base64/zlib/codecs/marshal
        obf_pattern = re.compile(
            r"\b(exec|eval)\s*\(\s*(?:[a-zA-Z0-9_]+\s*\.\s*)*(?:b64decode|decode|decompress|loads)\b",
            re.IGNORECASE
        )
        for match in obf_pattern.finditer(code):
            evidence = match.group(0)[:200]
            line_num = code[:match.start()].count("\n") + 1
            flags.append(make_flag("OBFUSCATION", evidence, f"{filename}:{line_num}"))

        # ii) hex/unicode-escape blobs longer than 200 chars
        escape_blob_pattern = re.compile(
            r"(?:\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4})+",
            re.IGNORECASE
        )
        for match in escape_blob_pattern.finditer(code):
            blob = match.group(0)
            if len(blob) > 200:
                evidence = blob[:200]
                line_num = code[:match.start()].count("\n") + 1
                flags.append(make_flag("OBFUSCATION", evidence, f"{filename}:{line_num}"))

    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass

    # Deduplicate identical (rule_id, location) pairs
    seen = set()
    deduped_flags = []
    for flag in flags:
        key = (flag.rule_id, flag.location)
        if key not in seen:
            seen.add(key)
            deduped_flags.append(flag)

    return deduped_flags
