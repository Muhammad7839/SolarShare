"""Regression tests for ranking logic, API validation, and recommendation behavior."""

import sqlite3

from fastapi.testclient import TestClient

from app.main import app
import app.main as app_main
from app.schemas import UserRequest
import app.logic as logic
from app.simulation_config import ANNUAL_OUTPUT_PER_KW, production_shares_sum
from app.utility_rates import get_utility_rate, list_rate_refresh_jobs, refresh_utility_rate_store


client = TestClient(app)


def _request(priority: str = "balanced", location: str = "New York City") -> UserRequest:
    return UserRequest(location=location, monthly_usage_kwh=600, priority=priority)


def _reset_idempotency_state() -> None:
    """Clear in-memory idempotency caches so tests remain isolated."""
    app_main._IDEMPOTENCY_CACHE.clear()
    app_main._IDEMPOTENCY_KEY_LOCKS.clear()


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


def test_live_comparison_supports_nassau_zip_11501() -> None:
    response = client.post(
        "/live-comparison",
        json={"location": "", "zip_code": "11501", "monthly_usage_kwh": 600, "priority": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["market_context"]["state_code"] == "NY"
    assert payload["market_context"]["region"] == "Long Island"
    assert payload["market_context"]["utility"] == "PSEG Long Island"


def test_live_comparison_includes_financial_breakdown_and_rate_metadata() -> None:
    response = client.post(
        "/live-comparison",
        json={"location": "New York City", "monthly_usage_kwh": 650, "priority": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    financial = payload["financial_breakdown"]
    assert financial["credit_value"] > 0
    assert financial["user_payment"] > 0
    assert financial["user_savings"] > 0
    assert len(financial["monthly_breakdown"]) == 12
    monthly_savings = {item["savings"] for item in financial["monthly_breakdown"]}
    assert len(monthly_savings) > 1
    assert financial["platform_revenue"] > 0
    assert financial["developer_payout"] > 0
    assert financial["annual_production_kwh"] > 0
    assert financial["monthly_share_total"] == production_shares_sum()
    assert payload["market_context"]["rate_source"]
    assert isinstance(payload["market_context"]["rate_is_estimated"], bool)
    assert isinstance(payload["confidence_reason"], list)
    assert isinstance(payload["assumptions_used"], list)


def test_waitlist_status_for_non_ny_region() -> None:
    response = client.post(
        "/live-comparison",
        json={"location": "", "zip_code": "07030", "monthly_usage_kwh": 620, "priority": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_status"] == "waitlist"
    assert payload["waitlist_timeline"]
    assert payload["matched_project_count"] == 0


def test_rollover_balance_accumulates_when_production_exceeds_usage() -> None:
    response = client.post(
        "/live-comparison",
        json={
            "location": "",
            "zip_code": "10001",
            "monthly_usage_kwh": 100,
            "priority": "balanced",
            "subscription_size_kw": 12,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    monthly = payload["financial_breakdown"]["monthly_breakdown"]
    assert any(item["rollover_balance"] > 0 for item in monthly)
    assert payload["financial_breakdown"]["rollover_credit_balance"] > 0


def test_project_assignment_reduces_available_slots() -> None:
    user_key = "test_assignment_user"
    first = client.post(
        "/live-comparison",
        json={
            "location": "",
            "zip_code": "11757",
            "monthly_usage_kwh": 650,
            "priority": "balanced",
            "assign_project": True,
            "user_key": user_key,
        },
    )
    second = client.post(
        "/live-comparison",
        json={
            "location": "",
            "zip_code": "11757",
            "monthly_usage_kwh": 650,
            "priority": "balanced",
            "user_key": user_key,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["project_name"]
    assert second.json()["project_name"] == first.json()["project_name"]


def test_dashboard_data_returns_persisted_subscription_and_savings() -> None:
    user_key = "dashboard_user_1"
    compare = client.post(
        "/live-comparison",
        json={
            "location": "",
            "zip_code": "10001",
            "monthly_usage_kwh": 620,
            "priority": "balanced",
            "assign_project": True,
            "user_key": user_key,
        },
    )
    assert compare.status_code == 200

    dashboard = client.get(f"/dashboard-data?user_key={user_key}")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["has_subscription"] is True
    assert payload["subscription_size_kw"] > 0
    assert payload["project_info"]["name"]
    assert isinstance(payload["monthly_savings"], list)
    assert isinstance(payload["billing_history"], list)


def test_location_resolve_unresolved_zip_returns_suggestions() -> None:
    response = client.post("/location-resolve", json={"location": "", "zip_code": "99999"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolution_status"] == "unresolved"
    assert len(payload["suggested_zip_codes"]) >= 1


def test_demo_mode_keeps_live_comparison_available(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    response = client.post(
        "/live-comparison",
        json={"location": "Unknown Place", "zip_code": "99999", "monthly_usage_kwh": 500, "priority": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_status"] == "available"
    assert payload["options"]


def test_utility_rate_lookup_prefers_utility_table_and_has_ny_fallback() -> None:
    coned_rate = get_utility_rate("Con Edison", "NYC")
    assert coned_rate.rate_used > 0.2
    assert coned_rate.is_estimated is False

    fallback_rate = get_utility_rate("Unknown Utility", "Unknown Region")
    assert fallback_rate.rate_used == 0.20
    assert fallback_rate.is_estimated is True


def test_utility_rate_refresh_pipeline_records_timestamped_job(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))
    monkeypatch.setenv(
        "SOLAR_SHARE_UTILITY_RATE_SOURCE_JSON",
        '[{"utility_name":"Con Edison","region":"NYC","avg_rate_per_kwh":0.301,"source":"test fixture"}]',
    )

    result = refresh_utility_rate_store()
    assert result["records_updated"] >= 1
    assert result["started_at"]
    assert result["completed_at"]

    jobs = list_rate_refresh_jobs(limit=5)
    assert len(jobs) >= 1
    assert jobs[0]["status"] in {"success", "fallback"}


def test_generation_model_annual_total_and_monthly_shape_are_consistent() -> None:
    response = client.post(
        "/live-comparison",
        json={"location": "", "zip_code": "11757", "monthly_usage_kwh": 650, "priority": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    financial = payload["financial_breakdown"]
    monthly = financial["monthly_breakdown"]

    simulated_total = round(sum(item["production_kwh"] for item in monthly), 2)
    expected_total = round(float(financial["subscription_size_kw"]) * ANNUAL_OUTPUT_PER_KW, 2)
    assert abs(simulated_total - expected_total) <= 1.5
    assert abs(financial["simulated_production_kwh"] - expected_total) <= 1.5
    jan = next(item for item in monthly if item["month"] == "Jan")
    jul = next(item for item in monthly if item["month"] == "Jul")
    assert jan["production_kwh"] < jul["production_kwh"]


def test_auth_dashboard_requires_token_and_uses_authenticated_identity(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    unauthorized = client.get("/dashboard/me")
    assert unauthorized.status_code == 401

    signup = client.post(
        "/auth/signup",
        json={"email": "customer@example.com", "password": "password123"},
    )
    assert signup.status_code == 200
    session = signup.json()
    token = session["access_token"]
    user_key = session["user"]["user_identity_key"]
    headers = {"Authorization": f"Bearer {token}"}

    empty_dashboard = client.get("/dashboard/me", headers=headers)
    assert empty_dashboard.status_code == 200
    assert empty_dashboard.json()["has_subscription"] is False

    compare = client.post(
        "/live-comparison",
        json={
            "location": "",
            "zip_code": "10001",
            "monthly_usage_kwh": 620,
            "priority": "balanced",
            "assign_project": True,
            "user_key": user_key,
        },
    )
    assert compare.status_code == 200

    dashboard = client.get("/dashboard/me", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["has_subscription"] is True
    assert dashboard.json()["auth_based"] is True


def test_auth_refresh_and_session_controls(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    signup = client.post(
        "/auth/signup",
        json={"email": "session@example.com", "password": "password123"},
        headers={"x-device-name": "macbook-pro"},
    )
    assert signup.status_code == 200
    session_payload = signup.json()
    access_token = session_payload["access_token"]
    refresh_token = session_payload["refresh_token"]
    active_session_id = session_payload["session"]["id"]

    headers = {"Authorization": f"Bearer {access_token}"}
    sessions_response = client.get("/auth/sessions", headers=headers)
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()["sessions"]
    assert len(sessions) >= 1
    assert any(item["id"] == active_session_id for item in sessions)

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["access_token"] != access_token
    assert refreshed["refresh_token"] != refresh_token

    refreshed_headers = {"Authorization": f"Bearer {refreshed['access_token']}"}
    revoke_others = client.post("/auth/sessions/revoke-others", headers=refreshed_headers)
    assert revoke_others.status_code == 200
    assert revoke_others.json()["revoked_count"] >= 0

    logout = client.post("/auth/logout", json={"refresh_token": refreshed["refresh_token"]})
    assert logout.status_code == 200
    assert logout.json()["revoked"] is True

    after_logout = client.get("/dashboard/me", headers=refreshed_headers)
    assert after_logout.status_code == 401


def test_invoice_lifecycle_update_and_download(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))
    monkeypatch.setenv("SOLAR_SHARE_ADMIN_BOOTSTRAP_TOKEN", "bootstrap-secret")

    signup = client.post(
        "/auth/signup",
        json={"email": "billing@example.com", "password": "password123"},
    )
    assert signup.status_code == 200
    session = signup.json()
    token = session["access_token"]
    user_key = session["user"]["user_identity_key"]
    headers = {"Authorization": f"Bearer {token}"}

    compare = client.post(
        "/live-comparison",
        json={
            "location": "",
            "zip_code": "11757",
            "monthly_usage_kwh": 610,
            "priority": "balanced",
            "assign_project": True,
            "user_key": user_key,
        },
    )
    assert compare.status_code == 200

    invoices_response = client.get("/billing/invoices", headers=headers)
    assert invoices_response.status_code == 200
    invoices = invoices_response.json()["invoices"]
    assert len(invoices) >= 1
    invoice_id = invoices[0]["invoice_id"]

    payment_response = client.post(
        f"/billing/invoices/{invoice_id}/pay",
        json={"payment_method_token": "demo_card"},
        headers=headers,
    )
    assert payment_response.status_code == 200
    assert payment_response.json()["status"] == "paid"

    updated_invoices = client.get("/billing/invoices", headers=headers).json()["invoices"]
    target = next(item for item in updated_invoices if item["invoice_id"] == invoice_id)
    assert target["status"] == "paid"
    assert target["billing_status"] == "paid"
    assert target["payment_provider"]
    assert target["payment_transaction_id"]

    # Customer status updates now create moderated requests.
    request_response = client.patch(
        f"/billing/invoices/{invoice_id}/status",
        json={"status": "failed"},
        headers=headers,
    )
    assert request_response.status_code == 200
    assert request_response.json()["mode"] == "admin_moderation"
    request_id = request_response.json()["request_id"]

    admin_session = client.post(
        "/auth/bootstrap-admin",
        json={"email": "admin@example.com", "password": "adminpass123"},
        headers={"x-bootstrap-token": "bootstrap-secret"},
    )
    assert admin_session.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_session.json()['access_token']}"}

    review_response = client.patch(
        f"/admin/billing/status-requests/{request_id}/review",
        json={"decision": "approve", "review_note": "Approved by operations"},
        headers=admin_headers,
    )
    assert review_response.status_code == 200

    final_invoices = client.get("/billing/invoices", headers=headers).json()["invoices"]
    final_target = next(item for item in final_invoices if item["invoice_id"] == invoice_id)
    assert final_target["status"] == "failed"

    download_response = client.get(f"/billing/invoices/{invoice_id}/download", headers=headers)
    assert download_response.status_code == 200
    assert download_response.headers.get("content-type") == "application/pdf"
    assert len(download_response.content) > 100


def test_customer_cannot_access_admin_moderation_routes(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    customer = client.post(
        "/auth/signup",
        json={"email": "rbac@example.com", "password": "password123"},
    )
    assert customer.status_code == 200
    headers = {"Authorization": f"Bearer {customer.json()['access_token']}"}

    queue = client.get("/admin/billing/status-requests", headers=headers)
    assert queue.status_code == 403


def test_root_returns_api_status_json() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_routes_require_password_header(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_admin_pw")
    admin_page = client.get("/admin")
    admin_summary = client.get("/admin/analytics")
    assert admin_page.status_code == 401
    assert admin_summary.status_code == 401


def test_admin_routes_reject_invalid_password_header(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_admin_pw")
    headers = {"x-admin-password": "wrong_password"}
    assert client.get("/admin", headers=headers).status_code == 401
    assert client.get("/admin/analytics", headers=headers).status_code == 401


def test_admin_routes_fail_when_password_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert client.get("/admin").status_code == 500
    assert client.get("/admin/analytics").status_code == 500


def test_admin_routes_accept_valid_password_header(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_admin_pw")
    headers = {"x-admin-password": "secret_admin_pw"}
    admin_page = client.get("/admin", headers=headers)
    admin_summary = client.get("/admin/analytics", headers=headers)
    assert admin_page.status_code == 200
    assert admin_page.json()["message"] == "Admin API access granted"
    assert admin_summary.status_code == 200
    assert "totals" in admin_summary.json()


def test_backend_static_route_is_not_exposed(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_admin_pw")
    assert client.get("/static/admin.html").status_code == 404
    assert client.get("/static/admin.html", headers={"x-admin-password": "secret_admin_pw"}).status_code == 404


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
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_admin_pw")

    event_response = client.post(
        "/analytics/events",
        json={"event_name": "comparison_run", "page": "/", "session_id": "sess_test", "metadata": {"priority": "balanced"}},
    )
    assert event_response.status_code == 200
    assert event_response.json()["accepted"] is True

    admin_response = client.get("/admin/analytics", headers={"x-admin-password": "secret_admin_pw"})
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


def test_contact_inquiry_same_idempotency_key_returns_cached_response(tmp_path, monkeypatch) -> None:
    _reset_idempotency_state()
    contact_db_path = tmp_path / "contact_inquiries.sqlite3"
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_CONTACT_DB_PATH", str(contact_db_path))
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    payload = {
        "name": "Sami Rivera",
        "email": "sami@example.com",
        "interest": "partnership",
        "message": "Need details about integration timelines and onboarding windows.",
    }
    headers = {"Idempotency-Key": "contact-idem-1"}

    first = client.post("/contact-inquiries", json=payload, headers=headers)
    second = client.post("/contact-inquiries", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    with sqlite3.connect(str(contact_db_path)) as connection:
        total = connection.execute("SELECT COUNT(*) FROM contact_inquiries").fetchone()[0]
    assert total == 1


def test_contact_inquiry_different_idempotency_keys_create_separate_records(tmp_path, monkeypatch) -> None:
    _reset_idempotency_state()
    contact_db_path = tmp_path / "contact_inquiries.sqlite3"
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_CONTACT_DB_PATH", str(contact_db_path))
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    payload = {
        "name": "Sami Rivera",
        "email": "sami@example.com",
        "interest": "partnership",
        "message": "Need details about integration timelines and onboarding windows.",
    }
    first = client.post("/contact-inquiries", json=payload, headers={"Idempotency-Key": "contact-idem-a"})
    second = client.post("/contact-inquiries", json=payload, headers={"Idempotency-Key": "contact-idem-b"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["inquiry_id"] != first.json()["inquiry_id"]

    with sqlite3.connect(str(contact_db_path)) as connection:
        total = connection.execute("SELECT COUNT(*) FROM contact_inquiries").fetchone()[0]
    assert total == 2


def test_contact_inquiry_returns_success_when_crm_and_analytics_fail(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "contact_inquiries.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_CONTACT_DB_PATH", str(db_path))
    monkeypatch.setattr(app_main, "insert_crm_lead", lambda **_: (_ for _ in ()).throw(RuntimeError("crm down")))
    monkeypatch.setattr(app_main, "insert_analytics_event", lambda **_: (_ for _ in ()).throw(RuntimeError("analytics down")))

    response = client.post(
        "/contact-inquiries",
        json={
            "name": "Jordan Hayes",
            "email": "jordan@example.com",
            "interest": "other",
            "message": "Need support while moving to a new billing cycle.",
        },
    )
    assert response.status_code == 200
    inquiry_id = response.json()["inquiry_id"]

    with sqlite3.connect(str(db_path)) as connection:
        row = connection.execute("SELECT id FROM contact_inquiries WHERE id = ?", (inquiry_id,)).fetchone()
    assert row is not None


def test_contact_inquiry_returns_500_when_primary_db_write_fails(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "insert_contact_inquiry", lambda **_: (_ for _ in ()).throw(RuntimeError("db down")))
    response = client.post(
        "/contact-inquiries",
        json={
            "name": "Primary Failure",
            "email": "primary@example.com",
            "interest": "other",
            "message": "This should fail before side effects run.",
        },
    )
    assert response.status_code == 500


def test_demo_request_returns_success_when_analytics_fails(tmp_path, monkeypatch) -> None:
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))
    monkeypatch.setattr(app_main, "insert_analytics_event", lambda **_: (_ for _ in ()).throw(RuntimeError("analytics down")))

    response = client.post(
        "/demo-requests",
        json={
            "name": "Taylor North",
            "email": "taylor@example.com",
            "organization": "Solar Ops",
            "message": "Please schedule a walkthrough of the customer onboarding setup.",
        },
    )
    assert response.status_code == 200
    lead_id = response.json()["lead_id"]

    with sqlite3.connect(str(ops_db_path)) as connection:
        row = connection.execute("SELECT id FROM crm_leads WHERE id = ?", (lead_id,)).fetchone()
    assert row is not None


def test_demo_request_same_idempotency_key_returns_cached_response(tmp_path, monkeypatch) -> None:
    _reset_idempotency_state()
    ops_db_path = tmp_path / "ops_analytics.sqlite3"
    monkeypatch.setenv("SOLAR_SHARE_OPS_DB_PATH", str(ops_db_path))

    payload = {
        "name": "Taylor North",
        "email": "taylor@example.com",
        "organization": "Solar Ops",
        "message": "Please schedule a walkthrough of the customer onboarding setup.",
    }
    headers = {"Idempotency-Key": "demo-idem-1"}
    first = client.post("/demo-requests", json=payload, headers=headers)
    second = client.post("/demo-requests", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    with sqlite3.connect(str(ops_db_path)) as connection:
        total = connection.execute("SELECT COUNT(*) FROM crm_leads WHERE source = 'demo_request'").fetchone()[0]
    assert total == 1


def test_demo_request_returns_500_when_primary_db_write_fails(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "insert_crm_lead", lambda **_: (_ for _ in ()).throw(RuntimeError("db down")))
    response = client.post(
        "/demo-requests",
        json={
            "name": "Primary Failure",
            "email": "primary@example.com",
            "organization": "Org",
            "message": "This should fail before side effects run for demo flow.",
        },
    )
    assert response.status_code == 500


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
