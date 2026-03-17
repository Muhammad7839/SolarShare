"""Operational SQLite helpers for analytics events and CRM-ready lead capture."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

DEFAULT_OPS_DB_PATH = str(Path(__file__).resolve().parents[1] / "ops_analytics.sqlite3")


def _db_path() -> str:
    """Resolve operations database path from env with local default."""
    return os.getenv("SOLAR_SHARE_OPS_DB_PATH", DEFAULT_OPS_DB_PATH)


def _ensure_parent_directory(path: str) -> None:
    """Create parent directories for configured SQLite path when needed."""
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


def init_ops_store() -> None:
    """Create analytics and lead tables at startup."""
    path = _db_path()
    _ensure_parent_directory(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                page TEXT,
                session_id TEXT,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS crm_leads (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                name TEXT NOT NULL,
                email_normalized TEXT NOT NULL,
                organization TEXT,
                message TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def _normalize_name(value: str) -> str:
    """Normalize display names for CRM consistency."""
    return " ".join(value.strip().split())


def _normalize_email(value: str) -> str:
    """Normalize email for dedupe-friendly lead indexing."""
    return value.strip().lower()


def insert_analytics_event(
    event_name: str,
    page: str | None,
    session_id: str | None,
    metadata: Dict[str, Any],
) -> None:
    """Persist one analytics event for funnel and diagnostics."""
    path = _db_path()
    init_ops_store()
    created_at = datetime.utcnow().isoformat()
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO analytics_events (event_name, page, session_id, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_name,
                page,
                session_id,
                json.dumps(metadata, separators=(",", ":"), ensure_ascii=True),
                created_at,
            ),
        )
        connection.commit()


def insert_crm_lead(
    source: str,
    name: str,
    email: str,
    organization: str | None,
    message: str,
    payload: Dict[str, Any],
) -> str:
    """Persist normalized CRM lead from contact or demo workflow."""
    path = _db_path()
    init_ops_store()
    lead_id = uuid4().hex
    created_at = datetime.utcnow().isoformat()
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO crm_leads
            (id, source, name, email_normalized, organization, message, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                source,
                _normalize_name(name),
                _normalize_email(email),
                (organization or "").strip() or None,
                " ".join(message.strip().split()),
                json.dumps(payload, separators=(",", ":"), ensure_ascii=True),
                created_at,
            ),
        )
        connection.commit()
    return lead_id


def get_admin_analytics_summary() -> Dict[str, Any]:
    """Return aggregate event and funnel metrics for the admin analytics page."""
    path = _db_path()
    init_ops_store()
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        event_rows = connection.execute(
            "SELECT event_name, COUNT(*) as count FROM analytics_events GROUP BY event_name"
        ).fetchall()
        recent_rows = connection.execute(
            "SELECT event_name, page, session_id, metadata_json, created_at FROM analytics_events ORDER BY id DESC LIMIT 40"
        ).fetchall()
        total_events = connection.execute("SELECT COUNT(*) as count FROM analytics_events").fetchone()["count"]
        total_leads = connection.execute("SELECT COUNT(*) as count FROM crm_leads").fetchone()["count"]

    by_event = {row["event_name"]: int(row["count"]) for row in event_rows}
    funnel_order = [
        "hero_cta_click",
        "comparison_step_location_complete",
        "comparison_step_usage_complete",
        "comparison_step_review_complete",
        "comparison_run",
        "comparison_success",
        "contact_submit",
        "demo_request_submit",
    ]
    dropoff: Dict[str, int] = {}
    previous_value = None
    for event_name in funnel_order:
        current_value = int(by_event.get(event_name, 0))
        if previous_value is not None:
            dropoff[event_name] = max(previous_value - current_value, 0)
        previous_value = current_value

    recent_events: List[Dict[str, Any]] = []
    for row in recent_rows:
        try:
            metadata = json.loads(row["metadata_json"])
        except Exception:
            metadata = {}
        recent_events.append(
            {
                "event_name": row["event_name"],
                "page": row["page"],
                "session_id": row["session_id"],
                "metadata": metadata,
                "created_at": row["created_at"],
            }
        )

    return {
        "totals": {"events": int(total_events), "leads": int(total_leads)},
        "by_event": by_event,
        "dropoff": dropoff,
        "recent_events": recent_events,
    }
