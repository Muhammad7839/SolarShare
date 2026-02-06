from dataclasses import dataclass
from typing import List


@dataclass
class EnergyOption:
    id: int
    provider_name: str
    base_price_per_kwh: float
    distance_miles: float
    reliability_score: float
    time_of_use_modifier: float
    utility_plan_name: str


@dataclass
class ScoredOption:
    option: EnergyOption
    effective_price: float
    monthly_cost: float
    savings_vs_baseline: float
    badges: List[str]
    is_recommended: bool