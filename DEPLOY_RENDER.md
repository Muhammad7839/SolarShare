<!-- Deployment runbook for production split hosting: Vercel frontend + Render backend. -->
# SolarShare Deployment Runbook (Vercel + Render)

This repository is set up for a split deployment:

- Frontend (Next.js): Vercel
- Backend (FastAPI): Render

## 1) Deploy backend to Render

1. Push your branch to GitHub.
2. In Render, create a new **Blueprint** service from this repo.
3. Confirm Render picks up [`render.yaml`](/Users/muhammad/Development/SolarShare/render.yaml).
4. Deploy, then copy backend URL (example: `https://solarshare-api.onrender.com`).

## 2) Deploy frontend to Vercel

1. Import the same repo in Vercel.
2. Set **Root Directory** to `frontend`.
3. Add environment variable:
   - `NEXT_PUBLIC_API_BASE_URL=https://solarshare-api.onrender.com`
4. Deploy and copy frontend URL (example: `https://solarshare-web.vercel.app`).

## 3) Set backend CORS for frontend domain

In Render service environment variables, set:

`SOLAR_SHARE_CORS_ORIGINS=https://solarshare-web.vercel.app,http://localhost:3000,http://127.0.0.1:3000`

Replace `solarshare-web.vercel.app` with your real Vercel domain.

## 4) Smoke test checklist

1. Open frontend home page and verify navigation/animations.
2. Open Product page and submit a comparison.
3. Open Contact page and submit a test inquiry.
4. Verify backend health endpoint:
   - `GET https://solarshare-api.onrender.com/health`
5. Confirm browser network calls succeed for:
   - `POST /live-comparison`
   - `POST /contact-inquiries`

## 5) Rollback safety

1. Keep latest known-good deployment in Vercel and Render.
2. Roll back frontend in Vercel if UI release causes regressions.
3. Roll back backend in Render if API failures appear.
