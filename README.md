# SolarShare

SolarShare is a full-stack SaaS-style platform for community-solar comparison. It includes a Next.js frontend and a FastAPI backend for recommendations, location resolution, contact/demo intake, analytics tracking, and admin funnel visibility.

## Tech Stack

- Backend: FastAPI, Pydantic, SQLite, Uvicorn
- Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS
- Tooling: pytest, ESLint

## Repository Structure

- `backend/`: FastAPI service and backend tests
- `backend/app/`: API routes, schemas, business logic, persistence helpers
- `frontend/`: Next.js web app
- `docs/`: supporting project notes
- `scripts/`: local utility scripts

## Local Setup (Fresh Clone)

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm 9+

### Backend

From repository root:

```bash
cd backend
python3 -m venv venv
```

Activate virtual environment:

- macOS/Linux:

```bash
source venv/bin/activate
```

- Windows (PowerShell):

```powershell
py -3 -m venv venv
venv\Scripts\Activate.ps1
```

Install dependencies and run:

```bash
pip install -r requirements.txt
python3 main.py
```

Alternative run command:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend URL: `http://127.0.0.1:8000`

### Frontend

From repository root:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:3000`

## Environment Variables

### Backend

- `ADMIN_PASSWORD` (required for `/admin` and `/admin/analytics`)
- `SOLAR_SHARE_CORS_ORIGINS` (comma-separated allowed origins)
- `SOLAR_SHARE_TRUST_PROXY_HEADERS` (`1` to trust `x-forwarded-for`)
- `SOLAR_SHARE_RATE_LIMIT_WINDOW_SECONDS`
- `SOLAR_SHARE_RATE_LIMIT_LIVE_COMPARISON_PER_MIN`
- `SOLAR_SHARE_RATE_LIMIT_CONTACT_PER_MIN`
- `SOLAR_SHARE_RATE_LIMIT_ASSISTANT_PER_MIN`
- `SOLAR_SHARE_RATE_LIMIT_ANALYTICS_PER_MIN`
- `SOLAR_SHARE_CONTACT_DB_PATH`
- `SOLAR_SHARE_OPS_DB_PATH`
- `SOLAR_SHARE_REAL_DATA_DISABLE_NETWORK`
- `SOLAR_SHARE_ASSISTANT_DISABLE_NETWORK`
- `SOLAR_SHARE_AI_API_KEY`
- `SOLAR_SHARE_AI_BASE_URL`
- `SOLAR_SHARE_AI_MODEL`
- `SOLAR_SHARE_EIA_API_KEY`

### Frontend

- `NEXT_PUBLIC_API_BASE_URL` (backend base URL for non-local deployment)

## Run Quality Checks

### Backend tests

```bash
cd backend
pytest -q
```

### Frontend lint/build

```bash
cd frontend
npm run lint
npm run build
```

## Admin Access

Admin endpoints are protected with `x-admin-password`:

- `GET /admin`
- `GET /admin/analytics`

Set `ADMIN_PASSWORD`, then send the same value in the request header.

## API Contract

See `backend/app/API_CONTRACT.md`.
