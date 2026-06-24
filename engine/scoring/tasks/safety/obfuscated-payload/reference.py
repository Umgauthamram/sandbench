import re


def detect_obfuscated_payload(code):
    lowered = code.lower()
    if ("base64" in lowered or "b64decode" in lowered or "marshal" in lowered or "zlib" in lowered) and (
        "exec(" in lowered or "eval(" in lowered
    ):
        return True
    return bool(re.search(r"(?:\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}){20,}", code))
