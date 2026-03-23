"""Business logic for scoring, ranking, and selecting clean energy options."""

import os

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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp numeric values to a bounded range."""
    return max(minimum, min(maximum, value))


def _demo_mode_enabled() -> bool:
    """Return true when demo mode is explicitly enabled."""
    raw_value = (os.getenv("DEMO_MODE") or os.getenv("SOLAR_SHARE_DEMO_MODE") or "").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def _platform_margin_rate() -> float:
    """Resolve platform margin within the allowed 2-5 percent range."""
    raw = (os.getenv("SOLAR_SHARE_PLATFORM_MARGIN_RATE") or "0.03").strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = 0.03
    return round(_clamp(parsed, 0.02, 0.05), 4)


def _build_recommendation_reasons(snapshot) -> list[str]:
    """Build human-readable recommendation reasons for trust and explainability."""
    reasons: list[str] = []
    if snapshot.avg_shortwave_radiation >= 420:
        reasons.append("High solar production in your region supports stronger credit generation.")
    if snapshot.utility:
        reasons.append(f"Utility supports community solar credits: {snapshot.utility}.")
    reasons.append("10% discount available on utility bill credits in this scenario.")
    if snapshot.region == "Long Island":
        reasons.append("Long Island projects typically deliver strong matching for local load profiles.")
    if snapshot.region == "NYC":
        reasons.append("NYC billing compatibility improves credit application reliability.")
    return reasons


def _build_confidence_details(request: UserRequest, snapshot, project_status: str) -> tuple[float, list[str]]:
    """Return confidence score and rationale for the displayed recommendation."""
    reasons: list[str] = []
    score = snapshot.resolution_confidence

    requested_zip = (request.zip_code or "").strip()
    resolved_zip = (snapshot.postal_code or "").strip()
    if requested_zip and resolved_zip.startswith(requested_zip[:5]):
        reasons.append("Exact ZIP match")
        score += 0.03
    elif requested_zip:
        reasons.append("ZIP resolved through fallback mapping")
        score -= 0.02

    if snapshot.utility_rate_is_estimated:
        reasons.append("Savings based on estimated rate")
        score -= 0.12
    else:
        reasons.append("Utility data verified")
        score += 0.04

    if project_status == "waitlist":
        reasons.append("Project availability is pending, so savings certainty is lower")
        score -= 0.08
    else:
        reasons.append("Active project capacity is available")

    return round(_clamp(score, 0.0, 1.0), 3), reasons


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

    project_status = "available"
    project_reason = "Active project capacity is available"
    waitlist_timeline = None
    matched_project_count = len(ranked)
    if not _demo_mode_enabled() and snapshot.state_code != "NY":
        project_status = "waitlist"
        project_reason = "No active capacity in your resolved region yet"
        waitlist_timeline = "Estimated availability: 6-10 weeks"
        matched_project_count = 0

    discount_rate = 0.10
    margin_rate = _platform_margin_rate()
    credit_value = round(request.monthly_usage_kwh * snapshot.utility_price_per_kwh, 2) if project_status == "available" else 0.0
    user_payment = round(credit_value * (1.0 - discount_rate), 2)
    user_savings = round(credit_value - user_payment, 2)
    platform_revenue = round(credit_value * margin_rate, 2)
    developer_payout = round(credit_value - user_savings - platform_revenue, 2)

    recommendation_label = "recommended"
    low_savings_reason = None
    alternatives: list[str] = []
    if user_savings <= 0:
        recommendation_label = "not_recommended"
        low_savings_reason = "Discounted credit value does not exceed expected bill impact in this scenario."
        alternatives = ["Join waitlist for a closer project", "Share recent utility bill for finer sizing"]
    elif user_savings < 15:
        recommendation_label = "low_savings"
        low_savings_reason = "Savings are positive but low because usage-credit alignment is limited."
        alternatives = ["Try a higher usage month profile", "Select a project with higher production allocation"]

    confidence_score, confidence_reason = _build_confidence_details(
        request=request,
        snapshot=snapshot,
        project_status=project_status,
    )
    recommendation_reasons = _build_recommendation_reasons(snapshot)

    return {
        "options": ranked,
        "recommendation": {
            "recommended_option": ranked[0],
            "reason": _reason_for_priority(request.priority),
            "reasons": recommendation_reasons,
        },
        "market_context": {
            "resolved_location": snapshot.resolved_location,
            "city": snapshot.city,
            "county": snapshot.county,
            "state_code": snapshot.state_code,
            "postal_code": snapshot.postal_code,
            "country_code": snapshot.country_code,
            "region": snapshot.region,
            "utility": snapshot.utility,
            "latitude": snapshot.latitude,
            "longitude": snapshot.longitude,
            "utility_price_per_kwh": snapshot.utility_price_per_kwh,
            "utility_rate_period": snapshot.utility_rate_period,
            "rate_source": snapshot.utility_rate_source,
            "rate_is_estimated": snapshot.utility_rate_is_estimated,
            "avg_shortwave_radiation": snapshot.avg_shortwave_radiation,
            "avg_cloud_cover_pct": snapshot.avg_cloud_cover_pct,
            "data_sources": snapshot.data_sources,
            "source_urls": snapshot.source_urls,
            "observed_at_utc": snapshot.observed_at_utc,
            "using_fallback": snapshot.using_fallback,
        },
        "resolution_confidence": snapshot.resolution_confidence,
        "fallback_reason": snapshot.fallback_reason,
        "project_status": project_status,
        "matched_project_count": matched_project_count,
        "waitlist_timeline": waitlist_timeline,
        "project_status_reason": project_reason,
        "factor_breakdown": _build_factor_breakdown(ranked[0]),
        "financial_breakdown": {
            "credit_value": credit_value,
            "user_payment": user_payment,
            "user_savings": user_savings,
            "platform_revenue": platform_revenue,
            "platform_margin": round(margin_rate, 4),
            "developer_payout": developer_payout,
            "rate_used": snapshot.utility_price_per_kwh,
            "rate_source": snapshot.utility_rate_source,
            "is_estimated": snapshot.utility_rate_is_estimated,
            "discount_rate": discount_rate,
            "billing_explanation": "Estimated savings assume a 10% discount on utility bill credits. Example: $100 credits -> $90 payment -> $10 savings.",
            "platform_revenue_explanation": "How SolarShare makes money: a 2-5% platform margin is retained from credited value while customers receive discounted credits.",
        },
        "confidence_score": confidence_score,
        "confidence_reason": confidence_reason,
        "recommendation_label": recommendation_label,
        "low_savings_reason": low_savings_reason,
        "alternatives": alternatives,
        "platform_highlights": [
            "Best project automatically selected",
            "Optimized credit allocation",
            "Smart matching engine",
        ],
    }
