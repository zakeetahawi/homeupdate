@echo off
title CRM Online

echo Starting CRM System Online...
echo.

:: Go to project directory
cd /d "C:\Users\zakee\Desktop\crm"

:: Check if project exists
if not exist "manage.py" (
    echo ERROR: Project not found!
    pause
    exit
)

echo Project found!
echo Starting Django server...

:: Start Django server
start /B python manage.py runserver 127.0.0.1:8000

:: Wait for server
ping 127.0.0.1 -n 4 >nul

:: Download cloudflared if not exists
if not exist "cloudflared.exe" (
    echo Downloading Cloudflare Tunnel...
    curl -L -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
)

:: Check if download successful
if not exist "cloudflared.exe" (
    echo ERROR: Could not download cloudflared!
    pause
    exit
)

echo.
echo Starting Cloudflare Tunnel...
echo Copy the URL that appears below:
echo.

:: Start tunnel
cloudflared.exe tunnel --url http://127.0.0.1:8000

:: Cleanup
echo.
echo Stopping services...
taskkill /f /im python.exe >nul 2>&1
echo Done!
pause
