from app.data import ENERGY_OPTIONS, BASELINE_UTILITY_PRICE
from app.models import ScoredOption
from app.schemas import UserRequest


def calculate_effective_price(option):
    """
    Calculate the adjusted price per kWh for an energy option.
    This combines base price, distance impact, time-of-use impact,
    and a reliability bonus.
    """
    distance_penalty = option.distance_miles * 0.002
    reliability_bonus = option.reliability_score * 0.01

    effective_price = (
        option.base_price_per_kwh
        + option.time_of_use_modifier
        + distance_penalty
        - reliability_bonus
    )
    return effective_price


def get_ranked_options(request: UserRequest):
    """
    Return all energy options ranked by effective price.
    """
    baseline_monthly_cost = request.monthly_usage_kwh * BASELINE_UTILITY_PRICE
    scored_options = []

    for option in ENERGY_OPTIONS:
        effective_price = calculate_effective_price(option)
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

    # Sort by lowest effective price
    scored_options.sort(key=lambda x: x.effective_price)

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


def get_recommendation(request: UserRequest):
    """
    Return the single best recommended option with explanation.
    """
    ranked = get_ranked_options(request)
    best = ranked[0]

    return {
        "recommended_option": best,
        "reason": "Lowest overall cost after distance, timing, and reliability adjustments",
    }