@echo off
title Elkhawaga Trading - Quick Start
color 0A
cls

echo.
echo ========================================
echo    ELKHAWAGA TRADING SYSTEM
echo    https://elkhawaga.uk
echo    QUICK START MODE
echo ========================================
echo.

cd /d "%~dp0"

echo Starting Django server...
start /B python manage.py runserver 127.0.0.1:8000

echo Waiting for Django to load...
timeout /t 8 /nobreak >nul

echo Starting Cloudflare tunnel...
echo.
echo ========================================
echo        WEBSITE IS NOW LIVE!
echo ========================================
echo.
echo Your website is available at:
echo.
echo   Main Website:    https://elkhawaga.uk
echo   CRM System:      https://crm.elkhawaga.uk
echo   Admin Panel:     https://admin.elkhawaga.uk/admin/
echo.
echo Keep this window open while using the website
echo Press Ctrl+C to stop the server
echo.

cloudflared.exe tunnel --config cloudflared.yml run

echo.
echo Server stopped.
pause
