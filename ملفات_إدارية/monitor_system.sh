#!/bin/bash
# System monitoring script

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"

# Check if Gunicorn is running
if ! pgrep -f "gunicorn.*crm.wsgi" > /dev/null; then
    echo "[$(date)] Gunicorn is not running" >> "$LOGS_DIR/monitor.log"
    # Restart could be triggered here if needed
fi

# Check if Cloudflare tunnel is running
if ! pgrep -f "cloudflared.*tunnel" > /dev/null; then
    echo "[$(date)] Cloudflare tunnel is not running" >> "$LOGS_DIR/monitor.log"
fi

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "[$(date)] Redis is not running" >> "$LOGS_DIR/monitor.log"
fi
