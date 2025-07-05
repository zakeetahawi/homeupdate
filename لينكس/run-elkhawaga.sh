#!/bin/bash
# Elkhawaga Trading - elkhawaga.uk (Linux)

clear

echo "========================================"
echo "   ELKHAWAGA TRADING SYSTEM"
echo "   https://elkhawaga.uk"
echo "   PRODUCTION SERVER"
echo "========================================"
echo

# Set working directory to script location
cd "$(dirname "$0")"

# Kill any existing processes
echo "Stopping any existing servers..."
pkill -f manage.py > /dev/null 2>&1
pkill -f cloudflared > /dev/null 2>&1
sleep 2

# Check requirements
command -v python3 > /dev/null 2>&1 || { echo "[ERROR] Python3 not found! Please install Python3 first."; exit 1; }
[ -f "../cloudflared" ] || { echo "[ERROR] cloudflared not found!"; exit 1; }
[ -f "../cloudflared.yml" ] || { echo "[ERROR] cloudflared.yml not found!"; exit 1; }
[ -f "../cloudflare-credentials.json" ] || { echo "[ERROR] cloudflare-credentials.json not found!"; exit 1; }
echo "[OK] All requirements met"

# Collect static files for better performance
echo "Collecting static files for optimization..."
python3 ../manage.py collectstatic --noinput --clear > /dev/null 2>&1

# Create cache directory
mkdir -p ../cache

# Start Django server with optimizations
echo
nohup python3 ../manage.py runserver 127.0.0.1:8000 > ../django.log 2>&1 &
DJANGO_PID=$!

# Wait for Django to start
echo "Waiting for Django to initialize..."
for i in {1..5}; do
    if netstat -an | grep -q ":8000"; then
        echo "[OK] Django server is running successfully"
        break
    else
        echo "Checking Django startup attempt $i/5..."
        sleep 2
    fi
done

# Start Cloudflare tunnel in a restart loop
echo
chmod +x ../cloudflared
while true; do
    echo "[INFO] Starting Cloudflare Tunnel..."
    nohup ../cloudflared tunnel --config ../cloudflared.yml run >> ../cloudflared.log 2>&1 &
    CLOUDFLARED_PID=$!
    wait $CLOUDFLARED_PID
    echo "[WARNING] Tunnel disconnected. Restarting in 5 seconds..."
    sleep 5
done
