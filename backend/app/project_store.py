"""Persistent project, subscription, waitlist, and billing-ledger storage for SolarShare."""

from __future__ import annotations

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


def init_project_store() -> None:
    """Create and seed project/subscription/billing tables for production realism."""
    path = _db_path()
    _ensure_parent_directory(path)
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
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
                explanation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(subscription_id, month_label)
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


def assign_project_to_user(
    user_key: Optional[str],
    region: Optional[str],
    utility: Optional[str],
    subscription_size_kw: float,
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
            (id, user_key, project_id, subscription_size_kw, subscription_start_date, monthly_generation_share, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subscription_id,
                normalized_user_key,
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
    """Persist per-month billing outputs so dashboards can show real history."""
    if not subscription_id:
        return
    init_project_store()
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path()) as connection:
        for month in monthly_breakdown:
            connection.execute(
                """
                INSERT INTO credit_ledger
                (subscription_id, month_label, credit_value, payment_amount, savings, rollover_balance_kwh, explanation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subscription_id, month_label)
                DO UPDATE SET
                    credit_value=excluded.credit_value,
                    payment_amount=excluded.payment_amount,
                    savings=excluded.savings,
                    rollover_balance_kwh=excluded.rollover_balance_kwh,
                    explanation=excluded.explanation,
                    created_at=excluded.created_at
                """,
                (
                    subscription_id,
                    str(month["month"]),
                    float(month["credit_value"]),
                    float(month["payment"]),
                    float(month["savings"]),
                    float(month["rollover_balance"]),
                    str(month.get("explanation") or "Monthly community-solar credit cycle"),
                    created_at,
                ),
            )
        connection.commit()


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

    return {
        "user_key": normalized_user_key,
        "has_subscription": True,
        "total_savings": total_savings,
        "rollover_credits": rollover_credits,
        "subscription_size_kw": round(float(subscription["subscription_size_kw"]), 3),
        "project_info": {
            "name": subscription["project_name"],
            "capacity_kw": round(float(subscription["capacity_kw"]), 2),
            "remaining_capacity": int(subscription["available_slots"]),
            "billing_model": subscription["billing_model"],
        },
        "utility": subscription["utility"],
        "region": subscription["region"],
        "monthly_savings": monthly,
    }
