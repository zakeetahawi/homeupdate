@echo off
title Elkhawaga Trading - System Update
color 0B
cls

echo.
echo ========================================
echo    ELKHAWAGA TRADING SYSTEM
echo    AUTOMATIC UPDATE SYSTEM
echo ========================================
echo.

:: Set working directory
cd /d "%~dp0"

:: Check if git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not in PATH
    echo Please install Git first
    pause
    exit /b 1
)

echo [INFO] Checking for updates from repository...

:: Backup current production files
echo [INFO] Backing up production files...
if exist cloudflare-credentials.json (
    copy cloudflare-credentials.json cloudflare-credentials.json.backup >nul
    echo [OK] Backed up Cloudflare credentials
)

if exist cloudflared.yml (
    copy cloudflared.yml cloudflared.yml.backup >nul
    echo [OK] Backed up Cloudflare config
)

if exist run-elkhawaga.bat (
    copy run-elkhawaga.bat run-elkhawaga.bat.backup >nul
    echo [OK] Backed up run script
)

:: Stash any local changes to avoid conflicts
echo [INFO] Stashing local changes...
git stash push -m "Auto-stash before update - %date% %time%"

:: Fetch latest changes
echo [INFO] Fetching latest changes...
git fetch origin

:: Check if there are updates
for /f %%i in ('git rev-list HEAD..origin/main --count') do set UPDATE_COUNT=%%i

if "%UPDATE_COUNT%"=="0" (
    echo [INFO] System is already up to date
    echo [INFO] No updates available
    goto :restore_files
) else (
    echo [INFO] Found %UPDATE_COUNT% new updates
    echo [INFO] Updating system...
)

:: Pull latest changes
git pull origin main

if errorlevel 1 (
    echo [ERROR] Failed to pull updates
    echo [INFO] Restoring from stash...
    git stash pop
    goto :restore_files
)

echo [OK] Successfully updated system files

:: Restore production files
:restore_files
echo [INFO] Restoring production files...

if exist cloudflare-credentials.json.backup (
    copy cloudflare-credentials.json.backup cloudflare-credentials.json >nul
    del cloudflare-credentials.json.backup >nul
    echo [OK] Restored Cloudflare credentials
)

if exist cloudflared.yml.backup (
    copy cloudflared.yml.backup cloudflared.yml >nul
    del cloudflared.yml.backup >nul
    echo [OK] Restored Cloudflare config
)

if exist run-elkhawaga.bat.backup (
    copy run-elkhawaga.bat.backup run-elkhawaga.bat >nul
    del run-elkhawaga.bat.backup >nul
    echo [OK] Restored run script
)

:: Install/update Python dependencies if requirements.txt changed
if exist requirements.txt (
    echo [INFO] Checking Python dependencies...
    pip install -r requirements.txt --quiet
    echo [OK] Dependencies updated
)

:: Run database migrations
echo [INFO] Running database migrations...
python manage.py migrate --noinput
if errorlevel 1 (
    echo [WARNING] Migration failed, but continuing...
) else (
    echo [OK] Database migrations completed
)

:: Collect static files
echo [INFO] Collecting static files...
python manage.py collectstatic --noinput --clear
if errorlevel 1 (
    echo [WARNING] Static files collection failed, but continuing...
) else (
    echo [OK] Static files collected
)

echo.
echo ========================================
echo    UPDATE COMPLETED SUCCESSFULLY
echo ========================================
echo.
echo [INFO] System has been updated to the latest version
echo [INFO] Production files have been preserved
echo [INFO] You can now restart the server with: run-elkhawaga.bat
echo.

:: Ask if user wants to restart the server
set /p RESTART="Do you want to restart the server now? (y/n): "
if /i "%RESTART%"=="y" (
    echo [INFO] Restarting server...
    start run-elkhawaga.bat
    exit
) else (
    echo [INFO] Please restart the server manually when ready
)

pause
