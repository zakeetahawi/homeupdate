#!/bin/bash
# Elkhawaga Trading - elkhawaga.uk (Linux)

clear

echo "========================================"
echo "   ELKHAWAGA TRADING SYSTEM"
echo "   https://elkhawaga.uk"
echo "   PRODUCTION SERVER"
echo "========================================"
echo

cd "$(dirname "$0")"

CRED_FILE="$(pwd)/cloudflare-credentials.json"
echo "[INFO] Using credentials file: $CRED_FILE"

if [ ! -f "$CRED_FILE" ]; then
  echo "[ERROR] Credentials file not found at: $CRED_FILE"
  exit 1
fi

# تفعيل البيئة الافتراضية تلقائيًا
if [ -f "venv/bin/activate" ]; then
  source "venv/bin/activate"
  echo "[INFO] Python virtual environment activated."
else
  echo "[WARNING] Python virtual environment (venv) not found. Continuing without venv."
fi

# Kill any existing processes
echo "[INFO] Stopping any existing Django and cloudflared processes..."
pkill -f manage.py > /dev/null 2>&1
pkill -f cloudflared > /dev/null 2>&1
sleep 2

echo "[INFO] Checking requirements..."
command -v python3 > /dev/null 2>&1 || { echo "[ERROR] Python3 not found! Please install Python3 first."; exit 1; }
[ -f "cloudflared" ] || { echo "[ERROR] cloudflared not found!"; exit 1; }
[ -f "cloudflared.yml" ] || { echo "[ERROR] cloudflared.yml not found!"; exit 1; }
[ -f "$CRED_FILE" ] || { echo "[ERROR] cloudflare-credentials.json not found!"; exit 1; }
echo "[OK] All requirements met"

echo "[INFO] Collecting static files for optimization..."
python3 manage.py collectstatic --noinput --clear

mkdir -p cache

echo
# Start Django server in foreground (details will show in this terminal)
echo "[INFO] Starting Django server on http://127.0.0.1:8000 ..."
python3 manage.py runserver 127.0.0.1:8000 &
DJANGO_PID=$!

# Wait for Django to start
echo "[INFO] Waiting for Django to initialize..."
for i in {1..10}; do
    if netstat -an | grep -q ":8000"; then
        echo "[OK] Django server is running successfully (PID: $DJANGO_PID)"
        break
    else
        echo "[INFO] Checking Django startup attempt $i/10..."
        sleep 2
    fi
done

echo "[INFO] Starting Cloudflare Tunnel..."
chmod +x cloudflared
./cloudflared tunnel --config ./cloudflared.yml --credentials-file "$CRED_FILE" run &
CLOUDFLARED_PID=$!

# عرض تفاصيل العمليات في الطرفية
trap 'echo "\n[INFO] Stopping all processes..."; kill $DJANGO_PID $CLOUDFLARED_PID 2>/dev/null; exit' SIGINT SIGTERM

echo "========================================"
echo "  SYSTEM IS NOW LIVE!"
echo "========================================"
echo "Your website is available at:"
echo "  Main Website:    https://elkhawaga.uk"
echo "  WWW Website:     https://www.elkhawaga.uk"
echo "  CRM System:      https://crm.elkhawaga.uk"
echo "  Admin Panel:     https://admin.elkhawaga.uk/admin/"
echo "  API Access:      https://api.elkhawaga.uk"
echo "========================================"
echo "  Status: ONLINE - SSL: ENABLED"
echo "========================================"
echo "Keep this window open while using the website"
echo "Press Ctrl+C to stop the server"
echo

# متابعة تفاصيل العمليات بشكل حي
wait $DJANGO_PID
wait $CLOUDFLARED_PID
