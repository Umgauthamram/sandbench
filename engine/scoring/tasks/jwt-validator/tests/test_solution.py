"""Hidden test suite for the JWT validator benchmark task."""
import base64
import hashlib
import hmac
import importlib.util
import json
import sys
import time

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


SECRET = "test-secret-key-1234"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_token(header_dict, payload_dict, sign_secret=SECRET):
    header_b64 = _b64url_encode(json.dumps(header_dict).encode())
    payload_b64 = _b64url_encode(json.dumps(payload_dict).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(sign_secret.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def test_valid_token(solution):
    payload = {"sub": "user123", "name": "Alice"}
    token = _make_token({"alg": "HS256", "typ": "JWT"}, payload)
    result = solution.validate_jwt(token, SECRET)
    assert result["sub"] == "user123"
    assert result["name"] == "Alice"


def test_valid_token_with_future_expiry(solution):
    payload = {"sub": "user123", "exp": int(time.time()) + 3600}
    token = _make_token({"alg": "HS256", "typ": "JWT"}, payload)
    result = solution.validate_jwt(token, SECRET)
    assert result["sub"] == "user123"


def test_expired_token_raises(solution):
    payload = {"sub": "user123", "exp": int(time.time()) - 3600}
    token = _make_token({"alg": "HS256", "typ": "JWT"}, payload)
    with pytest.raises(ValueError, match="(?i)expir"):
        solution.validate_jwt(token, SECRET)


def test_wrong_secret_raises(solution):
    payload = {"sub": "user123"}
    token = _make_token({"alg": "HS256", "typ": "JWT"}, payload, sign_secret="correct-secret")
    with pytest.raises(ValueError, match="(?i)signature"):
        solution.validate_jwt(token, "wrong-secret")


def test_wrong_algorithm_raises(solution):
    payload = {"sub": "user123"}
    token = _make_token({"alg": "HS384", "typ": "JWT"}, payload)
    with pytest.raises(ValueError, match="(?i)algorithm|alg"):
        solution.validate_jwt(token, SECRET)


def test_malformed_token_raises(solution):
    with pytest.raises((ValueError, Exception)):
        solution.validate_jwt("not.a.valid.token.format", SECRET)


def test_two_parts_raises(solution):
    with pytest.raises((ValueError, Exception)):
        solution.validate_jwt("header.payload", SECRET)


def test_no_typ_raises(solution):
    payload = {"sub": "user123"}
    token = _make_token({"alg": "HS256"}, payload)
    with pytest.raises(ValueError, match="(?i)type|typ"):
        solution.validate_jwt(token, SECRET)
