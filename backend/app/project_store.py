"""Persistent project, subscription, waitlist, and billing-ledger storage for SolarShare."""

from __future__ import annotations

import io
import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[1] / "ops_analytics.sqlite3")

SEED_PROJECTS: list[tuple[str, str, str, float, int, int, str]] = [
    ("Long Island Solar One", "Long Island", "PSEG Long Island", 6400.0, 412, 88, "dual"),
    ("Long Island East Farm", "Long Island", "PSEG Long Island", 5200.0, 366, 54, "consolidated"),
    ("NYC Community Array", "NYC", "Con Edison", 9800.0, 771, 129, "consolidated"),
    ("Brooklyn Shared Solar", "NYC", "Con Edison", 4600.0, 321, 39, "dual"),
    ("Hudson Valley Shared Solar", "Upstate", "Central Hudson", 4300.0, 250, 42, "consolidated"),
    ("Capital Region Solar Pool", "Upstate", "National Grid", 5100.0, 307, 55, "consolidated"),
]


MONTH_ORDER = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

INVOICE_STATUSES = {"draft", "issued", "paid", "failed"}
STATUS_REQUEST_STATES = {"pending", "approved", "rejected", "cancelled"}


def _db_path() -> str:
    """Resolve DB location from env while keeping local default behavior."""
    configured_path = (os.getenv("SOLAR_SHARE_OPS_DB_PATH") or "").strip()
    return configured_path or DEFAULT_DB_PATH


def _ensure_parent_directory(path: str) -> None:
    """Create parent directories for configured SQLite path when needed."""
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert sqlite row objects to plain dictionaries."""
    return {key: row[key] for key in row.keys()}


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    """Add columns safely on existing local databases without destructive migrations."""
    existing_columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name in existing_columns:
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def auth_identity_user_key(user_id: str) -> str:
    """Map authenticated users to a deterministic internal subscription key."""
    return f"auth:{user_id}"


def _normalize_invoice_status(raw_status: Optional[str]) -> str:
    """Normalize lifecycle status to one of the supported billing states."""
    status = (raw_status or "").strip().lower()
    if status in INVOICE_STATUSES:
        return status
    return "issued"


def _build_invoice_pdf_bytes(
    invoice_id: str,
    month_label: str,
    utility_credits: float,
    payment_due: float,
    savings: float,
    billing_status: str,
) -> bytes:
    """Build branded invoice PDF artifact with customer-facing line-item breakdown."""

    def _pdf_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = [
        "SolarShare Community Solar Invoice",
        "No upfront cost | Cancel anytime | No installation required",
        "",
        f"Invoice ID: {invoice_id}",
        f"Billing Month: {month_label}",
        f"Invoice Status: {billing_status.upper()}",
        "Region: New York Community Solar Program",
        "",
        "Line Items",
        f"1) Utility Bill Credits Applied ......... ${utility_credits:.2f}",
        f"2) SolarShare Subscription Payment ...... ${payment_due:.2f}",
        f"3) Net Customer Savings ................. ${savings:.2f}",
        "",
        "Billing Explanation",
        "Step 1: Solar projects generate bill credits.",
        "Step 2: Utility applies credits to your account.",
        "Step 3: You pay SolarShare a discounted amount.",
        "",
        "Payment Support",
        "For billing questions contact billing@solarshare.com",
    ]
    stream_lines = ["BT", "/F1 12 Tf", "72 760 Td"]
    for index, line in enumerate(lines):
        if index > 0:
            stream_lines.append("0 -18 Td")
        stream_lines.append(f"({_pdf_escape(line)}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines) + "\n"
    stream_bytes = stream.encode("ascii", errors="replace")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii") + stream_bytes + b"endstream",
    ]

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets: list[int] = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(obj)
        output.write(b"\nendobj\n")
    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return output.getvalue()


def init_project_store() -> None:
    """Create and seed project/subscription/billing tables for production realism."""
    path = _db_path()
    _ensure_parent_directory(path)
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                created_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL,
                device_name TEXT,
                user_agent TEXT,
                ip_address TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                revoked_reason TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS solar_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT UNIQUE NOT NULL,
                region TEXT NOT NULL,
                utility TEXT NOT NULL,
                capacity_kw REAL NOT NULL,
                subscribers_count INTEGER NOT NULL DEFAULT 0,
                available_slots INTEGER NOT NULL DEFAULT 0,
                billing_model TEXT NOT NULL DEFAULT 'consolidated',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                user_key TEXT UNIQUE NOT NULL,
                user_id TEXT,
                project_id INTEGER NOT NULL,
                subscription_size_kw REAL NOT NULL,
                subscription_start_date TEXT NOT NULL,
                monthly_generation_share REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES solar_projects(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS credit_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id TEXT NOT NULL,
                month_label TEXT NOT NULL,
                credit_value REAL NOT NULL,
                payment_amount REAL NOT NULL,
                savings REAL NOT NULL,
                rollover_balance_kwh REAL NOT NULL,
                billing_status TEXT NOT NULL DEFAULT 'issued',
                invoice_id TEXT,
                explanation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(subscription_id, month_label)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                subscription_id TEXT NOT NULL,
                month_label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'issued',
                billing_status TEXT NOT NULL DEFAULT 'issued',
                utility_credits REAL NOT NULL,
                payment_due REAL NOT NULL,
                savings REAL NOT NULL,
                rollover_balance_kwh REAL NOT NULL,
                explanation TEXT NOT NULL,
                pdf_blob BLOB NOT NULL,
                payment_provider TEXT,
                payment_transaction_id TEXT,
                payment_status_message TEXT,
                created_at TEXT NOT NULL,
                issued_at TEXT,
                paid_at TEXT,
                failed_at TEXT,
                UNIQUE(subscription_id, month_label)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_status_requests (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                requested_by_user_id TEXT NOT NULL,
                current_status TEXT NOT NULL,
                requested_status TEXT NOT NULL,
                reason TEXT,
                state TEXT NOT NULL DEFAULT 'pending',
                reviewed_by_user_id TEXT,
                review_note TEXT,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS waitlist (
                id TEXT PRIMARY KEY,
                user_key TEXT,
                region TEXT,
                utility TEXT,
                monthly_usage_kwh REAL NOT NULL,
                position_estimate INTEGER NOT NULL,
                expected_timeline TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(connection, "subscriptions", "user_id", "TEXT")
        _ensure_column(connection, "credit_ledger", "billing_status", "TEXT NOT NULL DEFAULT 'issued'")
        _ensure_column(connection, "credit_ledger", "invoice_id", "TEXT")
        _ensure_column(connection, "invoices", "payment_provider", "TEXT")
        _ensure_column(connection, "invoices", "payment_transaction_id", "TEXT")
        _ensure_column(connection, "invoices", "payment_status_message", "TEXT")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_refresh_hash ON auth_sessions(refresh_token_hash)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_invoice_status_requests_state ON invoice_status_requests(state)")

        existing = connection.execute("SELECT COUNT(*) AS count FROM solar_projects").fetchone()["count"]
        if int(existing) == 0:
            connection.executemany(
                """
                INSERT INTO solar_projects
                (project_name, region, utility, capacity_kw, subscribers_count, available_slots, billing_model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(*project, created_at) for project in SEED_PROJECTS],
            )
        connection.commit()


def list_matching_projects(region: Optional[str], utility: Optional[str]) -> List[Dict[str, Any]]:
    """Return active projects filtered by region and utility for eligibility decisions."""
    init_project_store()
    normalized_region = (region or "").strip()
    normalized_utility = (utility or "").strip()

    query = """
        SELECT id, project_name, region, utility, capacity_kw, subscribers_count, available_slots, billing_model
        FROM solar_projects
        WHERE is_active = 1
    """
    params: list[Any] = []

    if normalized_region:
        query += " AND region = ?"
        params.append(normalized_region)
    if normalized_utility:
        query += " AND utility = ?"
        params.append(normalized_utility)

    query += " ORDER BY available_slots DESC, subscribers_count ASC"

    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, tuple(params)).fetchall()
    return [_row_to_dict(row) for row in rows]


def create_user(email: str, password_hash: str, role: str = "customer") -> Dict[str, Any]:
    """Create a new local auth user and return the stored profile."""
    init_project_store()
    now_iso = datetime.now(timezone.utc).isoformat()
    user_id = uuid4().hex
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            INSERT INTO users (id, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, email.strip().lower(), password_hash, role.strip().lower() or "customer", now_iso),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT id, email, role, created_at, last_login_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return _row_to_dict(row)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch user profile by normalized email."""
    normalized = email.strip().lower()
    if not normalized:
        return None
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, email, password_hash, role, created_at, last_login_at
            FROM users
            WHERE email = ?
            """,
            (normalized,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch user profile by primary key."""
    normalized = (user_id or "").strip()
    if not normalized:
        return None
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, email, role, created_at, last_login_at
            FROM users
            WHERE id = ?
            """,
            (normalized,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def mark_user_login(user_id: str) -> None:
    """Update user login timestamp for basic account lifecycle auditing."""
    normalized = (user_id or "").strip()
    if not normalized:
        return
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.execute(
            """
            UPDATE users
            SET last_login_at = ?
            WHERE id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), normalized),
        )
        connection.commit()


def create_auth_session(
    user_id: str,
    refresh_token_hash: str,
    expires_at: str,
    device_name: Optional[str],
    user_agent: Optional[str],
    ip_address: Optional[str],
) -> Dict[str, Any]:
    """Persist login session metadata used for refresh and revocation controls."""
    init_project_store()
    now_iso = datetime.now(timezone.utc).isoformat()
    session_id = uuid4().hex
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            INSERT INTO auth_sessions
            (id, user_id, refresh_token_hash, device_name, user_agent, ip_address, created_at, last_seen_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id.strip(),
                refresh_token_hash.strip(),
                (device_name or "").strip() or None,
                (user_agent or "").strip() or None,
                (ip_address or "").strip() or None,
                now_iso,
                now_iso,
                expires_at.strip(),
            ),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT id, user_id, device_name, user_agent, ip_address, created_at, last_seen_at, expires_at, revoked_at, revoked_reason
            FROM auth_sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
    return _row_to_dict(row)


def get_auth_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Return auth session record by ID."""
    normalized = (session_id or "").strip()
    if not normalized:
        return None
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, user_id, refresh_token_hash, device_name, user_agent, ip_address, created_at, last_seen_at, expires_at, revoked_at, revoked_reason
            FROM auth_sessions
            WHERE id = ?
            """,
            (normalized,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_auth_session_by_refresh_hash(refresh_token_hash: str) -> Optional[Dict[str, Any]]:
    """Resolve session by refresh token hash for token rotation."""
    normalized = (refresh_token_hash or "").strip()
    if not normalized:
        return None
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, user_id, refresh_token_hash, device_name, user_agent, ip_address, created_at, last_seen_at, expires_at, revoked_at, revoked_reason
            FROM auth_sessions
            WHERE refresh_token_hash = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def touch_auth_session(session_id: str) -> None:
    """Update session last-seen timestamp after successful authenticated use."""
    normalized = (session_id or "").strip()
    if not normalized:
        return
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.execute(
            """
            UPDATE auth_sessions
            SET last_seen_at = ?
            WHERE id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), normalized),
        )
        connection.commit()


def rotate_auth_session(session_id: str, refresh_token_hash: str, expires_at: str) -> bool:
    """Rotate session refresh hash and extend expiry during refresh flows."""
    normalized_id = (session_id or "").strip()
    normalized_hash = (refresh_token_hash or "").strip()
    normalized_expires_at = (expires_at or "").strip()
    if not normalized_id or not normalized_hash or not normalized_expires_at:
        return False
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        cursor = connection.execute(
            """
            UPDATE auth_sessions
            SET refresh_token_hash = ?, expires_at = ?, last_seen_at = ?
            WHERE id = ? AND revoked_at IS NULL
            """,
            (
                normalized_hash,
                normalized_expires_at,
                datetime.now(timezone.utc).isoformat(),
                normalized_id,
            ),
        )
        connection.commit()
    return cursor.rowcount > 0


def revoke_auth_session(session_id: str, reason: str = "logout") -> bool:
    """Revoke one session so future access/refresh checks fail."""
    normalized_id = (session_id or "").strip()
    if not normalized_id:
        return False
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        cursor = connection.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = COALESCE(revoked_at, ?), revoked_reason = COALESCE(revoked_reason, ?)
            WHERE id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                (reason or "").strip() or "logout",
                normalized_id,
            ),
        )
        connection.commit()
    return cursor.rowcount > 0


def revoke_other_auth_sessions(user_id: str, keep_session_id: Optional[str]) -> int:
    """Revoke all other sessions for a user to support account-wide sign-out."""
    normalized_user_id = (user_id or "").strip()
    keep_id = (keep_session_id or "").strip()
    if not normalized_user_id:
        return 0
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        if keep_id:
            cursor = connection.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = COALESCE(revoked_at, ?), revoked_reason = COALESCE(revoked_reason, 'logout_all')
                WHERE user_id = ? AND id != ? AND revoked_at IS NULL
                """,
                (datetime.now(timezone.utc).isoformat(), normalized_user_id, keep_id),
            )
        else:
            cursor = connection.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = COALESCE(revoked_at, ?), revoked_reason = COALESCE(revoked_reason, 'logout_all')
                WHERE user_id = ? AND revoked_at IS NULL
                """,
                (datetime.now(timezone.utc).isoformat(), normalized_user_id),
            )
        connection.commit()
    return int(cursor.rowcount)


def list_auth_sessions_for_user(user_id: str) -> List[Dict[str, Any]]:
    """List a user's sessions for device/session controls in dashboard settings."""
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        return []
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, user_id, device_name, user_agent, ip_address, created_at, last_seen_at, expires_at, revoked_at, revoked_reason
            FROM auth_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (normalized_user_id,),
        ).fetchall()
    sessions = [_row_to_dict(row) for row in rows]
    now_iso = datetime.now(timezone.utc).isoformat()
    for session in sessions:
        session["is_active"] = bool(not session.get("revoked_at") and str(session.get("expires_at") or "") > now_iso)
    return sessions


def update_user_role(user_id: str, role: str) -> bool:
    """Update user role for RBAC bootstrap and admin management flows."""
    normalized_user_id = (user_id or "").strip()
    normalized_role = (role or "").strip().lower()
    if normalized_role not in {"customer", "developer", "admin"}:
        return False
    if not normalized_user_id:
        return False
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET role = ?
            WHERE id = ?
            """,
            (normalized_role, normalized_user_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def get_subscription_for_user(user_key: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch existing user subscription and linked project metadata."""
    normalized_user_key = (user_key or "").strip()
    if not normalized_user_key:
        return None

    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                s.id,
                s.user_key,
                s.user_id,
                s.project_id,
                s.subscription_size_kw,
                s.subscription_start_date,
                s.monthly_generation_share,
                p.project_name,
                p.region,
                p.utility,
                p.capacity_kw,
                p.available_slots,
                p.billing_model
            FROM subscriptions s
            JOIN solar_projects p ON p.id = s.project_id
            WHERE s.user_key = ?
            """,
            (normalized_user_key,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_subscription_for_user_id(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch existing subscription for authenticated users."""
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        return None
    return get_subscription_for_user(auth_identity_user_key(normalized_user_id))


def assign_project_to_user(
    user_key: Optional[str],
    region: Optional[str],
    utility: Optional[str],
    subscription_size_kw: float,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Assign a user to the best available project and reduce available slots atomically."""
    normalized_user_key = (user_key or "").strip()
    if not normalized_user_key:
        return None

    init_project_store()
    existing = get_subscription_for_user(normalized_user_key)
    if existing:
        return existing

    normalized_region = (region or "").strip()
    normalized_utility = (utility or "").strip()
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id and normalized_user_key.startswith("auth:"):
        normalized_user_id = normalized_user_key.replace("auth:", "", 1).strip()
    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT id, project_name, region, utility, capacity_kw, subscribers_count, available_slots, billing_model
            FROM solar_projects
            WHERE is_active = 1
              AND region = ?
              AND utility = ?
              AND available_slots > 0
            ORDER BY available_slots DESC, subscribers_count ASC
            LIMIT 1
            """,
            (normalized_region, normalized_utility),
        ).fetchone()

        if row is None:
            row = connection.execute(
                """
                SELECT id, project_name, region, utility, capacity_kw, subscribers_count, available_slots, billing_model
                FROM solar_projects
                WHERE is_active = 1
                  AND region = ?
                  AND available_slots > 0
                ORDER BY available_slots DESC, subscribers_count ASC
                LIMIT 1
                """,
                (normalized_region,),
            ).fetchone()

        if row is None:
            connection.rollback()
            return None

        project_id = int(row["id"])
        updated_slots = max(int(row["available_slots"]) - 1, 0)
        updated_subscribers = int(row["subscribers_count"]) + 1

        connection.execute(
            """
            UPDATE solar_projects
            SET available_slots = ?, subscribers_count = ?
            WHERE id = ?
            """,
            (updated_slots, updated_subscribers, project_id),
        )

        subscription_id = uuid4().hex
        monthly_generation_share = max(subscription_size_kw / float(row["capacity_kw"]), 0.0)
        connection.execute(
            """
            INSERT INTO subscriptions
            (id, user_key, user_id, project_id, subscription_size_kw, subscription_start_date, monthly_generation_share, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subscription_id,
                normalized_user_key,
                normalized_user_id or None,
                project_id,
                float(subscription_size_kw),
                date.today().isoformat(),
                monthly_generation_share,
                created_at,
            ),
        )
        connection.commit()

    return get_subscription_for_user(normalized_user_key)


def add_user_to_waitlist(
    user_key: Optional[str],
    region: Optional[str],
    utility: Optional[str],
    monthly_usage_kwh: float,
) -> Dict[str, Any]:
    """Persist waitlist entry and return current position estimate."""
    init_project_store()
    normalized_region = (region or "").strip() or "Unknown"
    normalized_utility = (utility or "").strip() or "Unknown"
    normalized_user_key = (user_key or "").strip() or None
    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        count_row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM waitlist
            WHERE region = ? AND utility = ?
            """,
            (normalized_region, normalized_utility),
        ).fetchone()
        position = int(count_row["count"]) + 1
        timeline = "Estimated availability: 6-12 weeks"
        connection.execute(
            """
            INSERT INTO waitlist
            (id, user_key, region, utility, monthly_usage_kwh, position_estimate, expected_timeline, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                normalized_user_key,
                normalized_region,
                normalized_utility,
                float(monthly_usage_kwh),
                position,
                timeline,
                created_at,
            ),
        )
        connection.commit()
    return {"position_estimate": position, "expected_timeline": timeline}


def store_credit_ledger(subscription_id: str, monthly_breakdown: List[Dict[str, Any]]) -> None:
    """Persist per-month billing outputs and invoice artifacts for dashboard history."""
    if not subscription_id:
        return
    init_project_store()
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        for month in monthly_breakdown:
            month_label = str(month["month"])
            billing_status = _normalize_invoice_status(str(month.get("billing_status") or "issued"))
            invoice_id = f"{subscription_id}:{month_label.lower()}"
            credit_value = float(month["credit_value"])
            payment_amount = float(month["payment"])
            savings = float(month["savings"])
            rollover_balance = float(month["rollover_balance"])
            explanation = str(month.get("explanation") or "Monthly community-solar credit cycle")
            invoice_pdf = _build_invoice_pdf_bytes(
                invoice_id=invoice_id,
                month_label=month_label,
                utility_credits=credit_value,
                payment_due=payment_amount,
                savings=savings,
                billing_status=billing_status,
            )

            connection.execute(
                """
                INSERT INTO invoices
                (id, subscription_id, month_label, status, billing_status, utility_credits, payment_due, savings, rollover_balance_kwh, explanation, pdf_blob, created_at, issued_at, paid_at, failed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subscription_id, month_label)
                DO UPDATE SET
                    utility_credits=excluded.utility_credits,
                    payment_due=excluded.payment_due,
                    savings=excluded.savings,
                    rollover_balance_kwh=excluded.rollover_balance_kwh,
                    explanation=excluded.explanation,
                    pdf_blob=excluded.pdf_blob,
                    billing_status=CASE
                        WHEN invoices.status IN ('paid', 'failed') THEN invoices.billing_status
                        ELSE excluded.billing_status
                    END,
                    status=CASE
                        WHEN invoices.status IN ('paid', 'failed') THEN invoices.status
                        ELSE excluded.status
                    END,
                    issued_at=CASE
                        WHEN invoices.status IN ('paid', 'failed') THEN invoices.issued_at
                        WHEN excluded.status = 'issued' THEN COALESCE(invoices.issued_at, excluded.issued_at)
                        ELSE invoices.issued_at
                    END,
                    paid_at=CASE
                        WHEN invoices.status = 'paid' THEN invoices.paid_at
                        ELSE excluded.paid_at
                    END,
                    failed_at=CASE
                        WHEN invoices.status = 'failed' THEN invoices.failed_at
                        ELSE excluded.failed_at
                    END
                """,
                (
                    invoice_id,
                    subscription_id,
                    month_label,
                    billing_status,
                    billing_status,
                    credit_value,
                    payment_amount,
                    savings,
                    rollover_balance,
                    explanation,
                    invoice_pdf,
                    created_at,
                    created_at if billing_status == "issued" else None,
                    created_at if billing_status == "paid" else None,
                    created_at if billing_status == "failed" else None,
                ),
            )

            invoice_row = connection.execute(
                """
                SELECT id, status
                FROM invoices
                WHERE subscription_id = ? AND month_label = ?
                """,
                (subscription_id, month_label),
            ).fetchone()
            persisted_invoice_id = str(invoice_row["id"]) if invoice_row else invoice_id
            persisted_status = str(invoice_row["status"]) if invoice_row else billing_status

            connection.execute(
                """
                INSERT INTO credit_ledger
                (subscription_id, month_label, credit_value, payment_amount, savings, rollover_balance_kwh, billing_status, invoice_id, explanation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subscription_id, month_label)
                DO UPDATE SET
                    credit_value=excluded.credit_value,
                    payment_amount=excluded.payment_amount,
                    savings=excluded.savings,
                    rollover_balance_kwh=excluded.rollover_balance_kwh,
                    billing_status=excluded.billing_status,
                    invoice_id=excluded.invoice_id,
                    explanation=excluded.explanation,
                    created_at=excluded.created_at
                """,
                (
                    subscription_id,
                    month_label,
                    credit_value,
                    payment_amount,
                    savings,
                    rollover_balance,
                    persisted_status,
                    persisted_invoice_id,
                    explanation,
                    created_at,
                ),
            )
        connection.commit()


def _load_billing_history(subscription_id: str) -> list[dict[str, Any]]:
    """Fetch billing lifecycle history with invoice download metadata."""
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                i.id,
                i.month_label,
                i.status,
                i.billing_status,
                i.utility_credits,
                i.payment_due,
                i.savings,
                i.rollover_balance_kwh,
                i.explanation,
                i.payment_provider,
                i.payment_transaction_id,
                i.payment_status_message,
                i.created_at,
                i.issued_at,
                i.paid_at,
                i.failed_at
            FROM invoices i
            WHERE i.subscription_id = ?
            """,
            (subscription_id,),
        ).fetchall()
    history = [
        {
            "invoice_id": row["id"],
            "month": row["month_label"],
            "status": row["status"],
            "billing_status": row["billing_status"],
            "utility_credits": float(row["utility_credits"]),
            "payment_due": float(row["payment_due"]),
            "savings": float(row["savings"]),
            "rollover_balance": float(row["rollover_balance_kwh"]),
            "explanation": row["explanation"],
            "payment_provider": row["payment_provider"],
            "payment_transaction_id": row["payment_transaction_id"],
            "payment_status_message": row["payment_status_message"],
            "created_at": row["created_at"],
            "issued_at": row["issued_at"],
            "paid_at": row["paid_at"],
            "failed_at": row["failed_at"],
            "download_path": f"/invoices/{row['id']}/download",
        }
        for row in rows
    ]
    history.sort(key=lambda item: MONTH_ORDER.get(str(item["month"]), 99))
    return history


def list_billing_history_for_user(user_key: Optional[str]) -> list[dict[str, Any]]:
    """Return invoice history for compatibility users identified by user_key."""
    subscription = get_subscription_for_user(user_key)
    if not subscription:
        return []
    return _load_billing_history(str(subscription["id"]))


def list_billing_history_for_user_id(user_id: Optional[str]) -> list[dict[str, Any]]:
    """Return invoice history for authenticated users."""
    subscription = get_subscription_for_user_id(user_id)
    if not subscription:
        return []
    return _load_billing_history(str(subscription["id"]))


def get_invoice_for_user(user_key: Optional[str], invoice_id: str) -> Optional[Dict[str, Any]]:
    """Return invoice metadata for a user-scoped invoice access check."""
    normalized_invoice_id = (invoice_id or "").strip()
    normalized_user_key = (user_key or "").strip()
    if not normalized_invoice_id or not normalized_user_key:
        return None
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                i.id,
                i.subscription_id,
                i.month_label,
                i.status,
                i.billing_status,
                i.utility_credits,
                i.payment_due,
                i.savings,
                i.rollover_balance_kwh,
                i.explanation,
                i.payment_provider,
                i.payment_transaction_id,
                i.payment_status_message,
                i.created_at
            FROM invoices i
            JOIN subscriptions s ON s.id = i.subscription_id
            WHERE i.id = ? AND s.user_key = ?
            """,
            (normalized_invoice_id, normalized_user_key),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_invoice_for_user_id(user_id: Optional[str], invoice_id: str) -> Optional[Dict[str, Any]]:
    """Return invoice metadata for authenticated user access checks."""
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        return None
    return get_invoice_for_user(auth_identity_user_key(normalized_user_id), invoice_id=invoice_id)


def get_invoice_pdf_for_user(user_key: Optional[str], invoice_id: str) -> Optional[Dict[str, Any]]:
    """Return invoice PDF bytes only when invoice belongs to the provided user key."""
    normalized_invoice_id = (invoice_id or "").strip()
    normalized_user_key = (user_key or "").strip()
    if not normalized_invoice_id or not normalized_user_key:
        return None
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT i.id, i.month_label, i.status, i.billing_status, i.pdf_blob
            FROM invoices i
            JOIN subscriptions s ON s.id = i.subscription_id
            WHERE i.id = ? AND s.user_key = ?
            """,
            (normalized_invoice_id, normalized_user_key),
        ).fetchone()
    if not row:
        return None
    return {
        "invoice_id": row["id"],
        "month": row["month_label"],
        "status": row["status"],
        "billing_status": row["billing_status"],
        "pdf_blob": row["pdf_blob"],
    }


def get_invoice_pdf_for_user_id(user_id: Optional[str], invoice_id: str) -> Optional[Dict[str, Any]]:
    """Return invoice PDF bytes for authenticated users."""
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        return None
    return get_invoice_pdf_for_user(auth_identity_user_key(normalized_user_id), invoice_id=invoice_id)


def _update_invoice_status_by_id(
    connection: sqlite3.Connection,
    invoice_id: str,
    status: str,
    payment_provider: Optional[str] = None,
    payment_transaction_id: Optional[str] = None,
    payment_status_message: Optional[str] = None,
) -> bool:
    """Apply invoice status mutation and sync ledger row in one transaction."""
    normalized_invoice_id = (invoice_id or "").strip()
    normalized_status = _normalize_invoice_status(status)
    if not normalized_invoice_id:
        return False
    now_iso = datetime.now(timezone.utc).isoformat()
    connection.row_factory = sqlite3.Row
    invoice_row = connection.execute(
        """
        SELECT id, subscription_id, month_label
        FROM invoices
        WHERE id = ?
        """,
        (normalized_invoice_id,),
    ).fetchone()
    if not invoice_row:
        return False
    connection.execute(
        """
        UPDATE invoices
        SET
            status = ?,
            billing_status = ?,
            payment_provider = COALESCE(?, payment_provider),
            payment_transaction_id = COALESCE(?, payment_transaction_id),
            payment_status_message = COALESCE(?, payment_status_message),
            issued_at = CASE WHEN ? = 'issued' THEN COALESCE(issued_at, ?) ELSE issued_at END,
            paid_at = CASE WHEN ? = 'paid' THEN COALESCE(paid_at, ?) ELSE paid_at END,
            failed_at = CASE WHEN ? = 'failed' THEN COALESCE(failed_at, ?) ELSE failed_at END
        WHERE id = ?
        """,
        (
            normalized_status,
            normalized_status,
            (payment_provider or "").strip() or None,
            (payment_transaction_id or "").strip() or None,
            (payment_status_message or "").strip() or None,
            normalized_status,
            now_iso,
            normalized_status,
            now_iso,
            normalized_status,
            now_iso,
            normalized_invoice_id,
        ),
    )
    connection.execute(
        """
        UPDATE credit_ledger
        SET billing_status = ?, created_at = ?
        WHERE subscription_id = ? AND month_label = ?
        """,
        (
            normalized_status,
            now_iso,
            invoice_row["subscription_id"],
            invoice_row["month_label"],
        ),
    )
    return True


def update_invoice_status_for_user(
    user_key: Optional[str],
    invoice_id: str,
    status: str,
    payment_provider: Optional[str] = None,
    payment_transaction_id: Optional[str] = None,
    payment_status_message: Optional[str] = None,
) -> bool:
    """Update invoice lifecycle status and sync ledger billing status for a user's invoice."""
    normalized_user_key = (user_key or "").strip()
    normalized_invoice_id = (invoice_id or "").strip()
    if not normalized_user_key or not normalized_invoice_id:
        return False
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        exists = connection.execute(
            """
            SELECT i.id
            FROM invoices i
            JOIN subscriptions s ON s.id = i.subscription_id
            WHERE i.id = ? AND s.user_key = ?
            """,
            (normalized_invoice_id, normalized_user_key),
        ).fetchone()
        if not exists:
            return False
        updated = _update_invoice_status_by_id(
            connection=connection,
            invoice_id=normalized_invoice_id,
            status=status,
            payment_provider=payment_provider,
            payment_transaction_id=payment_transaction_id,
            payment_status_message=payment_status_message,
        )
        connection.commit()
        return updated


def update_invoice_status_for_user_id(
    user_id: Optional[str],
    invoice_id: str,
    status: str,
    payment_provider: Optional[str] = None,
    payment_transaction_id: Optional[str] = None,
    payment_status_message: Optional[str] = None,
) -> bool:
    """Update invoice status for authenticated users."""
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        return False
    return update_invoice_status_for_user(
        auth_identity_user_key(normalized_user_id),
        invoice_id=invoice_id,
        status=status,
        payment_provider=payment_provider,
        payment_transaction_id=payment_transaction_id,
        payment_status_message=payment_status_message,
    )


def update_invoice_status_as_admin(
    invoice_id: str,
    status: str,
    payment_provider: Optional[str] = None,
    payment_transaction_id: Optional[str] = None,
    payment_status_message: Optional[str] = None,
) -> bool:
    """Update invoice status without user ownership checks for admin moderation."""
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        updated = _update_invoice_status_by_id(
            connection=connection,
            invoice_id=invoice_id,
            status=status,
            payment_provider=payment_provider,
            payment_transaction_id=payment_transaction_id,
            payment_status_message=payment_status_message,
        )
        connection.commit()
    return updated


def create_invoice_status_request(
    user_id: str,
    invoice_id: str,
    requested_status: str,
    reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create a pending invoice status request for admin moderation."""
    normalized_user_id = (user_id or "").strip()
    normalized_invoice_id = (invoice_id or "").strip()
    normalized_requested = _normalize_invoice_status(requested_status)
    if not normalized_user_id or not normalized_invoice_id:
        return None
    request_id = uuid4().hex
    now_iso = datetime.now(timezone.utc).isoformat()
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        invoice_row = connection.execute(
            """
            SELECT i.id, i.status
            FROM invoices i
            JOIN subscriptions s ON s.id = i.subscription_id
            WHERE i.id = ? AND s.user_id = ?
            """,
            (normalized_invoice_id, normalized_user_id),
        ).fetchone()
        if not invoice_row:
            return None
        connection.execute(
            """
            INSERT INTO invoice_status_requests
            (id, invoice_id, requested_by_user_id, current_status, requested_status, reason, state, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                request_id,
                normalized_invoice_id,
                normalized_user_id,
                str(invoice_row["status"]),
                normalized_requested,
                (reason or "").strip() or None,
                now_iso,
            ),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT id, invoice_id, requested_by_user_id, current_status, requested_status, reason, state, reviewed_by_user_id, review_note, created_at, reviewed_at
            FROM invoice_status_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_invoice_status_requests(state: Optional[str] = None) -> List[Dict[str, Any]]:
    """List invoice status requests for admin moderation screens."""
    normalized_state = (state or "").strip().lower()
    init_project_store()
    query = """
        SELECT id, invoice_id, requested_by_user_id, current_status, requested_status, reason, state, reviewed_by_user_id, review_note, created_at, reviewed_at
        FROM invoice_status_requests
    """
    params: list[Any] = []
    if normalized_state:
        query += " WHERE state = ?"
        params.append(normalized_state)
    query += " ORDER BY created_at DESC"
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, tuple(params)).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_invoice_status_requests_for_user(user_id: str) -> List[Dict[str, Any]]:
    """List status requests created by one customer for dashboard visibility."""
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        return []
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, invoice_id, requested_by_user_id, current_status, requested_status, reason, state, reviewed_by_user_id, review_note, created_at, reviewed_at
            FROM invoice_status_requests
            WHERE requested_by_user_id = ?
            ORDER BY created_at DESC
            """,
            (normalized_user_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def review_invoice_status_request(
    request_id: str,
    reviewer_user_id: str,
    decision: str,
    review_note: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Approve or reject a pending status request and apply mutation when approved."""
    normalized_request_id = (request_id or "").strip()
    normalized_reviewer = (reviewer_user_id or "").strip()
    normalized_decision = (decision or "").strip().lower()
    if normalized_decision not in {"approve", "reject"}:
        return None
    if not normalized_request_id or not normalized_reviewer:
        return None
    now_iso = datetime.now(timezone.utc).isoformat()
    init_project_store()
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, invoice_id, requested_status, state
            FROM invoice_status_requests
            WHERE id = ?
            """,
            (normalized_request_id,),
        ).fetchone()
        if not row or row["state"] != "pending":
            return None
        new_state = "approved" if normalized_decision == "approve" else "rejected"
        connection.execute(
            """
            UPDATE invoice_status_requests
            SET state = ?, reviewed_by_user_id = ?, review_note = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (
                new_state,
                normalized_reviewer,
                (review_note or "").strip() or None,
                now_iso,
                normalized_request_id,
            ),
        )
        if new_state == "approved":
            _update_invoice_status_by_id(
                connection=connection,
                invoice_id=str(row["invoice_id"]),
                status=str(row["requested_status"]),
                payment_status_message="Updated via admin moderation workflow",
            )
        connection.commit()
        result = connection.execute(
            """
            SELECT id, invoice_id, requested_by_user_id, current_status, requested_status, reason, state, reviewed_by_user_id, review_note, created_at, reviewed_at
            FROM invoice_status_requests
            WHERE id = ?
            """,
            (normalized_request_id,),
        ).fetchone()
    return _row_to_dict(result) if result else None


def load_dashboard_data(user_key: Optional[str]) -> Dict[str, Any]:
    """Load dashboard-ready aggregates from persisted subscription and ledger tables."""
    normalized_user_key = (user_key or "").strip()
    if not normalized_user_key:
        return {
            "user_key": None,
            "has_subscription": False,
            "total_savings": 0.0,
            "rollover_credits": 0.0,
            "subscription_size_kw": 0.0,
            "project_info": None,
            "utility": None,
            "region": None,
            "monthly_savings": [],
            "billing_history": [],
            "year_to_date_savings": 0.0,
        }

    subscription = get_subscription_for_user(normalized_user_key)
    if not subscription:
        return {
            "user_key": normalized_user_key,
            "has_subscription": False,
            "total_savings": 0.0,
            "rollover_credits": 0.0,
            "subscription_size_kw": 0.0,
            "project_info": None,
            "utility": None,
            "region": None,
            "monthly_savings": [],
            "billing_history": [],
            "year_to_date_savings": 0.0,
        }

    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        ledger_rows = connection.execute(
            """
            SELECT month_label, savings, rollover_balance_kwh
            FROM credit_ledger
            WHERE subscription_id = ?
            """,
            (subscription["id"],),
        ).fetchall()

    monthly = [
        {
            "month": row["month_label"],
            "savings": float(row["savings"]),
            "rollover_balance": float(row["rollover_balance_kwh"]),
        }
        for row in ledger_rows
    ]
    monthly.sort(key=lambda item: MONTH_ORDER.get(str(item["month"]), 99))

    total_savings = round(sum(item["savings"] for item in monthly), 2)
    rollover_credits = round(monthly[-1]["rollover_balance"], 2) if monthly else 0.0
    billing_history = _load_billing_history(str(subscription["id"]))

    return {
        "user_key": normalized_user_key,
        "has_subscription": True,
        "total_savings": total_savings,
        "year_to_date_savings": total_savings,
        "rollover_credits": rollover_credits,
        "subscription_size_kw": round(float(subscription["subscription_size_kw"]), 3),
        "project_info": {
            "name": subscription["project_name"],
            "capacity_kw": round(float(subscription["capacity_kw"]), 2),
            "remaining_capacity": int(subscription["available_slots"]),
            "billing_model": subscription["billing_model"],
        },
        "subscription_start_date": subscription["subscription_start_date"],
        "monthly_generation_share": round(float(subscription["monthly_generation_share"]), 6),
        "utility": subscription["utility"],
        "region": subscription["region"],
        "monthly_savings": monthly,
        "billing_history": billing_history,
    }


def load_dashboard_data_for_user(user_id: Optional[str]) -> Dict[str, Any]:
    """Load dashboard payload for authenticated users mapped by user ID."""
    normalized_user_id = (user_id or "").strip()
    if not normalized_user_id:
        return load_dashboard_data(None)
    payload = load_dashboard_data(auth_identity_user_key(normalized_user_id))
    payload["user_id"] = normalized_user_id
    payload["auth_based"] = True
    payload["status_requests"] = list_invoice_status_requests_for_user(normalized_user_id)
    return payload
