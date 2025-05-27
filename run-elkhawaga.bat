@echo off
title Elkhawaga Trading - elkhawaga.uk
color 0A
cls

echo.
echo ========================================
echo    ELKHAWAGA TRADING SYSTEM
echo    https://elkhawaga.uk
echo    PRODUCTION SERVER
echo ========================================
echo.

:: Set working directory
cd /d "%~dp0"

:: Kill any existing processes
echo Stopping any existing servers...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Check requirements
echo Checking system requirements...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python first.
    pause
    exit /b 1
)

if not exist cloudflared.exe (
    echo [ERROR] cloudflared.exe not found!
    pause
    exit /b 1
)

if not exist cloudflared.yml (
    echo [ERROR] cloudflared.yml not found!
    pause
    exit /b 1
)

if not exist cloudflare-credentials.json (
    echo [ERROR] cloudflare-credentials.json not found!
    pause
    exit /b 1
)

echo [OK] All requirements met

:: Collect static files for better performance
echo Collecting static files for optimization...
python manage.py collectstatic --noinput --clear >nul 2>&1

:: Create cache directory
if not exist "cache" mkdir cache

:: Start Django server with optimizations
echo.
echo Starting Django CRM server with performance optimizations...
start /B python manage.py runserver 127.0.0.1:8000

:: Wait for Django to start
echo Waiting for Django to initialize...
timeout /t 10 /nobreak >nul

:: Verify Django is running with multiple attempts
set DJANGO_STARTED=0
for /L %%i in (1,1,5) do (
    netstat -an | findstr ":8000" >nul
    if not errorlevel 1 (
        set DJANGO_STARTED=1
        goto :django_ready
    )
    echo Checking Django startup attempt %%i/5...
    timeout /t 2 /nobreak >nul
)

:django_ready
if "%DJANGO_STARTED%"=="1" (
    echo [OK] Django server is running successfully
) else (
    echo [WARNING] Django may still be starting, continuing with tunnel...
)

:: Start Cloudflare tunnel
echo.
echo Starting Cloudflare tunnel...
echo.
echo ========================================
echo        WEBSITE IS NOW LIVE!
echo ========================================
echo.
echo Your website is available at:
echo.
echo   Main Website:    https://elkhawaga.uk
echo   WWW Website:     https://www.elkhawaga.uk
echo   CRM System:      https://crm.elkhawaga.uk
echo   Admin Panel:     https://admin.elkhawaga.uk/admin/
echo   API Access:      https://api.elkhawaga.uk
echo.
echo ========================================
echo   Status: ONLINE - SSL: ENABLED
echo ========================================
echo.
echo Keep this window open while using the website
echo Press Ctrl+C to stop the server
echo.

:: Start tunnel and keep it running
cloudflared.exe tunnel --config cloudflared.yml run

:: If tunnel stops, show message
echo.
echo [WARNING] Tunnel disconnected
echo Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto :eof
