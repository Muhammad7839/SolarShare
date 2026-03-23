"""Pydantic request/response schemas that define the public API contract."""

import math
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
SAFE_PAGE_PATTERN = re.compile(r"[A-Za-z0-9_./:-]{1,120}")
SAFE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
MAX_JSON_DEPTH = 3
MAX_JSON_KEYS = 30
MAX_JSON_LIST_ITEMS = 30


def _clean_text(value: str) -> str:
    """Remove control characters and collapse repeated whitespace."""
    return " ".join(CONTROL_CHAR_PATTERN.sub(" ", value).split())


def _normalize_path_token(value: Optional[str], field_name: str) -> Optional[str]:
    """Normalize route-like values and reject unsupported characters."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if not SAFE_PAGE_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field_name} contains unsupported characters")
    return normalized


def _sanitize_json_like(value: Any, depth: int = 0) -> Any:
    """Validate and sanitize analytics/context payloads to safe JSON-like values."""
    if depth >= MAX_JSON_DEPTH:
        raise ValueError("nested payload depth is too large")

    if value is None or isinstance(value, (bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("numeric payload values must be finite")
        return value

    if isinstance(value, str):
        return _clean_text(value)

    if isinstance(value, list):
        if len(value) > MAX_JSON_LIST_ITEMS:
            raise ValueError("list payloads exceed size limit")
        return [_sanitize_json_like(item, depth + 1) for item in value]

    if isinstance(value, dict):
        if len(value) > MAX_JSON_KEYS:
            raise ValueError("object payloads exceed size limit")
        sanitized: Dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("payload keys must be strings")
            key = raw_key.strip().lower().replace(" ", "_")
            if not SAFE_TOKEN_PATTERN.fullmatch(key):
                raise ValueError("payload keys contain unsupported characters")
            sanitized[key] = _sanitize_json_like(raw_value, depth + 1)
        return sanitized

    raise ValueError("payload contains unsupported value types")


# ---------- Request ----------

class UserRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    location: str = Field(default="", max_length=120)
    zip_code: Optional[str] = Field(default=None, max_length=10)
    user_key: Optional[str] = Field(default=None, max_length=120)
    assign_project: bool = False
    subscription_size_kw: Optional[float] = Field(default=None, gt=0)
    monthly_usage_kwh: float = Field(gt=0)
    priority: Literal[
        "balanced",
        "lowest_cost",
        "highest_reliability",
        "closest_distance",
    ] = "balanced"

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        """Collapse duplicate whitespace for stable downstream matching."""
        return _clean_text(value)

    @field_validator("zip_code")
    @classmethod
    def normalize_zip_code(cls, value: Optional[str]) -> Optional[str]:
        """Normalize ZIP code input and validate US ZIP/ZIP+4 format."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"\d{5}(?:-\d{4})?", normalized):
            raise ValueError("ZIP code must be 5 digits or ZIP+4 format")
        return normalized

    @field_validator("user_key")
    @classmethod
    def normalize_user_key(cls, value: Optional[str]) -> Optional[str]:
        """Normalize user key token used for subscription persistence."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{2,120}", normalized):
            raise ValueError("user_key contains unsupported characters")
        return normalized

    @model_validator(mode="after")
    def require_location_or_zip(self) -> "UserRequest":
        """Require at least one location identifier for geocoding accuracy."""
        if not self.location and not self.zip_code:
            raise ValueError("Provide a city/state location or a ZIP code")
        return self


# ---------- Nested option ----------

class EnergyOptionSchema(BaseModel):
    id: int
    provider_name: str
    base_price_per_kwh: float
    distance_miles: float
    reliability_score: float
    time_of_use_modifier: float
    utility_plan_name: str


# ---------- Scored option ----------

class ScoredOptionSchema(BaseModel):
    option: EnergyOptionSchema
    effective_price: float
    monthly_cost: float
    savings_vs_baseline: float
    badges: List[str]
    is_recommended: bool


# ---------- Recommendation ----------

class RecommendationResponse(BaseModel):
    recommended_option: ScoredOptionSchema
    reason: str
    reasons: List[str] = Field(default_factory=list)


class FactorBreakdownSchema(BaseModel):
    """Transparent score breakdown for recommendation explainability."""

    price: float
    reliability: float
    distance: float


class MarketContextSchema(BaseModel):
    """Live market context used to explain recommendation assumptions."""

    resolved_location: str
    city: Optional[str]
    county: Optional[str]
    state_code: Optional[str]
    postal_code: Optional[str]
    country_code: Optional[str]
    region: Optional[str] = None
    utility: Optional[str] = None
    latitude: float
    longitude: float
    utility_price_per_kwh: float
    utility_rate_period: Optional[str]
    rate_source: str = "NY average fallback"
    rate_is_estimated: bool = True
    avg_shortwave_radiation: float
    avg_cloud_cover_pct: float
    data_sources: List[str]
    source_urls: List[str]
    observed_at_utc: str
    using_fallback: bool


class LiveComparisonResponse(BaseModel):
    """Combined payload for live ranking, recommendation, and context."""

    options: List[ScoredOptionSchema]
    recommendation: RecommendationResponse
    market_context: MarketContextSchema
    resolution_confidence: float
    fallback_reason: Optional[str]
    project_status: str = "available"
    project_status_reason: Optional[str] = None
    waitlist_timeline: Optional[str] = None
    waitlist_position: Optional[int] = None
    matched_project_count: int = 0
    project_name: Optional[str] = None
    project_capacity: Optional[float] = None
    remaining_capacity: Optional[int] = None
    factor_breakdown: FactorBreakdownSchema
    financial_breakdown: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    confidence_reason: List[str] = Field(default_factory=list)
    recommendation_label: Literal["recommended", "low_savings", "not_recommended"] = "recommended"
    low_savings_reason: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)
    platform_highlights: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class LocationResolveIn(BaseModel):
    """Location resolution payload used for pre-submit geocoding preview."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    location: str = Field(default="", max_length=120)
    zip_code: Optional[str] = Field(default=None, max_length=10)

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        """Normalize location text for deterministic resolution behavior."""
        return _clean_text(value)

    @field_validator("zip_code")
    @classmethod
    def normalize_zip_code(cls, value: Optional[str]) -> Optional[str]:
        """Normalize ZIP code input and validate US ZIP/ZIP+4 format."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"\d{5}(?:-\d{4})?", normalized):
            raise ValueError("ZIP code must be 5 digits or ZIP+4 format")
        return normalized

    @model_validator(mode="after")
    def require_location_or_zip(self) -> "LocationResolveIn":
        """Require at least one location identifier for geocoding preview."""
        if not self.location and not self.zip_code:
            raise ValueError("Provide a city/state location or a ZIP code")
        return self


class LocationResolveOut(BaseModel):
    """Resolved location payload returned to frontend location preview card."""

    resolved_location: str
    city: Optional[str]
    county: Optional[str]
    state_code: Optional[str]
    postal_code: Optional[str]
    country_code: Optional[str]
    latitude: float
    longitude: float
    confidence: float
    using_fallback: bool
    resolution_status: str = "resolved"
    suggested_zip_codes: List[str] = Field(default_factory=list)
    region: Optional[str] = None
    utility: Optional[str] = None
    source: str


class AssistantChatIn(BaseModel):
    """Chat assistant request payload with optional page and client context."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    message: str = Field(min_length=2, max_length=600)
    page: Optional[str] = Field(default=None, max_length=120)
    context: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        """Normalize chat prompts before assistant processing."""
        return _clean_text(value)

    @field_validator("page")
    @classmethod
    def validate_page(cls, value: Optional[str]) -> Optional[str]:
        """Validate optional page token for log and analytics consistency."""
        return _normalize_path_token(value, "page")

    @field_validator("context")
    @classmethod
    def sanitize_context(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        """Keep assistant context payload JSON-safe and bounded in size."""
        if not isinstance(value, dict):
            raise ValueError("context must be an object")
        return _sanitize_json_like(value)


class AssistantChatOut(BaseModel):
    """Assistant response payload with mode and suggested follow-up actions."""

    reply: str
    mode: Literal["ai", "fallback"]
    suggested_actions: List[str]


class AnalyticsEventIn(BaseModel):
    """Anonymous analytics event payload for conversion funnel tracking."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    event_name: str = Field(min_length=2, max_length=120)
    page: Optional[str] = Field(default=None, max_length=120)
    session_id: Optional[str] = Field(default=None, max_length=120)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_name")
    @classmethod
    def normalize_event_name(cls, value: str) -> str:
        """Restrict event naming to safe operational tokens."""
        normalized = value.strip().lower().replace(" ", "_")
        if not re.fullmatch(r"[a-z0-9_.:-]{2,120}", normalized):
            raise ValueError("event_name must contain only letters, numbers, and _ . : -")
        return normalized

    @field_validator("page")
    @classmethod
    def validate_page(cls, value: Optional[str]) -> Optional[str]:
        """Validate page value to avoid unsafe HTML-like payloads."""
        return _normalize_path_token(value, "page")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: Optional[str]) -> Optional[str]:
        """Validate session identifier format for analytics safety and consistency."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", normalized):
            raise ValueError("session_id contains unsupported characters")
        return normalized

    @field_validator("metadata")
    @classmethod
    def sanitize_metadata(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        """Reject malformed analytics payloads and normalize accepted metadata."""
        if not isinstance(value, dict):
            raise ValueError("metadata must be an object")
        return _sanitize_json_like(value)


class AnalyticsEventOut(BaseModel):
    """Acknowledgement payload for accepted analytics events."""

    accepted: bool


class AdminAnalyticsOut(BaseModel):
    """Admin analytics summary for funnel and event visibility."""

    totals: Dict[str, int]
    by_event: Dict[str, int]
    dropoff: Dict[str, int]
    recent_events: List[Dict[str, Any]]


class DemoRequestIn(BaseModel):
    """Demo request payload for normalized CRM lead intake."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    organization: Optional[str] = Field(default=None, max_length=160)
    message: str = Field(min_length=10, max_length=1000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Normalize names before CRM and log processing."""
        return _clean_text(value)

    @field_validator("organization")
    @classmethod
    def normalize_organization(cls, value: Optional[str]) -> Optional[str]:
        """Normalize organization strings while allowing blank optional values."""
        if value is None:
            return None
        normalized = _clean_text(value)
        return normalized or None

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        """Normalize free-text demo requests for consistent persistence."""
        return _clean_text(value)


class DemoRequestOut(BaseModel):
    """Acknowledgement payload returned after demo request capture."""

    lead_id: str
    received: bool


class ContactInquiryIn(BaseModel):
    """Validated contact inquiry payload accepted from public contact page."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    interest: Literal[
        "customer_support",
        "methodology_question",
        "partnership",
        "investor_relations",
        "other",
    ] = "other"
    message: str = Field(min_length=10, max_length=1000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Normalize contact names before persistence."""
        return _clean_text(value)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        """Normalize inquiry body text before persistence."""
        return _clean_text(value)


class ContactInquiryOut(BaseModel):
    """Acknowledgement response returned after contact form submission."""

    inquiry_id: str
    received: bool
