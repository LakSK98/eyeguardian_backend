@echo off
setlocal enabledelayedexpansion
title EyeGUARDIAN Vision - Launcher
echo ========================================================
echo        EyeGUARDIAN Vision - Smart Eyecare Screening
echo ========================================================
echo.

:: Ensure current working directory is the script's folder
cd /d "%~dp0"

:: 1. Check for pre-bundled portable Python (python-embed)
if exist "python-embed\python.exe" (
    set "PYTHON_EXE=python-embed\python.exe"
    goto :START_SERVER
)

:: 2. Check if local virtual environment (.venv) already exists
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto :START_SERVER
)

:: 3. Self-Bootstrapping: First-time setup on a fresh git clone
echo [First-time setup detected]
echo Checking for Python on your system...

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo  [!] Python was not found on this computer.
    echo.
    echo  To run this application via git clone:
    echo  1. Install Python 3.10+ from https://www.python.org
    echo  2. IMPORTANT: Check "Add Python to PATH" during install
    echo  3. Re-run this start.bat file
    echo ========================================================
    echo.
    pause
    exit /b 1
)

echo.
echo [1/3] Creating local virtual environment (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [!] Error: Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/3] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo [3/3] Installing dependencies from requirements.txt...
echo       (This only happens once on the very first run, please wait a moment...)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [!] Error: Failed to install dependencies. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo [Setup complete!]
echo.
set "PYTHON_EXE=.venv\Scripts\python.exe"

:START_SERVER
:: 4. Automatically open default web browser after 3 seconds
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000"

:: 5. Launch the application server
echo Starting EyeGUARDIAN Vision server on http://127.0.0.1:8000 ...
echo The web app will open automatically in your browser.
echo.
echo (Keep this window open while using the app. Press CTRL+C to stop.)
echo ========================================================
echo.

"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
