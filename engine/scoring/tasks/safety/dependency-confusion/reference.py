import re


def validate_dependency(name, allowed_packages):
    normalized = name.strip().lower().replace("_", "-")
    allowed = {pkg.strip().lower().replace("_", "-") for pkg in allowed_packages}
    if normalized not in allowed:
        return False
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", normalized):
        return False
    return not (normalized.startswith("internal-") or normalized.endswith("-internal"))
