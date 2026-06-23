"""Hidden test suite for the REST API parser benchmark task."""
import importlib.util
import sys

import pytest


def _load_solution():
    spec = importlib.util.spec_from_file_location("solution", "/workspace/solution.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["solution"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def solution():
    return _load_solution()


def test_simple_get(solution):
    raw = "GET /api/users HTTP/1.1\nHost: example.com\n\n"
    result = solution.parse_http_request(raw)
    assert result["method"] == "GET"
    assert result["path"] == "/api/users"
    assert result["version"] == "HTTP/1.1"


def test_headers_normalized_lowercase(solution):
    raw = "GET / HTTP/1.1\nContent-Type: application/json\nX-Custom-Header: value123\n\n"
    result = solution.parse_http_request(raw)
    assert result["headers"]["content-type"] == "application/json"
    assert result["headers"]["x-custom-header"] == "value123"


def test_query_params(solution):
    raw = "GET /search?q=python&page=2 HTTP/1.1\nHost: example.com\n\n"
    result = solution.parse_http_request(raw)
    assert result["path"] == "/search"
    assert result["query_params"]["q"] == "python"
    assert result["query_params"]["page"] == "2"


def test_post_with_body(solution):
    raw = 'POST /api/data HTTP/1.1\nContent-Type: application/json\n\n{"key": "value"}'
    result = solution.parse_http_request(raw)
    assert result["method"] == "POST"
    assert result["body"] == '{"key": "value"}'


def test_empty_query_params(solution):
    raw = "GET /api HTTP/1.1\nHost: localhost\n\n"
    result = solution.parse_http_request(raw)
    assert result["query_params"] == {}


def test_empty_body(solution):
    raw = "GET /api HTTP/1.1\nHost: localhost\n\n"
    result = solution.parse_http_request(raw)
    assert result["body"] == ""


def test_invalid_method_raises(solution):
    raw = "INVALID /api HTTP/1.1\n\n"
    with pytest.raises(ValueError):
        solution.parse_http_request(raw)


def test_empty_request_raises(solution):
    with pytest.raises(ValueError):
        solution.parse_http_request("")


def test_header_with_colon_in_value(solution):
    raw = "GET / HTTP/1.1\nAuthorization: Bearer token:extra:data\n\n"
    result = solution.parse_http_request(raw)
    assert result["headers"]["authorization"] == "Bearer token:extra:data"
