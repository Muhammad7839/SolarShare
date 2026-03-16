"""Business logic for scoring, ranking, and selecting clean energy options."""

from app.data import ENERGY_OPTIONS, BASELINE_UTILITY_PRICE
from app.models import EnergyOption
from app.models import ScoredOption
from app.real_data import build_live_market_snapshot
from app.schemas import UserRequest


LOCATION_DISTANCE_MULTIPLIERS = {
    "urban": 0.95,
    "city": 0.95,
    "downtown": 0.95,
    "suburb": 1.05,
    "suburban": 1.05,
    "rural": 1.15,
}


def get_location_distance_multiplier(location: str) -> float:
    """
    Infer a simple distance sensitivity multiplier from user location text.
    """
    normalized_location = location.lower()
    for keyword, multiplier in LOCATION_DISTANCE_MULTIPLIERS.items():
        if keyword in normalized_location:
            return multiplier
    return 1.0


def calculate_effective_price(option: EnergyOption, location_distance_multiplier: float) -> float:
    """
    Calculate the adjusted price per kWh for an energy option.
    This combines base price, distance impact, time-of-use impact,
    and a reliability bonus.
    """
    distance_penalty = option.distance_miles * 0.002 * location_distance_multiplier
    reliability_bonus = option.reliability_score * 0.01

    effective_price = (
        option.base_price_per_kwh
        + option.time_of_use_modifier
        + distance_penalty
        - reliability_bonus
    )
    return effective_price


def _rank_sort_key(scored_option: ScoredOption, priority: str) -> tuple:
    """
    Return sort key based on user preference while preserving stable tie-breaks.
    """
    if priority == "lowest_cost":
        return (
            scored_option.effective_price,
            scored_option.option.distance_miles,
            -scored_option.option.reliability_score,
        )

    if priority == "highest_reliability":
        return (
            -scored_option.option.reliability_score,
            scored_option.effective_price,
            scored_option.option.distance_miles,
        )

    if priority == "closest_distance":
        return (
            scored_option.option.distance_miles,
            scored_option.effective_price,
            -scored_option.option.reliability_score,
        )

    # balanced
    return (
        scored_option.effective_price,
        scored_option.option.distance_miles,
        -scored_option.option.reliability_score,
    )


def _reason_for_priority(priority: str) -> str:
    """Return recommendation explanation copy per ranking mode."""
    reasons = {
        "balanced": "Best overall balance of adjusted cost, distance, and reliability",
        "lowest_cost": "Lowest adjusted monthly cost based on your usage",
        "highest_reliability": "Highest provider reliability with cost and distance tie-breakers",
        "closest_distance": "Closest provider distance with cost and reliability tie-breakers",
    }
    return reasons[priority]


def _build_factor_breakdown(recommended: ScoredOption) -> dict[str, float]:
    """Build transparent recommendation-factor scores on a normalized 0..1 scale."""
    price_component = max(0.0, min(1.0, 1.0 - (recommended.effective_price / 0.5)))
    reliability_component = max(0.0, min(1.0, recommended.option.reliability_score))
    distance_component = max(0.0, min(1.0, 1.0 - (recommended.option.distance_miles / 350.0)))
    return {
        "price": round(price_component, 3),
        "reliability": round(reliability_component, 3),
        "distance": round(distance_component, 3),
    }


def _rank_with_options(
    request: UserRequest,
    options: list[EnergyOption],
    baseline_utility_price: float,
) -> list[ScoredOption]:
    """Score and rank any candidate option list using existing ranking rules."""
    if not options:
        return []

    baseline_monthly_cost = request.monthly_usage_kwh * baseline_utility_price
    location_distance_multiplier = get_location_distance_multiplier(request.location)
    scored_options = []

    for option in options:
        effective_price = calculate_effective_price(option, location_distance_multiplier)
        monthly_cost = effective_price * request.monthly_usage_kwh
        savings = baseline_monthly_cost - monthly_cost

        scored_options.append(
            ScoredOption(
                option=option,
                effective_price=round(effective_price, 3),
                monthly_cost=round(monthly_cost, 2),
                savings_vs_baseline=round(savings, 2),
                badges=[],
                is_recommended=False,
            )
        )

    # Sort based on the user-selected priority.
    scored_options.sort(key=lambda option: _rank_sort_key(option, request.priority))

    # Reset badges (so repeated calls never accumulate)
    for item in scored_options:
        item.badges = []

    # Assign badges
    cheapest = min(scored_options, key=lambda x: x.option.base_price_per_kwh)
    closest = min(scored_options, key=lambda x: x.option.distance_miles)
    most_reliable = max(scored_options, key=lambda x: x.option.reliability_score)

    cheapest.badges.append("Cheapest")
    closest.badges.append("Closest")
    most_reliable.badges.append("Most Reliable")

    # Mark top recommendation
    scored_options[0].is_recommended = True

    return scored_options


def get_ranked_options(request: UserRequest):
    """
    Return default ranked options using local baseline dataset.
    """
    return _rank_with_options(request, ENERGY_OPTIONS, BASELINE_UTILITY_PRICE)


def get_recommendation(request: UserRequest):
    """
    Return the single best recommended option with explanation.
    """
    ranked = get_ranked_options(request)
    if not ranked:
        raise ValueError("No energy options are currently available")

    best = ranked[0]
    return {
        "recommended_option": best,
        "reason": _reason_for_priority(request.priority),
    }


def get_live_comparison(request: UserRequest):
    """
    Return live-data ranking, recommendation, and market context in one payload.
    """
    snapshot = build_live_market_snapshot(request.location, request.zip_code)
    ranked = _rank_with_options(
        request=request,
        options=snapshot.options,
        baseline_utility_price=snapshot.utility_price_per_kwh,
    )
    if not ranked:
        raise ValueError("No live options are currently available")

    return {
        "options": ranked,
        "recommendation": {
            "recommended_option": ranked[0],
            "reason": _reason_for_priority(request.priority),
        },
        "market_context": {
            "resolved_location": snapshot.resolved_location,
            "city": snapshot.city,
            "county": snapshot.county,
            "state_code": snapshot.state_code,
            "postal_code": snapshot.postal_code,
            "country_code": snapshot.country_code,
            "latitude": snapshot.latitude,
            "longitude": snapshot.longitude,
            "utility_price_per_kwh": snapshot.utility_price_per_kwh,
            "utility_rate_period": snapshot.utility_rate_period,
            "avg_shortwave_radiation": snapshot.avg_shortwave_radiation,
            "avg_cloud_cover_pct": snapshot.avg_cloud_cover_pct,
            "data_sources": snapshot.data_sources,
            "source_urls": snapshot.source_urls,
            "observed_at_utc": snapshot.observed_at_utc,
            "using_fallback": snapshot.using_fallback,
        },
        "resolution_confidence": snapshot.resolution_confidence,
        "fallback_reason": snapshot.fallback_reason,
        "factor_breakdown": _build_factor_breakdown(ranked[0]),
    }
