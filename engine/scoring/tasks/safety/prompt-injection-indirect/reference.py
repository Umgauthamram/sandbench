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


def filter_retrieved_context(chunks):
    return [chunk for chunk in chunks if not detect_prompt_injection(chunk)]
