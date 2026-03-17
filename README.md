# SolarShare

## 1. Project Overview
SolarShare is a full-stack startup project for community-solar decision support. It combines a FastAPI backend (recommendation, intake, analytics) with a Next.js frontend (customer-facing web app).

## 2. Tech Stack
- Backend: Python, FastAPI, Pydantic, SQLite, Uvicorn, pytest
- Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS
- Runtime config: `.env` files for backend and frontend

## 3. Project Structure
```text
SolarShare/
├── backend/      # FastAPI API, persistence helpers, tests
├── frontend/     # Next.js web application
├── docs/         # Supporting documentation
└── scripts/      # Utility scripts
```

## 4. Prerequisites
- Python: 3.9+
- Node.js: 18+
- npm: 9+

## 5. Backend Setup

### Mac
```bash
cd backend
cp .env.example .env
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows
Command Prompt:
```bat
cd backend
copy .env.example .env
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell:
```powershell
cd backend
Copy-Item .env.example .env
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Frontend Setup

### Mac
```bash
cd frontend
cp .env.example .env.local
npm install
```

### Windows
Command Prompt:
```bat
cd frontend
copy .env.example .env.local
npm install
```

PowerShell:
```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
```

## 7. Running the App
Start backend and frontend in separate terminals.

Backend:
```bash
cd backend
# activate venv first
python main.py
```

Frontend:
```bash
cd frontend
npm run dev
```

Local URLs:
- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`

## 8. Environment Variables

### Backend (`backend/.env`)
Create from `backend/.env.example`. Common keys:
- `ADMIN_PASSWORD` (required for admin endpoints)
- `SOLAR_SHARE_CORS_ORIGINS`
- `SOLAR_SHARE_HOST`, `SOLAR_SHARE_PORT`, `SOLAR_SHARE_RELOAD`
- `SOLAR_SHARE_CONTACT_DB_PATH`, `SOLAR_SHARE_OPS_DB_PATH`
- `SOLAR_SHARE_IDEMPOTENCY_TTL_SECONDS` (duplicate-submit protection window)

The backend now auto-loads `backend/.env` when started with `python main.py`.

### Frontend (`frontend/.env.local`)
Create from `frontend/.env.example`.
- `NEXT_PUBLIC_API_BASE_URL` (for non-local backend URLs)

## 9. Common Errors + Fixes
- `address already in use`: Port 8000 or 3000 is occupied. Stop the other process or change ports.
- PowerShell activation blocked: run `Set-ExecutionPolicy -Scope Process Bypass` and retry `Activate.ps1`.
- Frontend cannot reach backend: verify backend is running and `NEXT_PUBLIC_API_BASE_URL` is correct.

## 10. One-command quick start (optional)
No cross-platform single command is included in this repo to avoid shell-specific behavior. Use the setup and run commands above for reliable Mac/Windows startup.

## Verification Commands
Backend tests:
```bash
cd backend
pytest -q
```

Frontend production build:
```bash
cd frontend
npm run build
```
