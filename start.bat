@echo off
title INNERCORE — Sovereign Command Center
cls
echo ======================================================================
echo                 INNERCORE — SOVEREIGN COMMAND CENTER
echo           Air-gapped on-premise AI & Cryptographic Audit
echo ======================================================================
echo.

cd /d "%~dp0backend"

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

echo [2/3] Checking dependencies...
pip install -r Requirements.txt --quiet --no-warn-script-location

echo [3/3] Starting Sovereign Server on port 8000...
echo.
echo ======================================================================
echo  * Landing Page:    http://127.0.0.1:8000/
echo  * Command Center:  http://127.0.0.1:8000/command-center.html
echo  * API Health:      http://127.0.0.1:8000/api/health
echo ======================================================================
echo.
echo Opening Command Center in default browser...
start http://127.0.0.1:8000/command-center.html

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
