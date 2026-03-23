"""Business logic for scoring, ranking, and selecting clean energy options."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.data import ENERGY_OPTIONS, BASELINE_UTILITY_PRICE
from app.models import EnergyOption, ScoredOption
from app.project_store import (
    add_user_to_waitlist,
    assign_project_to_user,
    get_subscription_for_user,
    list_matching_projects,
    store_credit_ledger,
)
from app.real_data import build_live_market_snapshot
from app.schemas import UserRequest
from app.simulation_config import (
    ANNUAL_OUTPUT_PER_KW,
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_PLATFORM_MARGIN,
    MONTHLY_PRODUCTION_SHARES,
    production_shares_sum,
)


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
    raw = (os.getenv("SOLAR_SHARE_PLATFORM_MARGIN_RATE") or str(DEFAULT_PLATFORM_MARGIN)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = DEFAULT_PLATFORM_MARGIN
    return round(_clamp(parsed, 0.02, 0.05), 4)


def _discount_rate() -> float:
    """Resolve discount rate from env while keeping supported 5-20% range."""
    raw = (os.getenv("SOLAR_SHARE_DEFAULT_DISCOUNT_RATE") or str(DEFAULT_DISCOUNT_RATE)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = DEFAULT_DISCOUNT_RATE
    return round(_clamp(parsed, 0.05, 0.20), 4)


def _estimate_system_size_kw(monthly_usage_kwh: float, annual_output_per_kw: float = ANNUAL_OUTPUT_PER_KW) -> float:
    """Estimate subscription system size from annual usage using configured NY production factor."""
    annual_kwh = monthly_usage_kwh * 12.0
    output_factor = max(annual_output_per_kw, 1.0)
    return round(max(annual_kwh / output_factor, 0.1), 3)


def _simulate_generation_billing(
    monthly_usage_kwh: float,
    utility_rate: float,
    subscription_size_kw: float,
    discount_rate: float,
) -> Dict[str, Any]:
    """Run a 12-month generation simulation using annual production shares and rollover behavior."""
    monthly_breakdown: List[Dict[str, float | str]] = []
    rollover_bank_kwh = 0.0
    annual_credit_value = 0.0
    annual_payment = 0.0
    annual_savings = 0.0
    annual_production_kwh = max(subscription_size_kw * ANNUAL_OUTPUT_PER_KW, 0.0)
    monthly_share_total = production_shares_sum()
    monthly_labels: list[str] = []
    total_production_simulated = 0.0

    for month, monthly_share in MONTHLY_PRODUCTION_SHARES:
        monthly_labels.append(month)
        production_kwh = annual_production_kwh * monthly_share
        usage_kwh = monthly_usage_kwh
        usable_kwh = production_kwh + rollover_bank_kwh
        credit_kwh = min(usable_kwh, usage_kwh)
        rollover_bank_kwh = max(usable_kwh - usage_kwh, 0.0)
        total_production_simulated += production_kwh

        credit_value = credit_kwh * utility_rate
        payment = credit_value * (1.0 - discount_rate)
        savings = credit_value - payment

        annual_credit_value += credit_value
        annual_payment += payment
        annual_savings += savings

        monthly_breakdown.append(
            {
                "month": month,
                "production_kwh": round(production_kwh, 2),
                "usage_kwh": round(usage_kwh, 2),
                "credit_kwh": round(credit_kwh, 2),
                "credit_value": round(credit_value, 2),
                "payment": round(payment, 2),
                "savings": round(savings, 2),
                "rollover_balance": round(rollover_bank_kwh, 2),
                "explanation": "Solar generation, utility crediting, discount payment, and rollover carry-forward.",
            }
        )

    average_monthly_savings = annual_savings / 12.0
    baseline_annual_bill = monthly_usage_kwh * 12.0 * utility_rate
    savings_percent = (annual_savings / baseline_annual_bill * 100.0) if baseline_annual_bill > 0 else 0.0

    return {
        "monthly_breakdown": monthly_breakdown,
        "annual_savings": round(annual_savings, 2),
        "average_monthly_savings": round(average_monthly_savings, 2),
        "estimated_credit_value": round(annual_credit_value, 2),
        "customer_payment": round(annual_payment, 2),
        "rollover_credit_balance": round(rollover_bank_kwh, 2),
        "savings_percent": round(savings_percent, 2),
        "annual_production_kwh": round(annual_production_kwh, 2),
        "simulated_production_kwh": round(total_production_simulated, 2),
        "monthly_share_total": monthly_share_total,
        "months_modeled": monthly_labels,
    }


def _build_recommendation_reasons(snapshot, project_name: Optional[str], recommendation_label: str) -> list[str]:
    """Build human-readable recommendation reasons for trust and explainability."""
    reasons: list[str] = []
    if snapshot.avg_shortwave_radiation >= 420:
        reasons.append("High solar production in your region supports stronger generation output.")
    if snapshot.utility:
        reasons.append(f"Utility supports community-solar credits: {snapshot.utility}.")
    reasons.append("10% discount applied to utility bill credits.")
    reasons.append("Seasonal solar production is modeled across 12 months.")
    if project_name:
        reasons.append(f"Best project automatically selected: {project_name}.")
    if recommendation_label == "low_savings":
        reasons.append("Savings are modest because winter generation is lower in this profile.")
    return reasons


def _build_confidence_details(
    request: UserRequest,
    snapshot,
    project_status: str,
    is_rate_estimated: bool,
) -> tuple[float, list[str]]:
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

    if is_rate_estimated:
        reasons.append("Savings based on estimated rate")
        score -= 0.10
    else:
        reasons.append("Utility data verified")
        score += 0.04

    reasons.append("Seasonal generation model applied")

    if project_status == "waitlist":
        reasons.append("Project availability pending")
        score -= 0.1
    else:
        reasons.append("Project capacity available")

    return round(_clamp(score, 0.0, 1.0), 3), reasons


def _build_assumptions(snapshot, is_rate_estimated: bool, discount_rate: float) -> list[str]:
    """Return user-facing assumptions for transparency and auditability."""
    assumptions = [
        f"{int(discount_rate * 100)}% discount applied",
        f"annual output factor {int(ANNUAL_OUTPUT_PER_KW)} kWh per kW-year",
        "seasonal solar production modeled",
        f"monthly production shares total {production_shares_sum()}",
        "monthly rollover credits carried forward",
    ]
    if is_rate_estimated:
        assumptions.append("utility rate estimated")
    else:
        assumptions.append("utility rate from utility table")

    if snapshot.region:
        assumptions.append(f"project matching constrained to {snapshot.region} region")
    return assumptions


def get_location_distance_multiplier(location: str) -> float:
    """Infer a simple distance sensitivity multiplier from user location text."""
    normalized_location = location.lower()
    for keyword, multiplier in LOCATION_DISTANCE_MULTIPLIERS.items():
        if keyword in normalized_location:
            return multiplier
    return 1.0


def calculate_effective_price(option: EnergyOption, location_distance_multiplier: float) -> float:
    """Calculate adjusted price per kWh combining base price, distance, TOU, and reliability."""
    distance_penalty = option.distance_miles * 0.002 * location_distance_multiplier
    reliability_bonus = option.reliability_score * 0.01
    return option.base_price_per_kwh + option.time_of_use_modifier + distance_penalty - reliability_bonus


def _rank_sort_key(scored_option: ScoredOption, priority: str) -> tuple:
    """Return sort key based on user preference while preserving stable tie-breaks."""
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
    scored_options: list[ScoredOption] = []

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

    scored_options.sort(key=lambda option: _rank_sort_key(option, request.priority))

    for item in scored_options:
        item.badges = []

    cheapest = min(scored_options, key=lambda x: x.option.base_price_per_kwh)
    closest = min(scored_options, key=lambda x: x.option.distance_miles)
    most_reliable = max(scored_options, key=lambda x: x.option.reliability_score)

    cheapest.badges.append("Cheapest")
    closest.badges.append("Closest")
    most_reliable.badges.append("Most Reliable")
    scored_options[0].is_recommended = True

    return scored_options


def get_ranked_options(request: UserRequest):
    """Return default ranked options using local baseline dataset."""
    return _rank_with_options(request, ENERGY_OPTIONS, BASELINE_UTILITY_PRICE)


def get_recommendation(request: UserRequest):
    """Return the single best recommended option with explanation."""
    ranked = get_ranked_options(request)
    if not ranked:
        raise ValueError("No energy options are currently available")

    best = ranked[0]
    return {
        "recommended_option": best,
        "reason": _reason_for_priority(request.priority),
    }


def get_live_comparison(request: UserRequest):
    """Return live-data ranking, recommendation, and realistic 12-month billing outputs."""
    snapshot = build_live_market_snapshot(request.location, request.zip_code)
    ranked = _rank_with_options(
        request=request,
        options=snapshot.options,
        baseline_utility_price=snapshot.utility_price_per_kwh,
    )
    if not ranked:
        raise ValueError("No live options are currently available")

    discount_rate = _discount_rate()
    margin_rate = _platform_margin_rate()

    estimated_subscription_size_kw = _estimate_system_size_kw(request.monthly_usage_kwh)
    subscription_size_kw = request.subscription_size_kw or estimated_subscription_size_kw
    subscription_size_kw = round(max(subscription_size_kw, 0.1), 3)

    project_status = "available"
    project_reason = "Active project capacity is available"
    waitlist_timeline: Optional[str] = None
    waitlist_position: Optional[int] = None
    matched_project_count = 0
    project_name: Optional[str] = None
    project_capacity: Optional[float] = None
    remaining_capacity: Optional[int] = None
    billing_model: Optional[str] = None
    subscription_id: Optional[str] = None
    subscription_start_date: Optional[str] = None
    monthly_generation_share: Optional[float] = None

    existing_subscription = get_subscription_for_user(request.user_key)
    matching_projects = list_matching_projects(snapshot.region, snapshot.utility) if snapshot.state_code == "NY" else []

    if existing_subscription:
        project_name = str(existing_subscription["project_name"])
        project_capacity = float(existing_subscription["capacity_kw"])
        remaining_capacity = int(existing_subscription["available_slots"])
        billing_model = str(existing_subscription["billing_model"])
        subscription_id = str(existing_subscription["id"])
        subscription_start_date = str(existing_subscription["subscription_start_date"])
        monthly_generation_share = float(existing_subscription["monthly_generation_share"])
        subscription_size_kw = round(float(existing_subscription["subscription_size_kw"]), 3)
        project_reason = "Using your active subscription project"
        matched_project_count = max(len(matching_projects), 1)
    elif matching_projects:
        matched_project_count = len(matching_projects)
        selected_project = matching_projects[0]
        project_name = str(selected_project["project_name"])
        project_capacity = float(selected_project["capacity_kw"])
        remaining_capacity = int(selected_project["available_slots"])
        billing_model = str(selected_project["billing_model"])

        if request.assign_project and request.user_key:
            assigned = assign_project_to_user(
                user_key=request.user_key,
                region=snapshot.region,
                utility=snapshot.utility,
                subscription_size_kw=subscription_size_kw,
            )
            if assigned:
                project_name = str(assigned["project_name"])
                project_capacity = float(assigned["capacity_kw"])
                remaining_capacity = int(assigned["available_slots"])
                billing_model = str(assigned["billing_model"])
                subscription_id = str(assigned["id"])
                subscription_start_date = str(assigned["subscription_start_date"])
                monthly_generation_share = float(assigned["monthly_generation_share"])
                project_reason = "Project assigned and subscription created"
            else:
                project_status = "waitlist"
                project_reason = "No active capacity in region"
    else:
        project_status = "waitlist"
        project_reason = "No active capacity in region"

    if _demo_mode_enabled() and project_status == "waitlist":
        project_status = "available"
        project_reason = "Demo mode returned a realistic New York scenario"
        waitlist_timeline = None
        if not project_name:
            demo_projects = list_matching_projects("Long Island", "PSEG Long Island")
            if demo_projects:
                chosen = demo_projects[0]
                project_name = str(chosen["project_name"])
                project_capacity = float(chosen["capacity_kw"])
                remaining_capacity = int(chosen["available_slots"])
                billing_model = str(chosen["billing_model"])
                matched_project_count = len(demo_projects)

    if project_status == "waitlist":
        if request.user_key:
            waitlist_info = add_user_to_waitlist(
                user_key=request.user_key,
                region=snapshot.region,
                utility=snapshot.utility,
                monthly_usage_kwh=request.monthly_usage_kwh,
            )
            waitlist_timeline = waitlist_info["expected_timeline"]
            waitlist_position = int(waitlist_info["position_estimate"])
        else:
            waitlist_timeline = "Estimated availability: 6-12 weeks"

    simulation = _simulate_generation_billing(
        monthly_usage_kwh=request.monthly_usage_kwh,
        utility_rate=snapshot.utility_price_per_kwh,
        subscription_size_kw=subscription_size_kw,
        discount_rate=discount_rate,
    )

    if project_status == "waitlist":
        for month in simulation["monthly_breakdown"]:
            month["credit_value"] = 0.0
            month["payment"] = 0.0
            month["savings"] = 0.0
        simulation["annual_savings"] = 0.0
        simulation["average_monthly_savings"] = 0.0
        simulation["estimated_credit_value"] = 0.0
        simulation["customer_payment"] = 0.0
        simulation["savings_percent"] = 0.0

    annual_credit_value = float(simulation["estimated_credit_value"])
    annual_payment = float(simulation["customer_payment"])
    annual_savings = float(simulation["annual_savings"])
    average_monthly_savings = float(simulation["average_monthly_savings"])
    savings_percent = float(simulation["savings_percent"])

    platform_revenue = round(annual_credit_value * margin_rate, 2)
    developer_payout = round(annual_credit_value - annual_savings - platform_revenue, 2)

    recommendation_label: str = "recommended"
    low_savings_reason: Optional[str] = None
    alternatives: list[str] = []

    if annual_savings < 0:
        recommendation_label = "not_recommended"
        low_savings_reason = "Projected annual savings are negative after billing assumptions."
        alternatives = [
            "Wait for a higher-production project",
            "Increase subscription size to offset winter underproduction",
        ]
    elif savings_percent < 2.0:
        recommendation_label = "low_savings"
        low_savings_reason = "Projected savings are below 2% of annual utility spend."
        alternatives = [
            "Try a higher subscription size",
            "Review utility tariff and timing for better project fit",
        ]

    confidence_score, confidence_reason = _build_confidence_details(
        request=request,
        snapshot=snapshot,
        project_status=project_status,
        is_rate_estimated=snapshot.utility_rate_is_estimated,
    )

    recommendation_reasons = _build_recommendation_reasons(
        snapshot=snapshot,
        project_name=project_name,
        recommendation_label=recommendation_label,
    )

    assumptions = _build_assumptions(
        snapshot=snapshot,
        is_rate_estimated=snapshot.utility_rate_is_estimated,
        discount_rate=discount_rate,
    )

    if subscription_id:
        store_credit_ledger(subscription_id=subscription_id, monthly_breakdown=simulation["monthly_breakdown"])

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
        "waitlist_position": waitlist_position,
        "project_status_reason": project_reason,
        "project_name": project_name,
        "project_capacity": round(project_capacity, 2) if project_capacity is not None else None,
        "remaining_capacity": remaining_capacity,
        "factor_breakdown": _build_factor_breakdown(ranked[0]),
        "financial_breakdown": {
            "credit_value": annual_credit_value,
            "user_payment": annual_payment,
            "user_savings": annual_savings,
            "average_monthly_savings": average_monthly_savings,
            "platform_revenue": platform_revenue,
            "platform_margin": round(margin_rate, 4),
            "developer_payout": developer_payout,
            "rate_used": snapshot.utility_price_per_kwh,
            "rate_source": snapshot.utility_rate_source,
            "is_estimated": snapshot.utility_rate_is_estimated,
            "discount_rate": discount_rate,
            "system_size_kw": estimated_subscription_size_kw,
            "subscription_size_kw": subscription_size_kw,
            "rollover_credit_balance": simulation["rollover_credit_balance"],
            "savings_percent": savings_percent,
            "estimated_credit_value": annual_credit_value,
            "customer_payment": annual_payment,
            "monthly_breakdown": simulation["monthly_breakdown"],
            "annual_savings": annual_savings,
            "annual_production_kwh": simulation["annual_production_kwh"],
            "simulated_production_kwh": simulation["simulated_production_kwh"],
            "monthly_share_total": simulation["monthly_share_total"],
            "billing_model": billing_model,
            "subscription_start_date": subscription_start_date,
            "monthly_generation_share": monthly_generation_share,
            "billing_explanation": "Step 1: Solar generates credits. Step 2: Utility applies credits. Step 3: You pay discounted amount.",
            "platform_revenue_explanation": "How SolarShare makes money: developer credit value is shared between customer savings and a 2-5% platform margin.",
            "invoice_preview": {
                "utility_credits": annual_credit_value,
                "payment_due": annual_payment,
                "savings": annual_savings,
                "explanation": "Invoice summarizes utility credits, discounted payment, and net savings for the cycle.",
            },
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
        "assumptions": assumptions,
        "assumptions_used": assumptions,
    }
