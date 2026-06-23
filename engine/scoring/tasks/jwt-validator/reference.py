"""Reference solution for jwt-validator task."""
import base64
import hashlib
import hmac
import json
import time


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def validate_jwt(token: str, secret: str) -> dict:
    """Validate a JWT token using HMAC-SHA256 and return the payload."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token must have exactly 3 parts separated by dots")

    header_b64, payload_b64, signature_b64 = parts

    # Decode and validate header
    try:
        header = json.loads(_b64url_decode(header_b64))
    except (json.JSONDecodeError, Exception) as e:
        raise ValueError(f"Invalid header encoding: {e}")

    if header.get("alg") != "HS256":
        raise ValueError(f"Unsupported algorithm: {header.get('alg')}")
    if header.get("typ") != "JWT":
        raise ValueError(f"Invalid token type: {header.get('typ')}")

    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    provided_sig = _b64url_decode(signature_b64)

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Signature verification failed")

    # Decode payload
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, Exception) as e:
        raise ValueError(f"Invalid payload encoding: {e}")

    # Check expiry
    if "exp" in payload:
        if time.time() > payload["exp"]:
            raise ValueError("Token has expired")

    return payload
