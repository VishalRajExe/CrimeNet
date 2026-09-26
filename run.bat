@echo off
setlocal EnableDelayedExpansion
title CrimeNet Investigation Platform

echo.
echo ======================================================
echo       CRIMENET INVESTIGATION PLATFORM
echo ======================================================
echo.

:: Move to repo root (same folder as this bat file)
cd /d "%~dp0"

:: ─── Find Python ──────────────────────────────────────────────────────────────
set "PYTHON="

:: 1. Prefer explicit AppData path (most reliable on Windows)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    echo [OK] Python 3.13 found at: !PYTHON!
    goto :python_ok
)

:: 2. Try py launcher
py --version >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PYTHON=py"
    echo [OK] Python found via py launcher.
    goto :python_ok
)

:: 3. Try python in PATH
python --version >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "PYTHON=python"
    echo [OK] Python found in PATH.
    goto :python_ok
)

echo.
echo [ERROR] Python not found.
echo         Install Python 3.13 from https://python.org
echo         or ensure it is added to PATH.
echo.
pause
exit /b 1

:python_ok
echo.

:: ─── Run DB schema migration (safe, idempotent) ──────────────────────────────
echo [..] Initialising database schema ...
"%PYTHON%" -c "import sys; sys.path.insert(0, r'%~dp0'); exec(open(r'%~dp0storage\schema_migration.py').read()); run_migration()" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    echo [OK] Database schema ready.
) else (
    echo [WARN] Schema migration skipped - SQLite fallback will be used.
)
echo.

:: ─── Start FastAPI in a background window (optional) ─────────────────────────
"%PYTHON%" -c "import uvicorn" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    echo [..] Starting FastAPI service on http://127.0.0.1:8000 ...
    start "CrimeNet API" /min "%PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
    timeout /t 2 /nobreak >nul
    echo [OK] API service window opened.
) else (
    echo [INFO] uvicorn not installed - UI will run in offline mode.
)
echo.

:: ─── Open browser after 3 seconds ────────────────────────────────────────────
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8050"

:: ─── Start Dash Visualizer (foreground) ──────────────────────────────────────
echo [OK] Starting CrimeNet Investigation UI...
echo      URL  : http://127.0.0.1:8050
echo      Stop : Press Ctrl+C in this window
echo.
echo ======================================================
echo.

"%PYTHON%" visualizer\index.py

echo.
echo [INFO] CrimeNet stopped.
pause
