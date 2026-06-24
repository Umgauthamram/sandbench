from pathlib import Path


def safe_join(root, requested_path):
    root_path = Path(root).resolve()
    candidate = (root_path / requested_path).resolve()
    if root_path != candidate and root_path not in candidate.parents:
        raise ValueError("path escapes root")
    return str(candidate)
