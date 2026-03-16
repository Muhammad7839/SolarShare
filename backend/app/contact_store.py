"""SQLite-backed storage helpers for website contact inquiries."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def _db_path() -> str:
    """Resolve contact database path from env with a sensible local default."""
    return os.getenv("SOLAR_SHARE_CONTACT_DB_PATH", "./contact_inquiries.sqlite3")


def _ensure_parent_directory(path: str) -> None:
    """Create parent directories for configured SQLite path when needed."""
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


def init_contact_store() -> None:
    """Create contact inquiry table when the API process starts."""
    path = _db_path()
    _ensure_parent_directory(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contact_inquiries (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                interest TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def insert_contact_inquiry(name: str, email: str, interest: str, message: str) -> str:
    """Persist one contact inquiry and return stable inquiry id."""
    path = _db_path()
    init_contact_store()
    inquiry_id = uuid4().hex
    created_at = datetime.utcnow().isoformat()
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO contact_inquiries (id, name, email, interest, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (inquiry_id, name, email, interest, message, created_at),
        )
        connection.commit()
    return inquiry_id
