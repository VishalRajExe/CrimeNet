@echo off
setlocal EnableDelayedExpansion
title CrimeNet Investigation Platform

:: ============================================================
::   CrimeNet Local Runner
::   Starts:
::     1. CrimeNet Dash Visualizer  (port 8050)
::     2. CrimeNet FastAPI Service  (port 8000)  [optional]
::   Reads ports from .env when present.
:: ============================================================

echo.
echo ======================================================
echo       CRIMENET INVESTIGATION PLATFORM
echo       Local Runner
echo ======================================================
echo.

:: ── Move to repo root ────────────────────────────────────
cd /d "%~dp0"

:: ── Read .env for VISUALIZER_PORT / AI_SERVICE_PORT ──────
set VISUALIZER_PORT=8050
set AI_SERVICE_PORT=8000

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set "line=%%A"
        if "!line!"=="VISUALIZER_PORT"  set VISUALIZER_PORT=%%B
        if "!line!"=="AI_SERVICE_PORT"  set AI_SERVICE_PORT=%%B
    )
)

:: ── Locate Python 3.13 ───────────────────────────────────
set PYTHON_CMD=

:: 1. Try py launcher
py -3.13 --version >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set PYTHON_CMD=py -3.13
    goto :python_found
)

:: 2. Try explicit AppData path
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :python_found
)

:: 3. Try default python (check it has dash)
python -c "import dash" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set PYTHON_CMD=python
    goto :python_found
)

echo [ERROR] Could not find Python 3.13 with CrimeNet dependencies installed.
echo         Install requirements with:
echo           python -m pip install -r requirements.txt
echo.
pause
goto :eof

:python_found
echo [OK] Python found: %PYTHON_CMD%
echo.

:: ── Check core dependencies ───────────────────────────────
%PYTHON_CMD% -c "import dash, plotly, dash_cytoscape" >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [WARN] Core UI dependencies missing. Installing from requirements.txt ...
    %PYTHON_CMD% -m pip install -r requirements.txt
    echo.
)

:: ── Run database schema migration (safe, idempotent) ─────
echo [..] Running schema migration (safe - adds missing tables only) ...
%PYTHON_CMD% -c "
import sys, os
sys.path.insert(0, os.getcwd())
try:
    from storage.schema_migration import run_migration
    run_migration()
    print('[OK] Schema migration complete.')
except Exception as e:
    print('[WARN] Schema migration skipped:', e)
"
echo.

:: ── Start FastAPI AI Service in background? ───────────────
set START_API=0
%PYTHON_CMD% -c "import uvicorn, fastapi" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    echo [..] Starting FastAPI AI Service on port %AI_SERVICE_PORT% (background) ...
    start "CrimeNet API Service" /min cmd /c "%PYTHON_CMD% -m uvicorn backend.main:app --host 127.0.0.1 --port %AI_SERVICE_PORT% 2>&1 | more"
    set START_API=1
    timeout /t 2 /nobreak >nul
    echo [OK] FastAPI service started (http://127.0.0.1:%AI_SERVICE_PORT%)
) else (
    echo [INFO] uvicorn/fastapi not found — API service not started.
    echo        UI runs in local-only mode with direct DB/service calls.
)
echo.

:: ── Start Dash Visualizer (foreground) ───────────────────
echo [OK] Starting CrimeNet Investigation UI on http://127.0.0.1:%VISUALIZER_PORT%
echo.
echo      Press Ctrl+C to stop the server.
echo      Close the API Service window separately if it was opened.
echo.
echo ======================================================
echo.

:: Open browser after a brief delay (fire-and-forget)
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:%VISUALIZER_PORT%"

%PYTHON_CMD% visualizer\index.py

echo.
echo [INFO] CrimeNet visualizer stopped.
echo.
pause
