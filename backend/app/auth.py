"""Authentication, session lifecycle, and RBAC helpers for protected API routes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.project_store import (
    auth_identity_user_key,
    create_auth_session,
    get_auth_session,
    get_auth_session_by_refresh_hash,
    get_user_by_id,
    list_auth_sessions_for_user,
    revoke_auth_session,
    revoke_other_auth_sessions,
    rotate_auth_session,
    touch_auth_session,
)

_BEARER = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    """Read JWT secret while keeping local development functional by default."""
    return (os.getenv("SOLAR_SHARE_JWT_SECRET") or "solarshare-dev-secret").strip()


def _jwt_algorithm() -> str:
    """Return signed-token algorithm used by access token helpers."""
    return "HS256"


def _token_expiry_minutes() -> int:
    """Return default access-token TTL from env with safe fallback."""
    raw_value = (os.getenv("SOLAR_SHARE_JWT_EXPIRES_MINUTES") or "60").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 60
    return max(min(parsed, 43200), 5)


def _refresh_expiry_days() -> int:
    """Return refresh token TTL in days for session rotation."""
    raw_value = (os.getenv("SOLAR_SHARE_REFRESH_EXPIRES_DAYS") or "30").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 30
    return max(min(parsed, 365), 1)


def _b64url_encode(raw: bytes) -> str:
    """Encode bytes using URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    """Decode URL-safe base64 handling optional missing padding."""
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def _hash_refresh_token(refresh_token: str) -> str:
    """Hash refresh token before persistence to avoid storing raw secrets."""
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def _is_session_active(session: Dict[str, Any]) -> bool:
    """Check session revocation and expiry window."""
    if session.get("revoked_at"):
        return False
    expires_at = str(session.get("expires_at") or "")
    if not expires_at:
        return False
    return expires_at > datetime.now(timezone.utc).isoformat()


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


def _build_access_token(user: Dict[str, Any], session_id: str) -> tuple[str, str]:
    """Create signed JWT bound to a persisted session ID."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=_token_expiry_minutes())
    payload = {
        "sub": str(user["id"]),
        "email": str(user["email"]),
        "role": str(user.get("role") or "customer"),
        "sid": session_id,
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    header = {"alg": _jwt_algorithm(), "typ": "JWT"}
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(_jwt_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    token = f"{header_part}.{payload_part}.{_b64url_encode(signature)}"
    return token, expires_at.isoformat()


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


def _session_auth_response(user: Dict[str, Any], session: Dict[str, Any], refresh_token: str) -> Dict[str, Any]:
    """Build unified auth response with access + refresh + session metadata."""
    access_token, access_expires_at = _build_access_token(user=user, session_id=str(session["id"]))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": access_expires_at,
        "refresh_token": refresh_token,
        "refresh_expires_at": str(session["expires_at"]),
        "session": {
            "id": str(session["id"]),
            "device_name": session.get("device_name"),
            "user_agent": session.get("user_agent"),
            "ip_address": session.get("ip_address"),
            "created_at": session.get("created_at"),
            "last_seen_at": session.get("last_seen_at"),
            "expires_at": session.get("expires_at"),
            "is_active": bool(not session.get("revoked_at")),
        },
        "user": {
            "id": str(user["id"]),
            "email": str(user["email"]),
            "role": str(user.get("role") or "customer"),
            "user_identity_key": auth_identity_user_key(str(user["id"])),
        },
    }


def create_access_token(
    user: Dict[str, Any],
    device_name: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> Dict[str, Any]:
    """Create a new session and return access/refresh token bundle."""
    refresh_token = secrets.token_urlsafe(48)
    refresh_expires_at = (datetime.now(timezone.utc) + timedelta(days=_refresh_expiry_days())).isoformat()
    session = create_auth_session(
        user_id=str(user["id"]),
        refresh_token_hash=_hash_refresh_token(refresh_token),
        expires_at=refresh_expires_at,
        device_name=device_name,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return _session_auth_response(user=user, session=session, refresh_token=refresh_token)


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Rotate refresh token and return fresh access token for active sessions."""
    normalized_refresh = (refresh_token or "").strip()
    if not normalized_refresh:
        raise HTTPException(status_code=401, detail="Refresh token is required.")
    session = get_auth_session_by_refresh_hash(_hash_refresh_token(normalized_refresh))
    if not session or not _is_session_active(session):
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired.")

    user = get_user_by_id(str(session["user_id"]))
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists.")

    new_refresh_token = secrets.token_urlsafe(48)
    new_expiry = (datetime.now(timezone.utc) + timedelta(days=_refresh_expiry_days())).isoformat()
    rotated = rotate_auth_session(str(session["id"]), _hash_refresh_token(new_refresh_token), new_expiry)
    if not rotated:
        raise HTTPException(status_code=401, detail="Session no longer active.")
    updated_session = get_auth_session(str(session["id"]))
    if not updated_session:
        raise HTTPException(status_code=401, detail="Session no longer active.")
    return _session_auth_response(user=user, session=updated_session, refresh_token=new_refresh_token)


def revoke_current_session(refresh_token: str) -> bool:
    """Revoke session by refresh token."""
    normalized_refresh = (refresh_token or "").strip()
    if not normalized_refresh:
        return False
    session = get_auth_session_by_refresh_hash(_hash_refresh_token(normalized_refresh))
    if not session:
        return False
    return revoke_auth_session(str(session["id"]), reason="logout")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_BEARER),
) -> Dict[str, Any]:
    """Resolve authenticated user from Bearer token and verify session state."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(credentials.credentials)
    user_id = str(payload.get("sub") or "").strip()
    session_id = str(payload.get("sid") or "").strip()
    if not user_id or not session_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    session = get_auth_session(session_id)
    if not session or str(session.get("user_id") or "") != user_id or not _is_session_active(session):
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    touch_auth_session(session_id)
    request.state.session_id = session_id
    return {
        "id": str(user["id"]),
        "email": str(user["email"]),
        "role": str(user.get("role") or "customer"),
        "user_identity_key": auth_identity_user_key(str(user["id"])),
        "session_id": session_id,
    }


def require_roles(*roles: str):
    """Create dependency that enforces user role membership for RBAC routes."""
    required = {role.strip().lower() for role in roles if role.strip()}

    def _dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        role = str(current_user.get("role") or "").strip().lower()
        if required and role not in required:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return current_user

    return _dependency


def list_user_sessions(user_id: str) -> list[dict[str, Any]]:
    """Expose user sessions for account security controls."""
    return list_auth_sessions_for_user(user_id=user_id)


def revoke_session_by_id_for_user(user_id: str, session_id: str) -> bool:
    """Revoke one user-owned session."""
    session = get_auth_session(session_id)
    if not session or str(session.get("user_id") or "") != (user_id or "").strip():
        return False
    return revoke_auth_session(session_id=session_id, reason="user_session_revoke")


def revoke_other_sessions_for_user(user_id: str, keep_session_id: str | None) -> int:
    """Revoke all sessions except the one currently used."""
    return revoke_other_auth_sessions(user_id=user_id, keep_session_id=keep_session_id)
