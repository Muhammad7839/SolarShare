"""Authentication helpers for customer JWT access and protected API routes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.project_store import auth_identity_user_key, get_user_by_id

_BEARER = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    """Read JWT secret while keeping local development functional by default."""
    return (os.getenv("SOLAR_SHARE_JWT_SECRET") or "solarshare-dev-secret").strip()


def _jwt_algorithm() -> str:
    """Return signed-token algorithm used by access token helpers."""
    return "HS256"


def _token_expiry_minutes() -> int:
    """Return default access-token TTL from env with safe fallback."""
    raw_value = (os.getenv("SOLAR_SHARE_JWT_EXPIRES_MINUTES") or "720").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 720
    return max(min(parsed, 43200), 15)


def _b64url_encode(raw: bytes) -> str:
    """Encode bytes using URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    """Decode URL-safe base64 handling optional missing padding."""
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def hash_password(password: str) -> str:
    """Hash passwords with PBKDF2-SHA256 and per-user random salts."""
    salt = os.urandom(16)
    iterations = 390_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against stored PBKDF2 hash."""
    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64)
        expected_digest = base64.b64decode(digest_b64)
    except Exception:
        return False

    candidate_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate_digest, expected_digest)


def create_access_token(user: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a signed JWT for authenticated API usage."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=_token_expiry_minutes())
    payload = {
        "sub": str(user["id"]),
        "email": str(user["email"]),
        "role": str(user.get("role") or "customer"),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    header = {"alg": _jwt_algorithm(), "typ": "JWT"}
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    token = f"{header_part}.{payload_part}.{_b64url_encode(signature)}"
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": str(user["id"]),
            "email": str(user["email"]),
            "role": str(user.get("role") or "customer"),
            "user_identity_key": auth_identity_user_key(str(user["id"])),
        },
    }


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed token")
        header_part, payload_part, signature_part = parts
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected_signature = hmac.new(_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_signature = _b64url_decode(signature_part)
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise ValueError("signature mismatch")

        header = json.loads(_b64url_decode(header_part).decode("utf-8"))
        if header.get("alg") != _jwt_algorithm():
            raise ValueError("unsupported algorithm")

        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
        expires_at = int(payload.get("exp") or 0)
        if expires_at < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("token expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_BEARER)) -> Dict[str, Any]:
    """Resolve authenticated user from Bearer token and verify account presence."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(credentials.credentials)
    user_id = str(payload.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return {
        "id": str(user["id"]),
        "email": str(user["email"]),
        "role": str(user.get("role") or "customer"),
        "user_identity_key": auth_identity_user_key(str(user["id"])),
    }
