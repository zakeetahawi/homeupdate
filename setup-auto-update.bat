@echo off
title Setup Auto Update for Elkhawaga Trading
color 0E
cls

echo.
echo ========================================
echo    SETUP AUTOMATIC UPDATES
echo    Elkhawaga Trading System
echo ========================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script requires administrator privileges
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [INFO] Setting up automatic daily updates...

:: Get current directory
set CURRENT_DIR=%~dp0
set TASK_NAME=ElkhawagaTradingAutoUpdate

:: Delete existing task if it exists
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Create scheduled task for daily updates at 3 AM
schtasks /create /tn "%TASK_NAME%" /tr "\"%CURRENT_DIR%auto-update-daily.bat\"" /sc daily /st 03:00 /ru SYSTEM /f

if errorlevel 1 (
    echo [ERROR] Failed to create scheduled task
    pause
    exit /b 1
)

echo [OK] Scheduled task created successfully
echo.
echo ========================================
echo    AUTO-UPDATE SETUP COMPLETE
echo ========================================
echo.
echo [INFO] The system will now automatically check for updates daily at 3:00 AM
echo [INFO] Updates will be applied automatically while preserving production files
echo [INFO] Logs will be saved to: update-log.txt
echo.
echo Manual update commands:
echo   - Run update now: update-system.bat
echo   - View update log: type update-log.txt
echo   - Disable auto-update: schtasks /delete /tn "%TASK_NAME%" /f
echo.

pause
