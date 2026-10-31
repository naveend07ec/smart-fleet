# ==============================================================================
# SmartFleet Operations System - One-Click Launcher (PowerShell)
# ==============================================================================

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Starting Quantum-Safe IoT Smart Fleet Management System        " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan

$RootDir = $PSScriptRoot

# 1. Virtual Environment Validation
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
$VenvUvicorn = Join-Path $RootDir ".venv\Scripts\uvicorn.exe"
$VenvAlembic = Join-Path $RootDir ".venv\Scripts\alembic.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[!] Virtual environment not detected at .venv. Creating..." -ForegroundColor Yellow
    python -m venv .venv
    & .\.venv\Scripts\pip.exe install -r backend\requirements.txt
}

# 2. Database Migrations & Seeding
Write-Host "[1/3] Running database migrations..." -ForegroundColor Blue
& $VenvAlembic -c backend\alembic.ini upgrade head

Write-Host "[2/3] Verifying fleet seed data..." -ForegroundColor Blue
& $VenvPython backend\seed.py

# 3. Launch Backend & Frontend in separate windows
Write-Host "[3/3] Launching FastAPI Backend (Port 8000) & Vite Frontend (Port 5173)..." -ForegroundColor Green

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RootDir\backend'; & '$VenvUvicorn' app.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RootDir\frontend'; npm run dev"

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  System Successfully Launched!                                  " -ForegroundColor Green
Write-Host "  • Web Dashboard:     http://localhost:5173                     " -ForegroundColor White
Write-Host "  • Backend API Docs:  http://127.0.0.1:8000/api/docs            " -ForegroundColor White
Write-Host "  • Health Check:      http://127.0.0.1:8000/api/health          " -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
