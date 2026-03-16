"""Regression tests for ranking logic, API validation, and recommendation behavior."""

import sqlite3

from fastapi.testclient import TestClient

from app.main import app
import app.main as app_main
from app.schemas import UserRequest
import app.logic as logic


client = TestClient(app)


def _request(priority: str = "balanced", location: str = "New York City") -> UserRequest:
    return UserRequest(location=location, monthly_usage_kwh=600, priority=priority)


def test_lowest_cost_priority_ranks_by_effective_price() -> None:
    ranked = logic.get_ranked_options(_request(priority="lowest_cost"))
    assert ranked
    assert ranked[0].is_recommended is True
    assert ranked[0].effective_price <= ranked[1].effective_price <= ranked[2].effective_price


def test_highest_reliability_priority_ranks_by_reliability() -> None:
    ranked = logic.get_ranked_options(_request(priority="highest_reliability"))
    reliabilities = [item.option.reliability_score for item in ranked]
    assert reliabilities == sorted(reliabilities, reverse=True)
    assert ranked[0].is_recommended is True


def test_closest_distance_priority_ranks_by_distance() -> None:
    ranked = logic.get_ranked_options(_request(priority="closest_distance"))
    distances = [item.option.distance_miles for item in ranked]
    assert distances == sorted(distances)
    assert ranked[0].is_recommended is True


def test_location_affects_effective_price_distance_penalty() -> None:
    urban_ranked = logic.get_ranked_options(_request(location="Urban Boston"))
    rural_ranked = logic.get_ranked_options(_request(location="Rural Vermont"))

    urban_prices_by_id = {item.option.id: item.effective_price for item in urban_ranked}
    rural_prices_by_id = {item.option.id: item.effective_price for item in rural_ranked}

    for option_id, urban_price in urban_prices_by_id.items():
        assert rural_prices_by_id[option_id] >= urban_price


def test_get_ranked_options_handles_empty_options(monkeypatch) -> None:
    monkeypatch.setattr(logic, "ENERGY_OPTIONS", [])
    assert logic.get_ranked_options(_request()) == []


def test_get_recommendation_raises_for_empty_options(monkeypatch) -> None:
    monkeypatch.setattr(logic, "ENERGY_OPTIONS", [])
    try:
        logic.get_recommendation(_request())
    except ValueError as exc:
        assert str(exc) == "No energy options are currently available"
    else:
        assert False, "Expected ValueError for empty options list"


def test_request_validation_rejects_invalid_usage() -> None:
    response = client.post(
        "/options",
        json={"location": "New York", "monthly_usage_kwh": 0, "priority": "balanced"},
    )
    assert response.status_code == 422


def test_request_validation_rejects_invalid_priority() -> None:
    response = client.post(
        "/options",
        json={"location": "New York", "monthly_usage_kwh": 300, "priority": "fastest"},
    )
    assert response.status_code == 422


def test_request_validation_requires_location_or_zip() -> None:
    response = client.post(
        "/options",
        json={"location": "", "zip_code": "", "monthly_usage_kwh": 300, "priority": "balanced"},
    )
    assert response.status_code == 422


def test_request_validation_rejects_malformed_zip_code() -> None:
    response = client.post(
        "/options",
        json={"location": "", "zip_code": "1175A", "monthly_usage_kwh": 300, "priority": "balanced"},
    )
    assert response.status_code == 422


def test_recommendation_returns_404_when_no_options(monkeypatch) -> None:
    monkeypatch.setattr(logic, "ENERGY_OPTIONS", [])
    response = client.post(
        "/recommendation",
        json={"location": "New York", "monthly_usage_kwh": 300, "priority": "balanced"},
    )
    assert response.status_code == 404


def test_live_comparison_returns_context_and_ranked_options() -> None:
    response = client.post(
        "/live-comparison",
        json={"location": "New York City", "monthly_usage_kwh": 650, "priority": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["options"]
    assert payload["recommendation"]["recommended_option"]["is_recommended"] is True
    assert payload["market_context"]["utility_price_per_kwh"] > 0
    assert isinstance(payload["market_context"]["data_sources"], list)
    assert isinstance(payload["market_context"]["source_urls"], list)
    assert payload["market_context"]["observed_at_utc"]
    assert isinstance(payload["resolution_confidence"], float)
    assert "factor_breakdown" in payload
    assert {"price", "reliability", "distance"} <= set(payload["factor_breakdown"].keys())


def test_live_comparison_zip_resolution_returns_location_details() -> None:
    response = client.post(
        "/live-comparison",
        json={"location": "", "zip_code": "11757", "monthly_usage_kwh": 650, "priority": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    context = payload["market_context"]
    assert context["postal_code"] in ("11757", None)
    assert context["state_code"] == "NY"
    assert context["city"]


def test_site_pages_are_served() -> None:
    for route in ["/", "/about", "/methodology", "/pricing", "/contact", "/admin"]:
        response = client.get(route)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


def test_location_resolve_endpoint_returns_confidence() -> None:
    response = client.post("/location-resolve", json={"location": "", "zip_code": "11757"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_location"]
    assert payload["state_code"] == "NY"
    assert isinstance(payload["confidence"], float)
    assert payload["source"]


def test_location_resolve_rejects_malformed_zip_code() -> None:
    response = client.post("/location-resolve", json={"location": "", "zip_code": "11A57"})
    assert response.status_code == 422


def test_assistant_chat_fallback_mode_in_tests() -> None:
    response = client.post("/assistant-chat", json={"message": "How do I run comparison?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fallback"
    assert isinstance(payload["reply"], str)
    assert isinstance(payload["suggested_actions"], list)


def test_assistant_chat_rate_limit_enforced(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "ASSISTANT_RATE_LIMIT", 1)
    app_main._RATE_LIMIT_BUCKETS.clear()

    first = client.post("/assistant-chat", json={"message": "How do I run comparison?"})
    second = client.post("/assistant-chat", json={"message": "Where do I enter my ZIP?"})

    assert first.status_code == 200
    assert second.status_code == 429
    app_main._RATE_LIMIT_BUCKETS.clear()


def test_analytics_event_and_admin_summary(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    event_response = client.post(
        "/analytics/events",
        json={"event_name": "comparison_run", "page": "/", "session_id": "sess_test", "metadata": {"priority": "balanced"}},
    )
    assert event_response.status_code == 200
    assert event_response.json()["accepted"] is True

    admin_response = client.get("/admin/analytics")
    assert admin_response.status_code == 200
    summary = admin_response.json()
    assert summary["totals"]["events"] >= 1
    assert summary["by_event"]["comparison_run"] >= 1


def test_demo_request_submission_creates_lead(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    response = client.post(
        "/demo-requests",
        json={
            "name": "Jordan Miles",
            "email": "Jordan@Example.com",
            "organization": "Green Realty",
            "message": "We want a demo for our customer success team.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["received"] is True
    assert payload["lead_id"]

    with sqlite3.connect(str(ops_db_path)) as connection:
        row = connection.execute(
            "SELECT source, email_normalized, organization FROM crm_leads WHERE id = ?",
            (payload["lead_id"],),
        ).fetchone()

    assert row == ("demo_request", "jordan@example.com", "Green Realty")


def test_contact_inquiry_accepts_valid_payload() -> None:
    response = client.post(
        "/contact-inquiries",
        json={
            "name": "Amina Patel",
            "email": "amina@example.com",
            "interest": "partnership",
            "message": "Interested in piloting the advisor workflow with our customers.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["received"] is True
    assert payload["inquiry_id"]


def test_health_includes_request_id_header() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")


def test_health_includes_security_headers() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "no-referrer"
    assert "geolocation=()" in str(response.headers.get("permissions-policy"))


def test_contact_inquiry_persists_to_sqlite(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "contact_inquiries.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_CONTACT_DB_PATH", str(db_path))
    response = client.post(
        "/contact-inquiries",
        json={
            "name": "Kendra Lewis",
            "email": "kendra@example.com",
            "interest": "investor_relations",
            "message": "Please share deployment timeline and onboarding details.",
        },
    )
    assert response.status_code == 200
    inquiry_id = response.json()["inquiry_id"]

    with sqlite3.connect(str(db_path)) as connection:
        row = connection.execute(
            "SELECT name, email, interest, message FROM contact_inquiries WHERE id = ?",
            (inquiry_id,),
        ).fetchone()

    assert row == (
        "Kendra Lewis",
        "kendra@example.com",
        "investor_relations",
        "Please share deployment timeline and onboarding details.",
    )


def test_contact_inquiry_rate_limit_enforced(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "CONTACT_RATE_LIMIT", 1)
    app_main._RATE_LIMIT_BUCKETS.clear()

    payload = {
        "name": "Rate Limit User",
        "email": "ratelimit@example.com",
        "interest": "other",
        "message": "This verifies contact inquiry throttling behavior.",
    }
    first = client.post("/contact-inquiries", json=payload)
    second = client.post("/contact-inquiries", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
    app_main._RATE_LIMIT_BUCKETS.clear()


def test_live_comparison_rate_limit_enforced(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "LIVE_COMPARISON_RATE_LIMIT", 1)
    app_main._RATE_LIMIT_BUCKETS.clear()

    payload = {"location": "New York City", "monthly_usage_kwh": 650, "priority": "balanced"}
    first = client.post("/live-comparison", json=payload)
    second = client.post("/live-comparison", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429


def test_analytics_event_rejects_unsafe_event_name() -> None:
    response = client.post(
        "/analytics/events",
        json={"event_name": "<script>alert(1)</script>", "page": "/", "session_id": "sess_1", "metadata": {}},
    )
    assert response.status_code == 422
    app_main._RATE_LIMIT_BUCKETS.clear()
