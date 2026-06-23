"""Reference solution for config-parser task."""


def parse_ini(text):
    """Parse an INI-format string into a nested dictionary."""
    result = {}
    current_section = "__global__"
    result[current_section] = {}

    for line in text.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith(";") or line.startswith("#"):
            continue

        # Section header
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            if current_section not in result:
                result[current_section] = {}
            continue

        # Key=value pair
        if "=" in line:
            key, _, value = line.partition("=")
            result[current_section][key.strip()] = value.strip()

    # Remove __global__ if it's empty
    if not result.get("__global__"):
        del result["__global__"]

    return result
