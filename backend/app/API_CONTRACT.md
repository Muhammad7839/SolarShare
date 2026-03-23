Solar Share Backend – API Contract (v1)

Base URL:
http://127.0.0.1:8000

GET /health
Description:
Returns service health metadata for monitoring.
Includes response header `X-Request-ID` for request tracing.
Includes baseline security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).

GET /
Description:
Returns backend API status only.
Response:
{
  "message": "SolarShare API running"
}

GET /admin
Description:
Returns protected admin API status payload.
Requires request header `x-admin-password` matching `ADMIN_PASSWORD`.
Returns `401` when missing or incorrect.

POST /live-comparison
Description:
Returns ranked options, recommendation, savings realism, confidence explanations, and live market context in a single payload.
Rate limited per client IP.

Response:
{
  "options": [ScoredOptionSchema],
  "recommendation": {
    "recommended_option": ScoredOptionSchema,
    "reason": string,
    "reasons": [string]
  },
  "project_status": "available" | "waitlist",
  "project_status_reason": string,
  "waitlist_timeline": string | null,
  "matched_project_count": number,
  "financial_breakdown": {
    "credit_value": number,
    "user_payment": number,
    "user_savings": number,
    "platform_revenue": number,
    "platform_margin": number,
    "developer_payout": number,
    "rate_used": number,
    "rate_source": string,
    "is_estimated": boolean
  },
  "confidence_score": number,
  "confidence_reason": [string],
  "recommendation_label": "recommended" | "low_savings" | "not_recommended",
  "low_savings_reason": string | null,
  "alternatives": [string],
  "platform_highlights": [string],
  "resolution_confidence": number,
  "fallback_reason": string | null,
  "factor_breakdown": {
    "price": number,
    "reliability": number,
    "distance": number
  },
  "market_context": {
    "resolved_location": string,
    "city": string | null,
    "county": string | null,
    "state_code": string | null,
    "postal_code": string | null,
    "country_code": string | null,
    "region": string | null,
    "utility": string | null,
    "latitude": number,
    "longitude": number,
    "utility_price_per_kwh": number,
    "utility_rate_period": string | null,
    "rate_source": string,
    "rate_is_estimated": boolean,
    "avg_shortwave_radiation": number,
    "avg_cloud_cover_pct": number,
    "data_sources": [string],
    "source_urls": [string],
    "observed_at_utc": string,
    "using_fallback": boolean
  }
}

POST /location-resolve
Description:
Resolves location/ZIP into normalized geography metadata for pre-submit preview and confidence display.

Request:
{
  "location": string (optional, max 120),
  "zip_code": string (optional, 5-digit or ZIP+4)
}

Response:
{
  "resolved_location": string,
  "city": string | null,
  "county": string | null,
  "state_code": string | null,
  "postal_code": string | null,
  "region": string | null,
  "utility": string | null,
  "country_code": string | null,
  "latitude": number,
  "longitude": number,
  "confidence": number,
  "using_fallback": boolean,
  "resolution_status": "resolved" | "unresolved",
  "suggested_zip_codes": [string],
  "source": string
}

POST /assistant-chat
Description:
Returns assistant guidance for navigation and product usage.
Uses AI when configured, with deterministic fallback mode.

Request:
{
  "message": string,
  "page": string | null,
  "context": object
}

Response:
{
  "reply": string,
  "mode": "ai" | "fallback",
  "suggested_actions": [string]
}

POST /analytics/events
Description:
Accepts anonymous frontend instrumentation events for conversion funnel tracking.

Validation:
- `event_name` is normalized to lowercase and must match `[a-z0-9_.:-]{2,120}`.
- `page` and `session_id` reject unsupported characters.

GET /admin/analytics
Description:
Returns aggregate operations metrics, event counts, and funnel drop-off summary.
Requires request header `x-admin-password` matching `ADMIN_PASSWORD`.
Returns `401` when missing or incorrect.

POST /demo-requests
Description:
Accepts demo requests and normalizes payload into CRM-ready lead storage.
The lead record is persisted first as source of truth.
Analytics forwarding runs as a best-effort side effect and does not fail the request.
Supports optional `Idempotency-Key` request header to prevent duplicate writes.

POST /contact-inquiries
Description:
Accepts validated inquiry submissions from the contact page.
Persists inquiries to SQLite-backed storage and is rate limited per client IP.
Inquiry persistence is treated as source of truth.
CRM and analytics forwarding run as best-effort side effects and do not fail the request.
Supports optional `Idempotency-Key` request header to prevent duplicate writes.

Request:
{
  "name": "Amina Patel",
  "email": "amina@example.com",
  "interest": "partnership",
  "message": "Interested in piloting the advisor workflow with our customers."
}

POST /options
Description:
Returns all local clean energy options ranked based on user priority.

Request Body:
{
  "location": string (optional, max 120),
  "zip_code": string (optional, 5-digit or ZIP+4),
  "monthly_usage_kwh": number (> 0),
  "priority": "balanced" | "lowest_cost" | "highest_reliability" | "closest_distance"
}

Notes:
- At least one of `location` or `zip_code` is required.
- `location` text influences how strongly distance affects adjusted pricing.
- `priority` controls final ranking order and recommendation reason.

Response:
[
  {
    "option": {
      "id": number,
      "provider_name": string,
      "base_price_per_kwh": number,
      "distance_miles": number,
      "reliability_score": number,
      "time_of_use_modifier": number,
      "utility_plan_name": string
    },
    "effective_price": number,
    "monthly_cost": number,
    "savings_vs_baseline": number,
    "badges": [string],
    "is_recommended": boolean
  }
]

POST /recommendation
Description:
Returns the single best recommended clean energy option.

Request Body:
Same as /options

Response:
{
  "recommended_option": (same structure as /options item),
  "reason": string
}

Errors:
- 404 when no energy options are currently available.
- 429 when per-client rate limits are exceeded on public POST endpoints.
