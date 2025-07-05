#!/bin/bash
# Elkhawaga Trading - Daily Auto Update (Linux)

# Set working directory to script location
cd "$(dirname "$0")"

# Log file for updates
LOG_FILE="update-log.txt"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily auto-update check" >> "$LOG_FILE"

# Check for updates silently
git fetch origin >> "$LOG_FILE" 2>&1

# Check if there are updates
UPDATE_COUNT=$(git rev-list HEAD..origin/main --count 2>/dev/null)

if [ "$UPDATE_COUNT" = "0" ] || [ -z "$UPDATE_COUNT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No updates available" >> "$LOG_FILE"
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found $UPDATE_COUNT updates, applying..." >> "$LOG_FILE"

# Backup production files
cp -f cloudflare-credentials.json cloudflare-credentials.json.bak 2>/dev/null
cp -f cloudflared.yml cloudflared.yml.bak 2>/dev/null
cp -f ../run-elkhawaga.bat run-elkhawaga.bat.bak 2>/dev/null

# Apply updates
git stash push -m "Auto-update stash $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE" 2>&1
git pull origin main >> "$LOG_FILE" 2>&1

# Restore production files
cp -f cloudflare-credentials.json.bak cloudflare-credentials.json 2>/dev/null
cp -f cloudflared.yml.bak cloudflared.yml 2>/dev/null
cp -f run-elkhawaga.bat.bak ../run-elkhawaga.bat 2>/dev/null

# Clean backup files
rm -f *.bak 2>/dev/null

# Update dependencies and migrate
pip install -r requirements.txt --quiet >> "$LOG_FILE" 2>&1
python3 manage.py migrate --noinput >> "$LOG_FILE" 2>&1
python3 manage.py collectstatic --noinput --clear >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Auto-update completed successfully" >> "$LOG_FILE"

# Keep only last 100 lines of logs (approx. 30 days)
tail -n 100 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

exit 0
