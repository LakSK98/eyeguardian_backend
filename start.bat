@echo off
setlocal enabledelayedexpansion
title EyeGUARDIAN Vision - Launcher
echo ========================================================
echo        EyeGUARDIAN Vision - Smart Eyecare Screening
echo ========================================================
echo.

:: Ensure current working directory is this script's directory
cd /d "%~dp0"

:: 1. Check if pre-configured portable Python already exists with dependencies
if exist "python-embed\Scripts\uvicorn.exe" (
    set "PYTHON_EXE=python-embed\python.exe"
    goto :START_SERVER
)

:: 2. Check if local virtual environment (.venv) already exists with dependencies
if exist ".venv\Scripts\uvicorn.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto :START_SERVER
)


:: 3. Neither exists -> Check if system Python is installed
echo [First-time setup detected]
echo Checking for Python on this computer...

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo System Python detected. Setting up local virtual environment...
    echo.
    echo [1/3] Creating virtual environment (.venv)...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [!] Failed to create .venv with system Python. Switching to auto-download...
        goto :AUTO_DOWNLOAD_PYTHON
    )

    echo [2/3] Upgrading pip...
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet

    echo [3/3] Installing dependencies from requirements.txt...
    echo       (This only happens once on the very first run, please wait...)
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [!] Error installing dependencies.
        pause
        exit /b 1
    )

    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto :START_SERVER
)

:AUTO_DOWNLOAD_PYTHON
:: 4. Python is NOT installed -> Automatically download portable Python 3.10!
echo.
echo ========================================================
echo  No Python installation found on this computer.
echo  Auto-downloading portable Python 3.10 (Zero-Install)...
echo ========================================================
echo.

if not exist "python-embed" mkdir "python-embed"

echo [1/4] Downloading official portable Python 3.10 (~10 MB)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip', 'python-embed.zip')"
if %errorlevel% neq 0 (
    echo [!] Failed to download Python. Please check your internet connection.
    pause
    exit /b 1
)

echo [2/4] Extracting portable Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path 'python-embed.zip' -DestinationPath 'python-embed' -Force"
del /f /q python-embed.zip 2>nul

:: Enable pip and site-packages in python310._pth
echo [3/4] Configuring portable Python environment...
(
    echo python310.zip
    echo .
    echo Lib\site-packages
    echo import site
) > python-embed\python310._pth

:: Download get-pip.py and bootstrap pip
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'python-embed\get-pip.py')"
python-embed\python.exe python-embed\get-pip.py --no-warn-script-location --quiet
del /f /q python-embed\get-pip.py 2>nul

echo [4/4] Installing dependencies from requirements.txt...
echo       (TensorFlow, OpenCV, FastAPI, etc. This takes 1-2 minutes on first run...)
python-embed\python.exe -m pip install -r requirements.txt --no-warn-script-location
if %errorlevel% neq 0 (
    echo [!] Error installing dependencies into portable environment.
    pause
    exit /b 1
)

set "PYTHON_EXE=python-embed\python.exe"
echo.
echo [Setup Complete! Portable environment is ready.]
echo.

:START_SERVER
:: 5. Launch default browser after 3 seconds
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000"

:: 6. Launch Uvicorn Server
echo ========================================================
echo Starting EyeGUARDIAN Vision server on http://127.0.0.1:8000 ...
echo The web app will open automatically in your browser.
echo.
echo (Keep this window open while using the app. Press CTRL+C to stop.)
echo ========================================================
echo.

"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
