"""Reference solution for rest-api-parser task."""
from urllib.parse import urlparse, parse_qs


VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def parse_http_request(raw_request: str) -> dict:
    """Parse a raw HTTP request string into a structured dictionary."""
    if not raw_request or not raw_request.strip():
        raise ValueError("Empty request")

    # Split headers and body at the blank line
    if "\r\n\r\n" in raw_request:
        header_section, body = raw_request.split("\r\n\r\n", 1)
        lines = header_section.split("\r\n")
    elif "\n\n" in raw_request:
        header_section, body = raw_request.split("\n\n", 1)
        lines = header_section.split("\n")
    else:
        lines = raw_request.split("\n")
        body = ""

    if not lines:
        raise ValueError("No request line found")

    # Parse request line
    request_line = lines[0].strip()
    parts = request_line.split(" ")
    if len(parts) != 3:
        raise ValueError(f"Malformed request line: {request_line!r}")

    method, full_path, version = parts

    if method not in VALID_METHODS:
        raise ValueError(f"Invalid HTTP method: {method!r}")

    # Parse path and query params
    if "?" in full_path:
        path, query_string = full_path.split("?", 1)
        raw_params = parse_qs(query_string, keep_blank_values=True)
        query_params = {k: v[0] if len(v) == 1 else v for k, v in raw_params.items()}
    else:
        path = full_path
        query_params = {}

    # Parse headers
    headers = {}
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        headers[key.strip().lower()] = value.strip()

    return {
        "method": method,
        "path": path,
        "version": version,
        "headers": headers,
        "query_params": query_params,
        "body": body,
    }
