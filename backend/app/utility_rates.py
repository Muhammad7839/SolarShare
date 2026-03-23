"""Utility-rate persistence and lookup helpers for realistic New York savings inputs."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_NY_AVERAGE_RATE = 0.20
DEFAULT_RATE_DB_PATH = str(Path(__file__).resolve().parents[1] / "ops_analytics.sqlite3")


@dataclass
class UtilityRateResult:
    """Resolved utility-rate payload returned to pricing and savings engines."""

    rate_used: float
    rate_source: str
    is_estimated: bool


SEED_RATES: list[tuple[str, str, float, str]] = [
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
            [(utility_name, region, rate, source, now_iso) for utility_name, region, rate, source in SEED_RATES],
        )
        connection.commit()


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

    return UtilityRateResult(
        rate_used=DEFAULT_NY_AVERAGE_RATE,
        rate_source="NY average fallback",
        is_estimated=True,
    )
