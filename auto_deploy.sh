#!/bin/bash
# Auto-deployment script for homeupdate production server
# Automatically pulls updates from GitHub, runs migrations, and restarts services

set -e  # Exit on any error

# Configuration
PROJECT_DIR="/home/zakee/homeupdate"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/auto_deploy_$(date +%Y%m%d_%H%M%S).log"
BRANCH="main"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to send notification (Telegram - optional)
notify_telegram() {
    # Uncomment and configure if you want Telegram notifications
    # BOT_TOKEN="YOUR_BOT_TOKEN"
    # CHAT_ID="YOUR_CHAT_ID"
    # MESSAGE="$1"
    # curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    #     -d chat_id="${CHAT_ID}" \
    #     -d text="${MESSAGE}" > /dev/null 2>&1 || true
    :
}

# Rollback function
rollback() {
    if [ -n "$LAST_GOOD_COMMIT" ]; then
        log "ERROR: Deployment failed. Rolling back to $LAST_GOOD_COMMIT..."
        git reset --hard "$LAST_GOOD_COMMIT"
        sudo systemctl restart homeupdate.service || true
        notify_telegram "❌ Deployment FAILED and rolled back to $LAST_GOOD_COMMIT"
    fi
    log "=========================================="
    log "❌ DEPLOYMENT FAILED"
    log "=========================================="
    exit 1
}

# Set trap for error handling
trap rollback ERR

log "=========================================="
log "Starting auto-deployment process"
log "=========================================="

# Navigate to project directory
cd "$PROJECT_DIR" || {
    log "ERROR: Cannot access project directory: $PROJECT_DIR"
    exit 1
}

# Save current commit for potential rollback
LAST_GOOD_COMMIT=$(git rev-parse HEAD)
log "Current commit: $LAST_GOOD_COMMIT"

# Check if there are local uncommitted changes
if [[ -n $(git status -s) ]]; then
    log "WARNING: Local changes detected. Stashing..."
    git stash save "Auto-stash before deployment $(date +%Y%m%d_%H%M%S)"
fi

# Fetch updates from GitHub
log "Fetching updates from GitHub..."
git fetch origin "$BRANCH"

# Check if there are new commits
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    log "No updates available. System is up to date."
    log "=========================================="
    exit 0
fi

log "New updates found. Current: ${LOCAL:0:7}, Remote: ${REMOTE:0:7}"

# Show what will be pulled
log "Changes to be applied:"
git log --oneline "$LOCAL..$REMOTE" | tee -a "$LOG_FILE"

# Pull changes
log "Pulling changes from GitHub..."
git pull origin "$BRANCH"

# Activate virtual environment
log "Activating virtual environment..."
source "$VENV_DIR/bin/activate" || {
    log "ERROR: Cannot activate virtual environment"
    exit 1
}

# Install/update requirements
log "Installing/updating Python packages..."
pip install -r requirements.txt --quiet || log "WARNING: Some packages may have issues"

# Run database migrations for all apps
log "Running database migrations..."
python manage.py migrate --no-input

# Setup accounting structure (idempotent - safe to run multiple times)
log "Setting up accounting structure..."
python manage.py setup_accounting_structure || log "WARNING: Accounting setup had issues"

# Create/update customer accounts (idempotent)
log "Creating/updating customer accounts..."
python manage.py create_customer_accounts || log "WARNING: Customer accounts update had issues"

# Collect static files
log "Collecting static files..."
python manage.py collectstatic --no-input --clear

# Run system health checks
log "Running Django system checks..."
python manage.py check --deploy || log "WARNING: Some deployment checks failed"

# Restart services
log "Restarting Django/Celery services..."
if command -v systemctl &> /dev/null; then
    # Restart main Django service
    sudo systemctl restart homeupdate.service && log "✓ homeupdate.service restarted"
    
    # Restart Celery worker
    sudo systemctl restart homeupdate-celery.service && log "✓ homeupdate-celery.service restarted"
    
    # Restart Celery beat scheduler
    sudo systemctl restart homeupdate-celerybeat.service && log "✓ homeupdate-celerybeat.service restarted"
    
    # Reload Nginx
    sudo systemctl reload nginx && log "✓ nginx reloaded"
else
    log "WARNING: systemctl not found. Manual service restart required."
fi

# Cleanup old deployment logs (keep last 30 days)
log "Cleaning up old deployment logs..."
find "$LOG_DIR" -name "auto_deploy_*.log" -mtime +30 -delete 2>/dev/null || true

# Remove trap
trap - ERR

# Success notification
NEW_COMMIT=$(git rev-parse HEAD)
log "=========================================="
log "✅ AUTO-DEPLOYMENT COMPLETED SUCCESSFULLY"
log "Deployed commit: ${NEW_COMMIT:0:7}"
log "=========================================="

notify_telegram "✅ Deployment completed successfully: ${NEW_COMMIT:0:7}"

exit 0
