<!-- Deployment runbook for production split hosting: Vercel frontend + Render backend. -->
# SolarShare Deployment Runbook (Render + Vercel)

This project is deployed as:
- Backend (FastAPI): Render
- Frontend (Next.js): Vercel

## 1) Backend deployment on Render

Use these exact values:
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
- Health Check Path: `/health`

Required backend environment variable:
- `SOLAR_SHARE_CORS_ORIGINS=https://<your-vercel-domain>,http://localhost:3000,http://127.0.0.1:3000`

Optional but recommended:
- `ADMIN_PASSWORD=<secure-value>`

## 2) Frontend deployment on Vercel

Use these exact values:
- Root Directory: `frontend`
- Framework Preset: Next.js

Required frontend environment variable:
- `NEXT_PUBLIC_API_BASE_URL=https://<your-render-backend-domain>`

## 3) Post-deploy smoke tests

1. Open frontend URL and confirm home page loads.
2. Run product flow and verify comparison request succeeds.
3. Verify backend health endpoint:
   - `GET https://<your-render-backend-domain>/health`
4. Verify API root endpoint:
   - `GET https://<your-render-backend-domain>/`
5. Confirm browser network calls succeed for:
   - `POST /live-comparison`
   - `POST /contact-inquiries`

## 4) Common failure fixes

- Render ASGI error `Attribute "app" not found in module "main"`:
  - Use `app.main:app` in the start command.
- Frontend `Failed to fetch`:
  - Confirm `NEXT_PUBLIC_API_BASE_URL` points to the live Render backend.
- CORS errors:
  - Add the Vercel domain to `SOLAR_SHARE_CORS_ORIGINS` on Render.
