"""Reference solution for json-flatten task."""


def flatten(obj, prefix="", sep="."):
    """Collapse a nested dict/list into dot-delimited keys."""
    result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}{sep}{k}" if prefix else k
            result.update(flatten(v, new_key, sep))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{prefix}{sep}{i}" if prefix else str(i)
            result.update(flatten(v, new_key, sep))
    else:
        result[prefix] = obj
    return result
