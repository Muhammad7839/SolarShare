# SolarShare

## Project Overview
SolarShare is a full-stack app with a FastAPI backend and a Next.js frontend.
The backend is API-only, and the frontend is the full user-facing web interface.

## Tech Stack
- Backend: FastAPI, Uvicorn, Python
- Frontend: Next.js, React, TypeScript
- Deployment: Render (backend) + Vercel (frontend)

## Project Structure
```text
SolarShare/
├── backend/        # FastAPI API service
├── frontend/       # Next.js UI
├── run.sh          # One-command local run (Mac/Linux)
├── run.bat         # One-command local run (Windows)
└── stop.sh         # Stop local dev processes (Mac/Linux)
```

## Quick Start (Beginner Friendly)

### 1) Clone the repository
```bash
git clone <YOUR_REPO_URL>
cd SolarShare
```

### 2) One-time setup

Backend (Mac/Linux):
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Backend (Windows Command Prompt):
```bat
cd backend
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Frontend (Mac/Linux + Windows):
```bash
cd ../frontend
cp .env.example .env.local
npm install
```

Windows Command Prompt copy command:
```bat
copy .env.example .env.local
```

### 3) Run the full app with one command

Mac/Linux:
```bash
./run.sh
```

Windows Command Prompt:
```bat
run.bat
```

Local URLs:
- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`

## Manual Run (Fallback)
Use two terminals.

Terminal 1 (backend):
```bash
cd backend
source venv/bin/activate
python main.py
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

## Environment Variables

Frontend (`frontend/.env.local`):
```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Production frontend value should be your Render backend URL, for example:
```bash
NEXT_PUBLIC_API_BASE_URL=https://solarshare-api.onrender.com
```

Backend (`backend/.env`): copy from `backend/.env.example` if needed.

## Deployment (Render + Vercel)

### Backend on Render
Use these exact settings:
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
- Health Check Path: `/health`

Important env var on Render:
- `SOLAR_SHARE_CORS_ORIGINS=https://<your-vercel-domain>,http://localhost:3000,http://127.0.0.1:3000`

### Frontend on Vercel
Use these exact settings:
- Root Directory: `frontend`
- Framework: Next.js
- Environment Variable:
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-render-backend-domain>`

## Troubleshooting
- Render ASGI error `Attribute "app" not found in module "main"`:
  - Use `uvicorn app.main:app --host 0.0.0.0 --port 10000`.
- Frontend `Failed to fetch`:
  - Confirm backend is running and `NEXT_PUBLIC_API_BASE_URL` is correct.
- CORS errors:
  - Ensure your Vercel domain is included in `SOLAR_SHARE_CORS_ORIGINS` on Render.
- Port already in use:
  - Stop old processes and rerun (`./stop.sh` on Mac/Linux).
