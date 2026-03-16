"""Pydantic request/response schemas that define the public API contract."""

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ---------- Request ----------

class UserRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    location: str = Field(default="", max_length=120)
    zip_code: Optional[str] = Field(default=None, max_length=10)
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
        return " ".join(value.split())

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
    latitude: float
    longitude: float
    utility_price_per_kwh: float
    utility_rate_period: Optional[str]
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
    factor_breakdown: FactorBreakdownSchema


class LocationResolveIn(BaseModel):
    """Location resolution payload used for pre-submit geocoding preview."""

    model_config = ConfigDict(str_strip_whitespace=True)

    location: str = Field(default="", max_length=120)
    zip_code: Optional[str] = Field(default=None, max_length=10)

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
    source: str


class AssistantChatIn(BaseModel):
    """Chat assistant request payload with optional page and client context."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=2, max_length=600)
    page: Optional[str] = Field(default=None, max_length=120)
    context: Dict[str, Any] = Field(default_factory=dict)


class AssistantChatOut(BaseModel):
    """Assistant response payload with mode and suggested follow-up actions."""

    reply: str
    mode: Literal["ai", "fallback"]
    suggested_actions: List[str]


class AnalyticsEventIn(BaseModel):
    """Anonymous analytics event payload for conversion funnel tracking."""

    model_config = ConfigDict(str_strip_whitespace=True)

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
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_./:-]{1,120}", normalized):
            raise ValueError("page contains unsupported characters")
        return normalized

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

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    organization: Optional[str] = Field(default=None, max_length=160)
    message: str = Field(min_length=10, max_length=1000)


class DemoRequestOut(BaseModel):
    """Acknowledgement payload returned after demo request capture."""

    lead_id: str
    received: bool


class ContactInquiryIn(BaseModel):
    """Validated contact inquiry payload accepted from public contact page."""

    model_config = ConfigDict(str_strip_whitespace=True)

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


class ContactInquiryOut(BaseModel):
    """Acknowledgement response returned after contact form submission."""

    inquiry_id: str
    received: bool
