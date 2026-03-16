"""External data adapters and fallback logic for live SolarShare comparisons."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any, List, Optional, Tuple

import httpx

from app.data import BASELINE_UTILITY_PRICE
from app.models import EnergyOption


@dataclass
class LiveMarketSnapshot:
    """Resolved location context and live-generated option candidates."""

    resolved_location: str
    city: Optional[str]
    county: Optional[str]
    state_code: Optional[str]
    postal_code: Optional[str]
    country_code: Optional[str]
    latitude: float
    longitude: float
    utility_price_per_kwh: float
    avg_shortwave_radiation: float
    avg_cloud_cover_pct: float
    data_sources: List[str]
    source_urls: List[str]
    observed_at_utc: str
    utility_rate_period: Optional[str]
    using_fallback: bool
    resolution_confidence: float
    fallback_reason: Optional[str]
    options: List[EnergyOption]


@dataclass
class ResolvedLocation:
    """Resolved location details returned from geocoding workflow."""

    latitude: float
    longitude: float
    display_name: str
    state_code: Optional[str]
    city: Optional[str]
    county: Optional[str]
    postal_code: Optional[str]
    country_code: Optional[str]
    source: str
    confidence: float
    fallback_reason: Optional[str]


SOLAR_SITES = [
    {
        "id": 101,
        "provider_name": "Long Island Community Solar",
        "utility_plan_name": "PSEG-LI Credit Allocation",
        "lat": 40.9049,
        "lon": -72.7807,
        "base_reliability": 0.93,
        "price_factor": 0.88,
    },
    {
        "id": 102,
        "provider_name": "Northeast Green Grid",
        "utility_plan_name": "Northeast Shared Solar",
        "lat": 42.6526,
        "lon": -73.7562,
        "base_reliability": 0.9,
        "price_factor": 0.9,
    },
    {
        "id": 103,
        "provider_name": "Mid-Atlantic Solar Collective",
        "utility_plan_name": "Regional Distributed Credit Plan",
        "lat": 39.2904,
        "lon": -76.6122,
        "base_reliability": 0.91,
        "price_factor": 0.89,
    },
    {
        "id": 104,
        "provider_name": "Carolina Bright Energy",
        "utility_plan_name": "Carolinas Utility Green Rider",
        "lat": 35.7796,
        "lon": -78.6382,
        "base_reliability": 0.92,
        "price_factor": 0.87,
    },
    {
        "id": 105,
        "provider_name": "Sun Belt Utility Solar",
        "utility_plan_name": "Sun Belt Clean Capacity Plan",
        "lat": 33.4484,
        "lon": -112.074,
        "base_reliability": 0.95,
        "price_factor": 0.86,
    },
    {
        "id": 106,
        "provider_name": "California Valley Solar Hub",
        "utility_plan_name": "West Grid Solar Share",
        "lat": 36.7783,
        "lon": -119.4179,
        "base_reliability": 0.96,
        "price_factor": 0.84,
    },
    {
        "id": 107,
        "provider_name": "Great Plains Renewables",
        "utility_plan_name": "Midwest Community Solar Option",
        "lat": 41.2565,
        "lon": -95.9345,
        "base_reliability": 0.9,
        "price_factor": 0.9,
    },
]

FALLBACK_COORDS = {
    "new york": (40.7128, -74.0060, "New York, NY", "NY"),
    "boston": (42.3601, -71.0589, "Boston, MA", "MA"),
    "long island": (40.7891, -73.1350, "Long Island, NY", "NY"),
    "chicago": (41.8781, -87.6298, "Chicago, IL", "IL"),
    "los angeles": (34.0522, -118.2437, "Los Angeles, CA", "CA"),
    "phoenix": (33.4484, -112.0740, "Phoenix, AZ", "AZ"),
}

FALLBACK_ZIP_COORDS = {
    "11757": (40.6862, -73.4664, "Massapequa Park, NY 11757", "NY", "Massapequa Park", "Nassau County"),
    "10001": (40.7506, -73.9972, "New York, NY 10001", "NY", "New York", "New York County"),
    "07030": (40.744, -74.0324, "Hoboken, NJ 07030", "NJ", "Hoboken", "Hudson County"),
}

STATE_RATE_FALLBACK = {
    "NY": 0.241,
    "CA": 0.305,
    "MA": 0.288,
    "NJ": 0.214,
    "PA": 0.198,
    "TX": 0.154,
    "FL": 0.142,
    "IL": 0.183,
    "AZ": 0.152,
    "NC": 0.136,
}

GEOCODE_CACHE_TTL_SECONDS = int(os.getenv("SOLAR_SHARE_GEOCODE_CACHE_TTL_SECONDS", "21600"))
SOLAR_CACHE_TTL_SECONDS = int(os.getenv("SOLAR_SHARE_SOLAR_CACHE_TTL_SECONDS", "900"))
RATE_CACHE_TTL_SECONDS = int(os.getenv("SOLAR_SHARE_RATE_CACHE_TTL_SECONDS", "21600"))
_CACHE_LOCK = threading.Lock()
_TTL_CACHE: dict[Tuple[str, str], Tuple[float, Any]] = {}


def _cache_get(bucket: str, key: str) -> Optional[Any]:
    """Return cached value for a bucket/key if TTL has not expired."""
    now = time.monotonic()
    cache_key = (bucket, key)
    with _CACHE_LOCK:
        item = _TTL_CACHE.get(cache_key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= now:
            _TTL_CACHE.pop(cache_key, None)
            return None
        return value


def _cache_set(bucket: str, key: str, value: Any, ttl_seconds: int) -> None:
    """Store value in TTL cache with per-bucket expiry policy."""
    expiry = time.monotonic() + max(ttl_seconds, 1)
    with _CACHE_LOCK:
        _TTL_CACHE[(bucket, key)] = (expiry, value)


def _network_enabled() -> bool:
    """Gate network calls for tests and offline deployments."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    if os.getenv("SOLAR_SHARE_REAL_DATA_DISABLE_NETWORK", "0") == "1":
        return False
    return True


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two coordinate pairs."""
    r = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return r * c


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp numeric values to a safe range."""
    return max(minimum, min(maximum, value))


def _extract_city(address: dict[str, Any]) -> Optional[str]:
    """Extract best-fit city/town label from Nominatim address payload."""
    for key in ["city", "town", "village", "hamlet", "municipality"]:
        value = address.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _build_geocode_query(location: str, zip_code: Optional[str]) -> str:
    """Construct geocoding query prioritizing ZIP precision when available."""
    safe_location = location.strip()
    safe_zip = (zip_code or "").strip()
    if safe_location and safe_zip:
        return f"{safe_location}, {safe_zip}, USA"
    if safe_zip:
        return f"{safe_zip}, USA"
    return safe_location


def _confidence_for_source(source: str, has_zip: bool, has_city: bool, has_county: bool) -> float:
    """Map geocode source quality to a stable confidence score for UI trust messaging."""
    if source.startswith("geocode:nominatim"):
        base = 0.95
    elif "fallback-zip" in source:
        base = 0.9
    elif "fallback" in source:
        base = 0.7
    else:
        base = 0.8

    score = base
    if has_zip:
        score += 0.03
    if has_city:
        score += 0.01
    if has_county:
        score += 0.01
    return _clamp(round(score, 2), 0.5, 0.99)


def _fallback_reason_for_source(source: str) -> Optional[str]:
    """Return human-readable fallback reason from source key when fallback occurred."""
    if "fallback-empty" in source:
        return "No geocode match returned; fallback location used."
    if "fallback-error" in source:
        return "Geocoding provider unavailable; fallback location used."
    if "fallback-offline" in source:
        return "Network disabled; fallback location used."
    if "fallback-default" in source:
        return "No precise location match found; default fallback applied."
    if "fallback-zip" in source:
        return "ZIP fallback map used for deterministic resolution."
    if "fallback" in source:
        return "Fallback location source used."
    return None


def _default_location(location: str, zip_code: Optional[str]) -> ResolvedLocation:
    """Return deterministic fallback coordinates when geocoding fails."""
    normalized = location.lower()
    normalized_zip = (zip_code or "").strip()

    if normalized_zip in FALLBACK_ZIP_COORDS:
        lat, lon, display_name, state_code, city, county = FALLBACK_ZIP_COORDS[normalized_zip]
        return ResolvedLocation(
            latitude=lat,
            longitude=lon,
            display_name=display_name,
            state_code=state_code,
            city=city,
            county=county,
            postal_code=normalized_zip,
            country_code="US",
            source="geocode:fallback-zip",
            confidence=0.9,
            fallback_reason="ZIP fallback map used for deterministic resolution.",
        )

    for keyword, data in FALLBACK_COORDS.items():
        if keyword in normalized:
            lat, lon, display_name, state_code = data
            return ResolvedLocation(
                latitude=lat,
                longitude=lon,
                display_name=display_name,
                state_code=state_code,
                city=display_name.split(",")[0].strip(),
                county=None,
                postal_code=normalized_zip or None,
                country_code="US",
                source="geocode:fallback",
                confidence=0.72,
                fallback_reason="Keyword fallback used for location resolution.",
            )

    return ResolvedLocation(
        latitude=40.7128,
        longitude=-74.0060,
        display_name="New York, NY",
        state_code="NY",
        city="New York",
        county="New York County",
        postal_code=normalized_zip or None,
        country_code="US",
        source="geocode:fallback-default",
        confidence=0.68,
        fallback_reason="Default fallback location used.",
    )


def _fetch_geocode(location: str, zip_code: Optional[str]) -> ResolvedLocation:
    """Resolve location text to coordinates using Nominatim."""
    query = _build_geocode_query(location, zip_code)
    normalized_query = " ".join(query.lower().split())
    fallback_location = _default_location(location, zip_code)
    cached = _cache_get("geocode", normalized_query)
    if cached:
        return replace(cached, source=f"{cached.source}:cache")

    if not _network_enabled():
        offline_source = f"{fallback_location.source}:offline"
        fallback_value = replace(
            fallback_location,
            source=offline_source,
            confidence=_confidence_for_source(
                offline_source,
                has_zip=bool(fallback_location.postal_code),
                has_city=bool(fallback_location.city),
                has_county=bool(fallback_location.county),
            ),
            fallback_reason=_fallback_reason_for_source(offline_source),
        )
        _cache_set(
            "geocode",
            normalized_query,
            fallback_value,
            GEOCODE_CACHE_TTL_SECONDS,
        )
        return fallback_value

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
        "countrycodes": "us",
    }
    headers = {"User-Agent": "SolarShare/1.0 (invest@solarshare.com)"}
    try:
        with httpx.Client(timeout=2.8, headers=headers) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        if not payload:
            empty_source = f"{fallback_location.source}:empty"
            fallback_value = replace(
                fallback_location,
                source=empty_source,
                confidence=_confidence_for_source(
                    empty_source,
                    has_zip=bool(fallback_location.postal_code),
                    has_city=bool(fallback_location.city),
                    has_county=bool(fallback_location.county),
                ),
                fallback_reason=_fallback_reason_for_source(empty_source),
            )
            _cache_set(
                "geocode",
                normalized_query,
                fallback_value,
                GEOCODE_CACHE_TTL_SECONDS,
            )
            return fallback_value

        first = payload[0]
        lat = float(first["lat"])
        lon = float(first["lon"])
        display_name = str(first.get("display_name") or fallback_location.display_name)
        address = first.get("address", {})
        state_code = address.get("state_code") or fallback_location.state_code
        if isinstance(state_code, str):
            state_code = state_code.upper()
        city = _extract_city(address) or fallback_location.city
        county = address.get("county") if isinstance(address.get("county"), str) else fallback_location.county
        postal_code = address.get("postcode") if isinstance(address.get("postcode"), str) else fallback_location.postal_code
        country_code = address.get("country_code") if isinstance(address.get("country_code"), str) else fallback_location.country_code
        if isinstance(country_code, str):
            country_code = country_code.upper()
        resolved = ResolvedLocation(
            latitude=lat,
            longitude=lon,
            display_name=display_name,
            state_code=state_code,
            city=city,
            county=county,
            postal_code=postal_code,
            country_code=country_code,
            source="geocode:nominatim",
            confidence=_confidence_for_source(
                "geocode:nominatim",
                has_zip=bool(postal_code),
                has_city=bool(city),
                has_county=bool(county),
            ),
            fallback_reason=None,
        )
        _cache_set(
            "geocode",
            normalized_query,
            resolved,
            GEOCODE_CACHE_TTL_SECONDS,
        )
        return resolved
    except Exception:
        error_source = f"{fallback_location.source}:error"
        fallback_value = replace(
            fallback_location,
            source=error_source,
            confidence=_confidence_for_source(
                error_source,
                has_zip=bool(fallback_location.postal_code),
                has_city=bool(fallback_location.city),
                has_county=bool(fallback_location.county),
            ),
            fallback_reason=_fallback_reason_for_source(error_source),
        )
        _cache_set(
            "geocode",
            normalized_query,
            fallback_value,
            GEOCODE_CACHE_TTL_SECONDS,
        )
        return fallback_value


def _fetch_solar_conditions(latitude: float, longitude: float) -> tuple[float, float, str]:
    """Fetch shortwave radiation and cloud cover from Open-Meteo."""
    location_key = f"{latitude:.3f},{longitude:.3f}"
    cached = _cache_get("solar", location_key)
    if cached:
        avg_radiation, avg_cloud, source = cached
        return avg_radiation, avg_cloud, f"{source}:cache"

    if not _network_enabled():
        source = "solar:fallback"
        _cache_set("solar", location_key, (430.0, 35.0, source), SOLAR_CACHE_TTL_SECONDS)
        return 430.0, 35.0, source

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "shortwave_radiation,cloud_cover",
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        with httpx.Client(timeout=2.8) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        hourly = payload.get("hourly", {})
        radiation_series = [float(v) for v in hourly.get("shortwave_radiation", []) if v is not None]
        cloud_series = [float(v) for v in hourly.get("cloud_cover", []) if v is not None]

        avg_radiation = sum(radiation_series) / len(radiation_series) if radiation_series else 430.0
        avg_cloud = sum(cloud_series) / len(cloud_series) if cloud_series else 35.0
        source = "solar:open-meteo"
        _cache_set(
            "solar",
            location_key,
            (avg_radiation, avg_cloud, source),
            SOLAR_CACHE_TTL_SECONDS,
        )
        return avg_radiation, avg_cloud, source
    except Exception:
        source = "solar:fallback-error"
        _cache_set("solar", location_key, (430.0, 35.0, source), SOLAR_CACHE_TTL_SECONDS)
        return 430.0, 35.0, source


def _fetch_utility_rate(state_code: Optional[str]) -> tuple[float, str, Optional[str]]:
    """Fetch latest U.S. retail electricity price from EIA v2 API."""
    if state_code:
        cached = _cache_get("utility-rate", state_code)
        if cached:
            utility_rate, source, period = cached
            return utility_rate, f"{source}:cache", period

    if not state_code:
        return BASELINE_UTILITY_PRICE, "rate:fallback-no-state", None
    if not _network_enabled():
        utility_rate = STATE_RATE_FALLBACK.get(state_code, BASELINE_UTILITY_PRICE)
        source = "rate:fallback-offline"
        _cache_set("utility-rate", state_code, (utility_rate, source, None), RATE_CACHE_TTL_SECONDS)
        return utility_rate, source, None

    api_key = os.getenv("SOLAR_SHARE_EIA_API_KEY", "DEMO_KEY")
    url = "https://api.eia.gov/v2/electricity/retail-sales/data/"
    params = {
        "api_key": api_key,
        "frequency": "monthly",
        "data[0]": "price",
        "facets[stateid][]": state_code,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 1,
    }
    try:
        with httpx.Client(timeout=3.2) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        records = payload.get("response", {}).get("data", [])
        if not records:
            utility_rate = STATE_RATE_FALLBACK.get(state_code, BASELINE_UTILITY_PRICE)
            source = "rate:fallback-empty"
            _cache_set("utility-rate", state_code, (utility_rate, source, None), RATE_CACHE_TTL_SECONDS)
            return utility_rate, source, None

        value = float(records[0].get("price"))
        period = records[0].get("period")
        if not isinstance(period, str):
            period = None
        # EIA retail "price" is typically reported in cents/kWh.
        if value > 3.0:
            value = value / 100.0
        value = _clamp(value, 0.08, 0.6)
        source = "rate:eia"
        _cache_set("utility-rate", state_code, (value, source, period), RATE_CACHE_TTL_SECONDS)
        return value, source, period
    except Exception:
        utility_rate = STATE_RATE_FALLBACK.get(state_code, BASELINE_UTILITY_PRICE)
        source = "rate:fallback-error"
        _cache_set("utility-rate", state_code, (utility_rate, source, None), RATE_CACHE_TTL_SECONDS)
        return utility_rate, source, None


def resolve_location_context(location: str, zip_code: Optional[str]) -> dict[str, Any]:
    """Resolve location identifiers into normalized geography metadata for preview flows."""
    resolved = _fetch_geocode(location, zip_code)
    return {
        "resolved_location": resolved.display_name,
        "city": resolved.city,
        "county": resolved.county,
        "state_code": resolved.state_code,
        "postal_code": resolved.postal_code,
        "country_code": resolved.country_code,
        "latitude": round(resolved.latitude, 4),
        "longitude": round(resolved.longitude, 4),
        "confidence": resolved.confidence,
        "using_fallback": "fallback" in resolved.source,
        "source": resolved.source,
    }


def build_live_market_snapshot(location: str, zip_code: Optional[str]) -> LiveMarketSnapshot:
    """Build live market inputs and dynamic local option candidates."""
    resolved = _fetch_geocode(location, zip_code)
    latitude = resolved.latitude
    longitude = resolved.longitude
    state_code = resolved.state_code
    avg_radiation, avg_cloud, solar_source = _fetch_solar_conditions(latitude, longitude)
    utility_rate, rate_source, rate_period = _fetch_utility_rate(state_code)

    solar_factor = _clamp(avg_radiation / 500.0, 0.72, 1.18)
    cloud_factor = _clamp(avg_cloud / 100.0, 0.0, 1.0)

    sites_by_distance = sorted(
        SOLAR_SITES,
        key=lambda site: _haversine_miles(latitude, longitude, site["lat"], site["lon"]),
    )

    options: List[EnergyOption] = []
    for site in sites_by_distance[:4]:
        distance = _haversine_miles(latitude, longitude, site["lat"], site["lon"])
        effective_price = utility_rate * site["price_factor"]
        weather_adjustment = (1.0 - solar_factor) * 0.012
        base_price = _clamp(effective_price + weather_adjustment, 0.07, 0.55)
        reliability = _clamp(
            site["base_reliability"] + (solar_factor - 1.0) * 0.08 - cloud_factor * 0.08,
            0.72,
            0.99,
        )
        tou_modifier = _clamp(0.005 + (cloud_factor * 0.014), 0.004, 0.028)
        options.append(
            EnergyOption(
                id=site["id"],
                provider_name=site["provider_name"],
                base_price_per_kwh=round(base_price, 3),
                distance_miles=round(distance, 1),
                reliability_score=round(reliability, 3),
                time_of_use_modifier=round(tou_modifier, 3),
                utility_plan_name=site["utility_plan_name"],
            )
        )

    sources = [resolved.source, solar_source, rate_source]
    source_urls = [
        "https://nominatim.openstreetmap.org/",
        "https://open-meteo.com/",
        "https://www.eia.gov/opendata/",
    ]
    using_fallback = any("fallback" in source for source in sources)

    return LiveMarketSnapshot(
        resolved_location=resolved.display_name,
        city=resolved.city,
        county=resolved.county,
        state_code=resolved.state_code,
        postal_code=resolved.postal_code,
        country_code=resolved.country_code,
        latitude=round(latitude, 4),
        longitude=round(longitude, 4),
        utility_price_per_kwh=round(utility_rate, 3),
        utility_rate_period=rate_period,
        avg_shortwave_radiation=round(avg_radiation, 1),
        avg_cloud_cover_pct=round(avg_cloud, 1),
        data_sources=sources,
        source_urls=source_urls,
        observed_at_utc=datetime.now(timezone.utc).isoformat(),
        using_fallback=using_fallback,
        resolution_confidence=resolved.confidence,
        fallback_reason=resolved.fallback_reason,
        options=options,
    )
