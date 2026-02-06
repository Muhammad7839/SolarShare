from app.models import EnergyOption

# Baseline utility price ($/kWh) used to calculate savings
BASELINE_UTILITY_PRICE = 0.22

# Mock local clean energy options (simulated but realistic)
ENERGY_OPTIONS = [
    EnergyOption(
        id=1,
        provider_name="Local Community Solar A",
        base_price_per_kwh=0.18,
        distance_miles=2.5,
        reliability_score=0.92,
        time_of_use_modifier=0.01,
        utility_plan_name="Community Solar Fixed"
    ),
    EnergyOption(
        id=2,
        provider_name="Green Energy Co-op",
        base_price_per_kwh=0.17,
        distance_miles=8.0,
        reliability_score=0.88,
        time_of_use_modifier=0.015,
        utility_plan_name="Variable Green Plan"
    ),
    EnergyOption(
        id=3,
        provider_name="Utility Green Choice",
        base_price_per_kwh=0.20,
        distance_miles=1.0,
        reliability_score=0.95,
        time_of_use_modifier=0.005,
        utility_plan_name="Utility Green Rider"
    ),
]