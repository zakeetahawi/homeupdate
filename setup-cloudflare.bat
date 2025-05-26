@echo off
title Setup Cloudflare Tunnel for elkhawaga.uk
color 0B
echo.
echo ========================================
echo    Cloudflare Tunnel Setup
echo    Domain: elkhawaga.uk
echo ========================================
echo.

:: Set working directory
cd /d "%~dp0"

:: Check if cloudflared is installed
cloudflared --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Cloudflared is not installed
    echo.
    echo Please download and install cloudflared from:
    echo https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
    echo.
    echo After installation, run this script again.
    pause
    exit /b 1
)

echo ✅ Cloudflared is installed
echo.

:: Login to Cloudflare
echo 🔐 Step 1: Login to Cloudflare...
echo This will open a browser window for authentication
pause
cloudflared tunnel login

if errorlevel 1 (
    echo ❌ Login failed
    pause
    exit /b 1
)

echo ✅ Login successful
echo.

:: Set Cloudflare credentials
set CLOUDFLARE_API_TOKEN=yxwKZnpQoQAX9sMurxfEOIAkuzHdA2xc-xq3wVsF
set CLOUDFLARE_ZONE_ID=06fbc6c23ac2bc2a4be75bed03d3e643
set CLOUDFLARE_ACCOUNT_ID=4085f6891221e9884cf399a561d235c0

:: Create tunnel
echo 🚇 Step 2: Creating tunnel for elkhawaga.uk...
cloudflared tunnel create elkhawaga-tunnel

if errorlevel 1 (
    echo ❌ Tunnel creation failed
    pause
    exit /b 1
)

echo ✅ Tunnel created successfully
echo.

:: Get tunnel ID and update config file
echo 📋 Getting tunnel information and updating config...
for /f "tokens=1" %%i in ('cloudflared tunnel list ^| findstr elkhawaga-tunnel') do (
    set TUNNEL_ID=%%i
    echo Found tunnel ID: %%i

    :: Update cloudflared.yml with actual tunnel ID
    powershell -Command "(Get-Content cloudflared.yml) -replace 'YOUR_TUNNEL_ID_HERE', '%%i' | Set-Content cloudflared.yml"
    echo ✅ Updated cloudflared.yml with tunnel ID
)

:: Create DNS records automatically
echo 🌐 Step 3: Creating DNS records...
echo Creating DNS records for elkhawaga.uk...

cloudflared tunnel route dns elkhawaga-tunnel elkhawaga.uk
cloudflared tunnel route dns elkhawaga-tunnel www.elkhawaga.uk
cloudflared tunnel route dns elkhawaga-tunnel crm.elkhawaga.uk
cloudflared tunnel route dns elkhawaga-tunnel api.elkhawaga.uk
cloudflared tunnel route dns elkhawaga-tunnel admin.elkhawaga.uk

echo ✅ DNS records created successfully

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Update cloudflared.yml with your tunnel ID
echo 2. Update .env.production with your API tokens
echo 3. Run: run-elkhawaga-production.bat
echo.
echo Your site will be available at:
echo • https://elkhawaga.uk
echo • https://www.elkhawaga.uk
echo • https://crm.elkhawaga.uk
echo • https://admin.elkhawaga.uk
echo.
pause
