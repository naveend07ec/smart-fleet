@echo off
title SMARTFLEET Backend (Port 8000)
cd /d "%~dp0backend"
echo Starting SMARTFLEET FastAPI Backend on http://127.0.0.1:8000 ...
..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
pause
