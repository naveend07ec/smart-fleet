@echo off
title Setup SMARTFLEET Database (Aiven / Local)
cd /d "%~dp0backend"
echo =================================================================
echo   Setting up SMARTFLEET Database Tables and Initial Fleet Data
echo =================================================================
echo.
echo [1/2] Running Alembic Database Migrations...
..\.venv\Scripts\alembic.exe -c alembic.ini upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Migration failed. Please check your DATABASE_URL in .env!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Seeding Initial Fleet Vehicles and Default Profiles...
..\.venv\Scripts\python.exe seed.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Seeding failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo =================================================================
echo   Database Setup Completed Successfully!
echo =================================================================
pause
