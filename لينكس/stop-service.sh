#!/bin/bash
# 🛑 سكريبت إيقاف النظام

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PIDS_DIR="$LOGS_DIR/pids"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >>"$LOGS_DIR/startup.log"
}

log "🛑 بدء إيقاف نظام HomeUpdate..."

# إيقاف المراقبة
if [ -f "$PIDS_DIR/monitor.pid" ]; then
	kill $(cat "$PIDS_DIR/monitor.pid") 2>/dev/null
	sleep 1
	kill -9 $(cat "$PIDS_DIR/monitor.pid") 2>/dev/null
	rm -f "$PIDS_DIR/monitor.pid"
	log "✅ تم إيقاف المراقبة"
fi

# إيقاف Daphne (مع الانتظار)
if [ -f "$PIDS_DIR/daphne.pid" ]; then
	PID=$(cat "$PIDS_DIR/daphne.pid")
	kill $PID 2>/dev/null
	sleep 2
	# التحقق إذا ما زالت تعمل
	if kill -0 $PID 2>/dev/null; then
		kill -9 $PID 2>/dev/null
	fi
	rm -f "$PIDS_DIR/daphne.pid"
	log "✅ تم إيقاف Daphne"
fi

# قتل جميع عمليات Daphne المتبقية
pkill -f "daphne" 2>/dev/null
sleep 1

# إيقاف Celery Worker
if [ -f "$PIDS_DIR/celery_worker.pid" ]; then
	PID=$(cat "$PIDS_DIR/celery_worker.pid")
	kill $PID 2>/dev/null
	sleep 2
	if kill -0 $PID 2>/dev/null; then
		kill -9 $PID 2>/dev/null
	fi
	rm -f "$PIDS_DIR/celery_worker.pid"
	log "✅ تم إيقاف Celery Worker"
fi

# قتل جميع عمليات Celery Worker المتبقية
pkill -f "celery.*worker" 2>/dev/null
sleep 1

# إيقاف Celery Beat
if [ -f "$PIDS_DIR/celery_beat.pid" ]; then
	PID=$(cat "$PIDS_DIR/celery_beat.pid")
	kill $PID 2>/dev/null
	sleep 2
	if kill -0 $PID 2>/dev/null; then
		kill -9 $PID 2>/dev/null
	fi
	rm -f "$PIDS_DIR/celery_beat.pid"
	rm -f "$LOGS_DIR/celerybeat-schedule"*
	log "✅ تم إيقاف Celery Beat"
fi

# قتل جميع عمليات Celery Beat المتبقية
pkill -f "celery.*beat" 2>/dev/null
sleep 1

# إيقاف Cloudflare Tunnel
if [ -f "$PIDS_DIR/cloudflared.pid" ]; then
	PID=$(cat "$PIDS_DIR/cloudflared.pid")
	kill $PID 2>/dev/null
	sleep 1
	if kill -0 $PID 2>/dev/null; then
		kill -9 $PID 2>/dev/null
	fi
	rm -f "$PIDS_DIR/cloudflared.pid"
	log "✅ تم إيقاف Cloudflare Tunnel"
fi

# قتل جميع عمليات Cloudflared المتبقية
pkill -f cloudflared 2>/dev/null
sleep 1

# إيقاف النسخ الاحتياطي
if [ -f "$PIDS_DIR/db_backup.pid" ]; then
	kill $(cat "$PIDS_DIR/db_backup.pid") 2>/dev/null
	rm -f "$PIDS_DIR/db_backup.pid"
	log "✅ تم إيقاف خدمة النسخ الاحتياطي"
fi

# تنظيف أي عمليات متبقية على المنفذ 8000
fuser -k 8000/tcp 2>/dev/null
pkill -f "monitor-service.sh" 2>/dev/null
pkill -f "daphne" 2>/dev/null
pkill -f "celery -A crm" 2>/dev/null

log "🛑 تم إيقاف جميع الخدمات وتحرير المنفذ 8000"
log "========================================"

exit 0
