@echo off
REM Local development launcher for starting SolarShare backend and frontend together on Windows.

setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo Starting SolarShare...

where npm >nul 2>&1
if errorlevel 1 (
  echo npm is not installed or not in PATH.
  echo Install Node.js, then run setup again.
  exit /b 1
)

if not exist "backend\venv\Scripts\activate.bat" (
  echo Missing backend virtual environment at backend\venv.
  echo Run one-time setup in backend first.
  exit /b 1
)

if not exist "frontend\node_modules" (
  echo Missing frontend dependencies at frontend\node_modules.
  echo Run one-time setup in frontend first.
  exit /b 1
)

for %%P in (8000 3000) do (
  netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul
  if !errorlevel! EQU 0 (
    echo Port %%P is already in use.
    echo Close the process using this port, then retry.
    exit /b 1
  )
)

start "SolarShare Backend" cmd /c "cd /d \"%~dp0backend\" && call venv\Scripts\activate.bat && python main.py"
start "SolarShare Frontend" cmd /c "cd /d \"%~dp0frontend\" && npm run dev"

echo Backend running on http://127.0.0.1:8000
echo Frontend running on http://localhost:3000
echo Close the two opened terminal windows to stop SolarShare.
