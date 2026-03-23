"""Centralized assumptions and constants for SolarShare financial simulation behavior."""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

ANNUAL_OUTPUT_PER_KW = float((os.getenv("SOLAR_SHARE_ANNUAL_OUTPUT_PER_KW") or "1300").strip())
DEFAULT_DISCOUNT_RATE = float((os.getenv("SOLAR_SHARE_DEFAULT_DISCOUNT_RATE") or "0.10").strip())
DEFAULT_PLATFORM_MARGIN = float((os.getenv("SOLAR_SHARE_PLATFORM_MARGIN_RATE") or "0.03").strip())
DEFAULT_NY_AVERAGE_RATE = float((os.getenv("SOLAR_SHARE_DEFAULT_NY_RATE") or "0.20").strip())

# Monthly share values sum to 1.0 (Option A model: annual total allocation by month).
MONTHLY_PRODUCTION_SHARES: List[Tuple[str, float]] = [
    ("Jan", 0.0536),
    ("Feb", 0.0625),
    ("Mar", 0.0804),
    ("Apr", 0.0982),
    ("May", 0.1071),
    ("Jun", 0.1161),
    ("Jul", 0.1161),
    ("Aug", 0.1071),
    ("Sep", 0.0893),
    ("Oct", 0.0714),
    ("Nov", 0.0536),
    ("Dec", 0.0446),
]

DEFAULT_UTILITY_RATE_BY_REGION: Dict[str, float] = {
    "NYC": 0.274,
    "Long Island": 0.232,
    "Upstate": 0.208,
}


def production_shares_sum() -> float:
    """Return monthly share total for test and runtime validation."""
    return round(sum(share for _, share in MONTHLY_PRODUCTION_SHARES), 6)
