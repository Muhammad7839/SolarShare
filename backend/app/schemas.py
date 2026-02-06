from typing import List
from pydantic import BaseModel


# ---------- Request ----------

class UserRequest(BaseModel):
    location: str
    monthly_usage_kwh: float
    priority: str


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