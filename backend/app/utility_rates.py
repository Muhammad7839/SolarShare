"""Utility-rate persistence and lookup helpers for realistic New York savings inputs."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.simulation_config import DEFAULT_NY_AVERAGE_RATE, DEFAULT_UTILITY_RATE_BY_REGION

DEFAULT_RATE_DB_PATH = str(Path(__file__).resolve().parents[1] / "ops_analytics.sqlite3")


@dataclass
class UtilityRateResult:
    """Resolved utility-rate payload returned to pricing and savings engines."""

    rate_used: float
    rate_source: str
    is_estimated: bool


SEED_RATES: list[tuple[str, str, float, str]] = [
    ("*", "NYC", DEFAULT_UTILITY_RATE_BY_REGION["NYC"], "NYC regional average override"),
    ("*", "Long Island", DEFAULT_UTILITY_RATE_BY_REGION["Long Island"], "Long Island regional average override"),
    ("*", "Upstate", DEFAULT_UTILITY_RATE_BY_REGION["Upstate"], "Upstate regional average override"),
    ("Con Edison", "NYC", 0.286, "NYS DPS blended residential estimate"),
    ("PSEG Long Island", "Long Island", 0.236, "PSEG LI blended residential estimate"),
    ("National Grid", "Upstate", 0.214, "National Grid NY blended residential estimate"),
    ("NYSEG", "Upstate", 0.205, "NYSEG blended residential estimate"),
    ("RG&E", "Upstate", 0.198, "RG&E blended residential estimate"),
    ("Central Hudson", "Upstate", 0.223, "Central Hudson blended residential estimate"),
]


def _db_path() -> str:
    """Resolve the shared operational DB path used for utility-rate storage."""
    configured_path = (os.getenv("SOLAR_SHARE_OPS_DB_PATH") or "").strip()
    return configured_path or DEFAULT_RATE_DB_PATH


def _ensure_parent_directory(path: str) -> None:
    """Create parent directories for configured SQLite path when needed."""
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


def init_utility_rate_store() -> None:
    """Create and seed the utility-rate table for deterministic lookup behavior."""
    path = _db_path()
    _ensure_parent_directory(path)
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS utility_rates (
                utility_name TEXT NOT NULL,
                region TEXT NOT NULL,
                avg_rate_per_kwh REAL NOT NULL,
                source TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                PRIMARY KEY (utility_name, region)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS utility_rate_refresh_jobs (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                records_updated INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                details TEXT
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_utility_rate_refresh_jobs_started_at ON utility_rate_refresh_jobs(started_at)")
        connection.executemany(
            """
            INSERT INTO utility_rates
            (utility_name, region, avg_rate_per_kwh, source, last_updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(utility_name, region)
            DO NOTHING
            """,
            [(utility_name, region, rate, source, now_iso) for utility_name, region, rate, source in SEED_RATES],
        )
        connection.commit()


def _upsert_rates(connection: sqlite3.Connection, rows: List[tuple[str, str, float, str]], now_iso: str) -> int:
    """Upsert utility rates and return the number of records processed."""
    if not rows:
        return 0
    connection.executemany(
        """
        INSERT INTO utility_rates
        (utility_name, region, avg_rate_per_kwh, source, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(utility_name, region)
        DO UPDATE SET
            avg_rate_per_kwh=excluded.avg_rate_per_kwh,
            source=excluded.source,
            last_updated=excluded.last_updated
        """,
        [(utility_name, region, rate, source, now_iso) for utility_name, region, rate, source in rows],
    )
    return len(rows)


def _load_external_rate_rows() -> tuple[List[tuple[str, str, float, str]], str]:
    """Load external rate rows from JSON URL or env payload when configured."""
    source_url = (os.getenv("SOLAR_SHARE_UTILITY_RATE_SOURCE_URL") or "").strip()
    raw_json = (os.getenv("SOLAR_SHARE_UTILITY_RATE_SOURCE_JSON") or "").strip()

    payload: Optional[Any] = None
    source_label = "seed"
    if source_url:
        with httpx.Client(timeout=6.0) as client:
            response = client.get(source_url)
            response.raise_for_status()
            payload = response.json()
        source_label = source_url
    elif raw_json:
        payload = json.loads(raw_json)
        source_label = "env:SOLAR_SHARE_UTILITY_RATE_SOURCE_JSON"

    if payload is None:
        return [], source_label

    if not isinstance(payload, list):
        raise ValueError("utility rate source payload must be a JSON array")

    rows: List[tuple[str, str, float, str]] = []
    for record in payload:
        if not isinstance(record, dict):
            continue
        utility_name = str(record.get("utility_name") or "").strip()
        region = str(record.get("region") or "").strip()
        source = str(record.get("source") or "External utility rate source").strip()
        rate_raw = record.get("avg_rate_per_kwh")
        if not utility_name or not region:
            continue
        try:
            rate = float(rate_raw)
        except (TypeError, ValueError):
            continue
        if rate <= 0:
            continue
        rows.append((utility_name, region, rate, source))
    return rows, source_label


def refresh_utility_rate_store() -> Dict[str, Any]:
    """Refresh utility rate table from external source when available, else seeded defaults."""
    init_utility_rate_store()
    path = _db_path()
    now_iso = datetime.now(timezone.utc).isoformat()
    refresh_id = f"refresh_{now_iso.replace(':', '').replace('-', '').replace('.', '')}"
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            INSERT INTO utility_rate_refresh_jobs (id, source, status, records_updated, started_at)
            VALUES (?, ?, 'running', 0, ?)
            """,
            (refresh_id, "pending", now_iso),
        )
        connection.commit()

        try:
            external_rows, source_label = _load_external_rate_rows()
            rows = external_rows or [(utility_name, region, rate, f"{source} (auto-refresh)") for utility_name, region, rate, source in SEED_RATES]
            records_updated = _upsert_rates(connection, rows, now_iso)
            status = "success"
            details = "Loaded external source." if external_rows else "External source unavailable; refreshed seeded defaults."
        except Exception as exc:
            records_updated = _upsert_rates(
                connection,
                [(utility_name, region, rate, f"{source} (fallback-refresh)") for utility_name, region, rate, source in SEED_RATES],
                now_iso,
            )
            source_label = "seed:fallback"
            status = "fallback"
            details = f"Refresh fallback used after source error: {exc}"

        completed_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            UPDATE utility_rate_refresh_jobs
            SET source = ?, status = ?, records_updated = ?, completed_at = ?, details = ?
            WHERE id = ?
            """,
            (source_label, status, int(records_updated), completed_at, details, refresh_id),
        )
        connection.commit()
    return {
        "refresh_id": refresh_id,
        "source": source_label,
        "status": status,
        "records_updated": int(records_updated),
        "started_at": now_iso,
        "completed_at": completed_at,
        "details": details,
    }


def list_rate_refresh_jobs(limit: int = 25) -> List[Dict[str, Any]]:
    """Return utility rate refresh history for timestamped operational audits."""
    init_utility_rate_store()
    safe_limit = max(min(int(limit), 200), 1)
    with sqlite3.connect(_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, source, status, records_updated, started_at, completed_at, details
            FROM utility_rate_refresh_jobs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def get_utility_rate(utility_name: str | None, region: str | None) -> UtilityRateResult:
    """Resolve utility-specific rates first, then fallback to documented NY average."""
    init_utility_rate_store()
    normalized_utility = (utility_name or "").strip()
    normalized_region = (region or "").strip()

    if not normalized_utility and not normalized_region:
        return UtilityRateResult(
            rate_used=DEFAULT_NY_AVERAGE_RATE,
            rate_source="NY average fallback",
            is_estimated=True,
        )

    with sqlite3.connect(_db_path()) as connection:
        row = connection.execute(
            """
            SELECT avg_rate_per_kwh, source
            FROM utility_rates
            WHERE utility_name = ? AND region = ?
            """,
            (normalized_utility, normalized_region),
        ).fetchone()
        if row:
            return UtilityRateResult(rate_used=float(row[0]), rate_source=str(row[1]), is_estimated=False)

        if normalized_utility:
            utility_only_row = connection.execute(
                """
                SELECT avg_rate_per_kwh, source
                FROM utility_rates
                WHERE utility_name = ?
                ORDER BY last_updated DESC
                LIMIT 1
                """,
                (normalized_utility,),
            ).fetchone()
            if utility_only_row:
                return UtilityRateResult(
                    rate_used=float(utility_only_row[0]),
                    rate_source=f"{utility_only_row[1]} (utility fallback)",
                    is_estimated=False,
                )

        if normalized_region:
            region_override_row = connection.execute(
                """
                SELECT avg_rate_per_kwh, source
                FROM utility_rates
                WHERE utility_name = '*' AND region = ?
                ORDER BY last_updated DESC
                LIMIT 1
                """,
                (normalized_region,),
            ).fetchone()
            if region_override_row:
                return UtilityRateResult(
                    rate_used=float(region_override_row[0]),
                    rate_source=f"{region_override_row[1]} (region override)",
                    is_estimated=True,
                )

    return UtilityRateResult(
        rate_used=DEFAULT_NY_AVERAGE_RATE,
        rate_source="NY average fallback",
        is_estimated=True,
    )
