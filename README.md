# SolarShare Repository

This repository contains the SolarShare website and API used for community-solar comparison, location resolution, contact capture, analytics events, and admin funnel visibility.

## Project Layout

- `frontend/`  
  Next.js website (customer/investor pages, guided comparison UI, assistant widget, cinematic/light theme).
- `backend/`  
  FastAPI service (comparison engine, location resolution, assistant endpoint, analytics/contact/demo APIs, SQLite persistence).
- `backend/app/static/`  
  Static fallback web app served by FastAPI for single-service deployment scenarios.
- `docs/`  
  Supporting notes and local skill integration references.
- `scripts/`  
  Utility scripts used for local workflows.

## Architecture Summary

- Frontend calls backend API endpoints:
  - `POST /live-comparison`
  - `POST /location-resolve`
  - `POST /assistant-chat`
  - `POST /contact-inquiries`
  - `POST /analytics/events`
  - `POST /demo-requests`
- Backend stores:
  - Contact records in `contact_inquiries.sqlite3`
  - Analytics + CRM leads in `ops_analytics.sqlite3`
- Backend includes:
  - Request validation via Pydantic schemas
  - Per-endpoint rate limiting
  - Structured request/event logging
  - Deterministic fallback behavior when external APIs are unavailable

## Local Development

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm

### 1) Run backend

```bash
cd backend
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

### 2) Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:3000`

## Environment Variables

### Backend

- `SOLAR_SHARE_CORS_ORIGINS` (comma-separated allowed origins)
- `SOLAR_SHARE_TRUST_PROXY_HEADERS` (`1` to trust `x-forwarded-for` from a known proxy)
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

- `NEXT_PUBLIC_API_BASE_URL`  
  Set this to the backend URL for non-local deployment.

## Quality Checks

### Backend tests

```bash
cd backend
pytest -q
```

### Frontend checks

```bash
cd frontend
npm run lint
npm run build
```

## Security and Reliability Notes

- Analytics event identifiers are validated to safe token formats.
- Admin analytics rendering escapes HTML to avoid injection from untrusted event content.
- API responses include baseline security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`).
- Rate limiting defaults are enabled on public write-heavy endpoints.

## API Contract

See `backend/app/API_CONTRACT.md` for request/response examples.

## Deployment

- Frontend can be deployed to Vercel (`frontend/vercel.json`).
- Backend can be deployed to Render (`render.yaml` / `DEPLOY_RENDER.md`).
- For split deployment, set frontend `NEXT_PUBLIC_API_BASE_URL` to the backend domain.
