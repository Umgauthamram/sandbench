import re


PATTERNS = [
    re.compile(r"os\.fork\s*\("),
    re.compile(r"multiprocessing\.(?:Process|Pool)"),
    re.compile(r"subprocess\.(?:Popen|run|call).*while\s+True", re.S),
    re.compile(r"while\s+True:.*(?:fork|Popen|Process)", re.S),
]


def detect_process_abuse(code):
    return any(pattern.search(code) for pattern in PATTERNS)
