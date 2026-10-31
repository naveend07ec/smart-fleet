@echo off
title SMARTFLEET Frontend (Port 5173)
cd /d "%~dp0frontend"
echo Starting SMARTFLEET React Dashboard on http://localhost:5173 ...
npm run dev
pause
