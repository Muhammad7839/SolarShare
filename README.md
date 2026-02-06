# SolarShare 🌞⚡

SolarShare is a full-stack clean-energy comparison platform that helps users choose the best local energy option based on cost, distance, reliability, and usage preferences.

The project is intentionally split into a backend decision engine and a frontend UI so team members can work independently and integrate later.

---

```## Repository Structure

SolarShare/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── logic.py
│   │   ├── data.py
│   │   └── API_CONTRACT.md
│   ├── requirements.txt
│   ├── run.sh
│   └── test_frontend.html
│
├── frontend/
│   └── .gitkeep
│
└── .gitignore
```
---

## Tech Stack

### Backend
- Python 3.9+
- FastAPI
- Uvicorn
- Pydantic

### Frontend (planned)
- React or similar modern JS framework
- Fetch / Axios for API calls

---

## Backend Overview

The backend exposes a JSON API that ranks clean-energy options and returns a best recommendation based on user input.

**Base URL (local):**

http://127.0.0.1:8000

**Swagger docs:**

http://127.0.0.1:8000/docs

---

## API Endpoints

### Health Check

**GET /**

**Response:**
``json
{
  "status": "ok",
  "message": "Solar Share backend is running",
  "version": "0.1.0"
}


⸻

POST /options

Returns all ranked energy options.

Request:

{
  "location": "Long Island, NY",
  "monthly_usage_kwh": 650,
  "priority": "lowest_cost"
}

Response (example):

[
  {
    "option": {
      "id": 1,
      "provider_name": "Local Community Solar A",
      "base_price_per_kwh": 0.18,
      "distance_miles": 2.5,
      "reliability_score": 0.92,
      "time_of_use_modifier": 0.01,
      "utility_plan_name": "Community Solar Fixed"
    },
    "effective_price": 0.186,
    "monthly_cost": 120.77,
    "savings_vs_baseline": 22.23,
    "badges": [],
    "is_recommended": true
  }
]


⸻

POST /recommendation

Returns the single best recommendation.

Request:

{
  "location": "Long Island, NY",
  "monthly_usage_kwh": 650,
  "priority": "lowest_cost"
}

Response:

{
  "recommended_option": {
    "option": {
      "id": 1,
      "provider_name": "Local Community Solar A",
      "base_price_per_kwh": 0.18,
      "distance_miles": 2.5,
      "reliability_score": 0.92,
      "time_of_use_modifier": 0.01,
      "utility_plan_name": "Community Solar Fixed"
    },
    "effective_price": 0.186,
    "monthly_cost": 120.77,
    "savings_vs_baseline": 22.23,
    "badges": [],
    "is_recommended": true
  },
  "reason": "Lowest overall cost after distance, timing, and reliability adjustments"
}


⸻

Running the Backend Locally

From the backend/ directory:

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh


⸻

Team Workflow
	•	Backend development happens in backend/
	•	Frontend development happens in frontend/
	•	Both sides communicate strictly through the API
	•	Integration happens after frontend UI is ready

⸻

Project Status
	•	Backend decision engine: complete and working
	•	API contract: stable
	•	Frontend: in progress

⸻

Notes

This project is currently a prototype for academic and demonstration purposes.
