#!/bin/bash
# 🛑 إيقاف نظام الخواجة بشكل آمن

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] بدء إيقاف النظام..." >> "$LOGS_DIR/startup.log"

# إيقاف Gunicorn
if [ -f "$PID_DIR/gunicorn.pid" ]; then
    GUNICORN_PID=$(cat "$PID_DIR/gunicorn.pid")
    if kill -0 $GUNICORN_PID 2>/dev/null; then
        echo "إيقاف Gunicorn (PID: $GUNICORN_PID)..."
        kill -TERM $GUNICORN_PID
        sleep 5
        kill -0 $GUNICORN_PID 2>/dev/null && kill -9 $GUNICORN_PID || true
    fi
    rm -f "$PID_DIR/gunicorn.pid"
fi

# إيقاف Celery Worker
if [ -f "$PID_DIR/celery.pid" ]; then
    CELERY_PID=$(cat "$PID_DIR/celery.pid")
    if kill -0 $CELERY_PID 2>/dev/null; then
        echo "إيقاف Celery Worker (PID: $CELERY_PID)..."
        kill -TERM $CELERY_PID
        sleep 3
        kill -0 $CELERY_PID 2>/dev/null && kill -9 $CELERY_PID || true
    fi
    rm -f "$PID_DIR/celery.pid"
fi

# إيقاف Celery Beat
if [ -f "$PID_DIR/celery-beat.pid" ]; then
    BEAT_PID=$(cat "$PID_DIR/celery-beat.pid")
    if kill -0 $BEAT_PID 2>/dev/null; then
        echo "إيقاف Celery Beat (PID: $BEAT_PID)..."
        kill -TERM $BEAT_PID
        sleep 2
        kill -0 $BEAT_PID 2>/dev/null && kill -9 $BEAT_PID || true
    fi
    rm -f "$PID_DIR/celery-beat.pid"
fi

# إيقاف Redis (اختياري - قد يكون مستخدم من تطبيقات أخرى)
# if [ -f "$PID_DIR/redis.pid" ]; then
#     REDIS_PID=$(cat "$PID_DIR/redis.pid")
#     kill -TERM $REDIS_PID 2>/dev/null || true
#     rm -f "$PID_DIR/redis.pid"
# fi

# تنظيف شامل للعمليات المتبقية
pkill -9 -f "gunicorn.*crm.wsgi" 2>/dev/null || true
pkill -9 -f "celery.*worker.*crm" 2>/dev/null || true

rm -f "$PID_DIR/service_info.txt"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] تم إيقاف النظام بنجاح" >> "$LOGS_DIR/startup.log"
echo "✅ تم إيقاف النظام بنجاح"

exit 0
