Solar Share Backend – API Contract (v1)

Base URL:
http://127.0.0.1:8000

POST /options
Description:
Returns all local clean energy options ranked by effective price.

Request Body:
{
  "location": string,
  "monthly_usage_kwh": number,
  "priority": string
}

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