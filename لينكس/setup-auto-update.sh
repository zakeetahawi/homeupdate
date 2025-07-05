#!/bin/bash
# Setup Auto Update for Elkhawaga Trading (Linux)

clear

echo "========================================"
echo "   SETUP AUTOMATIC UPDATES"
echo "   Elkhawaga Trading System"
echo "========================================"
echo

# Requires root privileges
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] This script requires root privileges. Please run with sudo."
  exit 1
fi

echo "[INFO] Setting up automatic daily updates..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_NAME="elkhawaga_auto_update"
CRON_JOB="0 3 * * * cd $SCRIPT_DIR && bash auto-update-daily.sh >> update-log.txt 2>&1"

# Remove existing cron job
crontab -l | grep -v "$SCRIPT_DIR/auto-update-daily.sh" | crontab -

# Add new cron job
(crontab -l; echo "$CRON_JOB") | crontab -

if [ $? -ne 0 ]; then
  echo "[ERROR] Failed to create cron job."
  exit 1
fi

echo "[OK] Cron job created successfully."
echo "========================================"
echo "   AUTO-UPDATE SETUP COMPLETE"
echo "========================================"
echo "[INFO] The system will now automatically check for updates daily at 3:00 AM."
echo "[INFO] Updates will be applied automatically while preserving production files."
echo "[INFO] Logs will be saved to: update-log.txt"
echo

echo "Manual update commands:"
echo "  - Run update now: bash auto-update-daily.sh"
echo "  - View update log: cat update-log.txt"
echo "  - Disable auto-update: crontab -e (and remove the relevant line)"
echo
