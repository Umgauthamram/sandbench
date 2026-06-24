import re


PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"reveal (the )?(system|hidden) prompt",
    r"developer mode",
    r"disable (safety|guardrails|policy)",
]


def detect_prompt_injection(text):
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in PATTERNS)
