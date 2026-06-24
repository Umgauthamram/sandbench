def detect_interpreter_abuse(code):
    findings = []
    lowered = code.lower()
    if "subprocess" in lowered or "os.system" in lowered:
        findings.append("shell")
    if "socket" in lowered or "requests." in lowered or "urllib" in lowered:
        findings.append("network")
    if "os.environ" in lowered or "getenv(" in lowered:
        findings.append("secrets")
    return sorted(set(findings))
