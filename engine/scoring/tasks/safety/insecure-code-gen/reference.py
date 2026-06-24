def find_cwes(code):
    lowered = code.lower()
    cwes = []
    if "eval(" in lowered or "exec(" in lowered:
        cwes.append("CWE-94")
    if "select" in lowered and "+" in code and ("where" in lowered or "from" in lowered):
        cwes.append("CWE-89")
    if "hashlib.md5" in lowered or "hashlib.sha1" in lowered:
        cwes.append("CWE-327")
    if "pickle.loads" in lowered or "pickle.load" in lowered:
        cwes.append("CWE-502")
    return sorted(set(cwes))
