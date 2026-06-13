"""Unified-diff application engine for SandBench.

Applies unified patches to original code files safely in-memory.
"""
import logging
import os
import tempfile
import patch_ng

logger = logging.getLogger(__name__)


def fallback_apply(original_code: str, patch: str) -> str:
    """Fallback unified-diff applier.

    Parses unified hunks and applies them to original_code's lines.
    Raises ValueError if hunks fail to match.
    """
    orig_lines = original_code.splitlines()
    patch_lines = patch.splitlines()

    hunks = []
    current_hunk = None

    for line in patch_lines:
        if line.startswith("@@ "):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    old_part = parts[1]
                    new_part = parts[2]

                    old_info = old_part[1:].split(",")
                    new_info = new_part[1:].split(",")

                    old_start = int(old_info[0])
                    old_len = int(old_info[1]) if len(old_info) > 1 else 1

                    new_start = int(new_info[0])
                    new_len = int(new_info[1]) if len(new_info) > 1 else 1

                    current_hunk = {
                        "old_start": old_start,
                        "old_len": old_len,
                        "new_start": new_start,
                        "new_len": new_len,
                        "lines": []
                    }
                    hunks.append(current_hunk)
                except (ValueError, IndexError):
                    # Ignore malformed hunk header
                    current_hunk = None
        elif current_hunk is not None:
            if line.startswith(" ") or line.startswith("-") or line.startswith("+") or line == "":
                current_hunk["lines"].append(line)
            else:
                current_hunk["lines"].append(" " + line)

    offset = 0
    if not hunks:
        raise ValueError("No hunks found in patch")
    for hunk in hunks:
        old_start = hunk["old_start"]
        expected_orig = []
        replacement = []

        for hl in hunk["lines"]:
            if hl.startswith("-"):
                expected_orig.append(hl[1:])
            elif hl.startswith("+"):
                replacement.append(hl[1:])
            else:
                val = hl[1:] if hl.startswith(" ") else hl
                expected_orig.append(val)
                replacement.append(val)

        target_idx = old_start - 1 + offset
        matched_idx = -1

        # 1. Try target_idx
        if 0 <= target_idx <= len(orig_lines) - len(expected_orig):
            if orig_lines[target_idx : target_idx + len(expected_orig)] == expected_orig:
                matched_idx = target_idx

        # 2. Scan the whole file for exact match
        if matched_idx == -1:
            for i in range(len(orig_lines) - len(expected_orig) + 1):
                if orig_lines[i : i + len(expected_orig)] == expected_orig:
                    matched_idx = i
                    break

        # 3. Scan ignoring trailing whitespace
        if matched_idx == -1:
            for i in range(len(orig_lines) - len(expected_orig) + 1):
                match = True
                for j in range(len(expected_orig)):
                    if orig_lines[i + j].strip() != expected_orig[j].strip():
                        match = False
                        break
                if match:
                    matched_idx = i
                    break

        if matched_idx != -1:
            orig_lines[matched_idx : matched_idx + len(expected_orig)] = replacement
            offset += len(replacement) - len(expected_orig)
        else:
            raise ValueError(f"Hunk at line {old_start} failed to match")

    return "\n".join(orig_lines)


def apply_patch(original_code: str, patch: str) -> tuple[str | None, str]:
    """Tolerant unified-diff application.

    Returns (patched_code, method) where method describes how it applied,
    or (None, reason) if it could not.
    """
    if not patch or not patch.strip():
        return None, "empty patch"

    # Strategy 1: Try patch-ng library
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "solution.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(original_code)

            # Parse the patch in-memory
            pset = patch_ng.fromstring(patch.encode("utf-8"))
            if pset and len(pset.items) > 0:
                # Force target filenames to match solution.py
                for p in pset.items:
                    p.source = b"solution.py"
                    p.target = b"solution.py"
                
                # Apply patch to the temp file
                if pset.apply(root=tmpdir):
                    with open(filepath, "r", encoding="utf-8") as f:
                        patched = f.read()
                    return patched, "patch-ng"
    except Exception as e:
        logger.debug("patch-ng library failed to apply patch: %s", e)

    # Strategy 2: Fallback hand-rolled unified-diff applier
    try:
        patched = fallback_apply(original_code, patch)
        return patched, "fallback"
    except Exception as e:
        logger.debug("fallback unified-diff applier failed: %s", e)

    return None, "patch did not apply"
