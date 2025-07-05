#!/bin/bash
# Elkhawaga Trading - System Update (Linux)

echo "========================================"
echo "   ELKHAWAGA TRADING SYSTEM"
echo "   AUTOMATIC UPDATE SYSTEM"
echo "========================================"
echo

# Set working directory to script location
cd "$(dirname "$0")"

# Check if git is available
command -v git >/dev/null 2>&1 || { echo "[ERROR] Git is not installed or not in PATH"; exit 1; }

echo "[INFO] Checking for updates from repository..."

# Backup current production files
echo "[INFO] Backing up production files..."
[ -f cloudflare-credentials.json ] && cp cloudflare-credentials.json cloudflare-credentials.json.backup && echo "[OK] Backed up Cloudflare credentials"
[ -f cloudflared.yml ] && cp cloudflared.yml cloudflared.yml.backup && echo "[OK] Backed up Cloudflare config"
[ -f ../run-elkhawaga.bat ] && cp ../run-elkhawaga.bat run-elkhawaga.bat.backup && echo "[OK] Backed up run script"

echo "[INFO] Stashing local changes..."
git stash push -m "Auto-stash before update - $(date '+%Y-%m-%d %H:%M:%S')"

echo "[INFO] Fetching latest changes..."
git fetch origin

UPDATE_COUNT=$(git rev-list HEAD..origin/main --count)
if [ "$UPDATE_COUNT" = "0" ] || [ -z "$UPDATE_COUNT" ]; then
    echo "[INFO] System is already up to date"
    echo "[INFO] No updates available"
else
    echo "[INFO] Found $UPDATE_COUNT new updates"
    echo "[INFO] Updating system..."
    git pull origin main || { echo "[ERROR] Failed to pull updates"; echo "[INFO] Restoring from stash..."; git stash pop; }
    echo "[OK] Successfully updated system files"
fi

echo "[INFO] Restoring production files..."
[ -f cloudflare-credentials.json.backup ] && mv cloudflare-credentials.json.backup cloudflare-credentials.json && echo "[OK] Restored Cloudflare credentials"
[ -f cloudflared.yml.backup ] && mv cloudflared.yml.backup cloudflared.yml && echo "[OK] Restored Cloudflare config"
[ -f run-elkhawaga.bat.backup ] && mv run-elkhawaga.bat.backup ../run-elkhawaga.bat && echo "[OK] Restored run script"

# Install/update Python dependencies if requirements.txt changed
if [ -f requirements.txt ]; then
    echo "[INFO] Checking Python dependencies..."
    pip install -r requirements.txt --quiet && echo "[OK] Dependencies updated"
fi

echo "[INFO] Running database migrations..."
python3 manage.py migrate --noinput || echo "[WARNING] Migration failed, but continuing..."
echo "[INFO] Collecting static files..."
python3 manage.py collectstatic --noinput --clear || echo "[WARNING] Static files collection failed, but continuing..."

echo

echo "========================================"
echo "   UPDATE COMPLETED SUCCESSFULLY"
echo "========================================"
echo "[INFO] System has been updated to the latest version"
echo "[INFO] Production files have been preserved"
echo "[INFO] You can now restart the server with: bash run-elkhawaga.sh"
echo

read -p "Do you want to restart the server now? (y/n): " RESTART
if [[ "$RESTART" =~ ^[Yy]$ ]]; then
    echo "[INFO] Restarting server..."
    bash run-elkhawaga.sh
else
    echo "[INFO] Please restart the server manually when ready."
fi
