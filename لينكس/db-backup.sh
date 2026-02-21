#!/bin/bash
# Simple DB backup loop for Postgres
# Creates an immediate backup on start, then one every hour.

PIDFILE="/tmp/db-backup.pid"
if [ -f "$PIDFILE" ]; then
	OLDPID=$(cat "$PIDFILE" 2>/dev/null || true)
	if [ -n "$OLDPID" ] && kill -0 "$OLDPID" 2>/dev/null; then
		echo "Another db-backup.sh is already running (PID=$OLDPID). Exiting." >&2
		exit 0
	else
		# stale pidfile
		rm -f "$PIDFILE"
	fi
fi
echo $$ >"$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT INT TERM

TARGET_DIR="/home/zakee/homeupdate/media/backups"
mkdir -p "$TARGET_DIR"

# Read DB connection from environment or fall back to project settings defaults
DB_NAME="${DB_NAME:-crm_system}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-5525}"

timestamp() {
	date +"%Y%m%d_%H%M%S"
}

create_backup() {
	TS=$(timestamp)
	FILENAME="backup-${TS}.sql.gz"
	OUTPATH="$TARGET_DIR/$FILENAME"

	# Use PGPASSWORD to avoid interactive prompt. If DB uses socket auth this is harmless.
	PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/tmp/pg_dump_error.log | gzip >"$OUTPATH"
	STATUS=$?
	if [ $STATUS -eq 0 ]; then
		echo "✔️ تم إنشاء نسخة احتياطية بنجاح: $OUTPATH"
		# remove error file if present
		[ -f /tmp/pg_dump_error.log ] && rm -f /tmp/pg_dump_error.log
	else
		echo "❌ فشل إنشاء النسخة الاحتياطية - تحقق من /tmp/pg_dump_error.log"
	fi
}

# Create one backup immediately on start
create_backup

# Run backups every hour (3600 seconds). The script will run in background from run-production.sh
while true; do
        # sleep في الخلفية + wait حتى يكون قابلاً للمقاطعة بـ SIGTERM
        sleep 3600 & wait $!
done
