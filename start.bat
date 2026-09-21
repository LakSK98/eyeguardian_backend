@echo off
setlocal
title EyeGUARDIAN Vision - Launcher

echo ========================================================
echo        EyeGUARDIAN Vision - Smart Eyecare Screening
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Check for pre-configured portable Python
if exist "python-embed\python.exe" (
    if exist "python-embed\Scripts\uvicorn.exe" (
        set "PYTHON_EXE=python-embed\python.exe"
        goto :START_SERVER
    )
)

:: 2. Check for local virtual environment with uvicorn
if exist ".venv\Scripts\uvicorn.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto :START_SERVER
)

:: 3. Check if system Python already has uvicorn ready
python -m uvicorn --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :START_SERVER
)

:: 4. Check if system Python exists (to build .venv)
where python >nul 2>nul
if %errorlevel% equ 0 goto :SETUP_VENV

:: 5. Python is not installed at all -> Auto-download portable Python
goto :AUTO_DOWNLOAD_PYTHON


:SETUP_VENV
echo [First-time setup detected]
echo System Python found. Creating local virtual environment...
echo.

echo [1/3] Creating virtual environment: .venv
python -m venv .venv
if %errorlevel% neq 0 (
    echo [!] Virtualenv creation failed. Switching to portable Python download...
    goto :AUTO_DOWNLOAD_PYTHON
)

echo [2/3] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo [3/3] Installing dependencies from requirements.txt...
echo       This only happens once on first launch. Please wait...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [!] Error installing packages into .venv.
    pause
    exit /b 1
)

set "PYTHON_EXE=.venv\Scripts\python.exe"
goto :START_SERVER


:AUTO_DOWNLOAD_PYTHON
echo.
echo ========================================================
echo  No Python installation found on this computer.
echo  Auto-downloading portable Python 3.10 [Zero-Install]
echo ========================================================
echo.

if not exist "python-embed" mkdir "python-embed"

echo [1/4] Downloading portable Python 3.10 runtime [~10 MB]...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip', 'python-embed.zip')"
if %errorlevel% neq 0 (
    echo [!] Download failed. Please check your internet connection.
    pause
    exit /b 1
)

echo [2/4] Extracting portable Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path 'python-embed.zip' -DestinationPath 'python-embed' -Force"
del /f /q python-embed.zip 2>nul

echo [3/4] Configuring portable environment...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-Content -Path 'python-embed\python310._pth' -Value @('python310.zip', '.', 'Lib\site-packages', 'import site')"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'python-embed\get-pip.py')"
python-embed\python.exe python-embed\get-pip.py --no-warn-script-location --quiet
del /f /q python-embed\get-pip.py 2>nul

echo [4/4] Installing dependencies from requirements.txt...
echo       This takes 1-2 minutes on first run. Please wait...
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
goto :START_SERVER


:START_SERVER
:: Launch default web browser after 3 seconds in background
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000"

echo ========================================================
echo Starting EyeGUARDIAN Vision server on http://127.0.0.1:8000
echo The web app will open automatically in your browser.
echo.
echo Keep this window open while using the application.
echo Press CTRL+C in this window to stop the server.
echo ========================================================
echo.

"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause
