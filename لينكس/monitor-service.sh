#!/bin/bash
# 🔍 سكريبت مراقبة الخدمات وإعادة تشغيلها عند الحاجة

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PIDS_DIR="$LOGS_DIR/pids"

cd "$PROJECT_DIR"
source "$PROJECT_DIR/venv/bin/activate"

export DEBUG=False
export DJANGO_LOG_LEVEL=WARNING

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# فترات الفحص (بالثواني)
CHECK_INTERVAL=60
DB_CHECK_INTERVAL=300
NOTIFICATION_CLEANUP_INTERVAL=1800
UPLOAD_CHECK_INTERVAL=600

LAST_DB_CHECK=0
LAST_NOTIFICATION_CLEANUP=0
LAST_UPLOAD_CHECK=0

while true; do
    sleep $CHECK_INTERVAL
    CURRENT_TIME=$(date +%s)

    # فحص Gunicorn
    if [ -f "$PIDS_DIR/gunicorn.pid" ]; then
        PID=$(cat "$PIDS_DIR/gunicorn.pid")
        if ! kill -0 $PID 2>/dev/null; then
            log "⚠️ Gunicorn توقف - إعادة تشغيل..."
            # تنظيف العمليات القديمة
            pkill -f "gunicorn crm.wsgi" 2>/dev/null
            sleep 2
            # التأكد من أن المنفذ حر
            lsof -ti:8000 | xargs kill -9 2>/dev/null
            sleep 1
            # إعادة التشغيل
            gunicorn crm.wsgi:application \
                --bind 0.0.0.0:8000 \
                --workers 2 \
                --threads 4 \
                --worker-class gthread \
                --worker-connections 100 \
                --max-requests 1000 \
                --max-requests-jitter 100 \
                --timeout 120 \
                --graceful-timeout 30 \
                --keep-alive 5 \
                --worker-tmp-dir /dev/shm \
                --access-logfile "$LOGS_DIR/gunicorn_access.log" \
                --error-logfile "$LOGS_DIR/gunicorn_error.log" \
                --log-level warning \
                --pid "$PIDS_DIR/gunicorn.pid" \
                --daemon
            sleep 2
            if [ -f "$PIDS_DIR/gunicorn.pid" ] && kill -0 $(cat "$PIDS_DIR/gunicorn.pid") 2>/dev/null; then
                log "✅ تم إعادة تشغيل Gunicorn بنجاح"
            else
                log "❌ فشل في إعادة تشغيل Gunicorn"
            fi
        fi
    fi

    # فحص Celery Worker
    if [ -f "$PIDS_DIR/celery_worker.pid" ]; then
        PID=$(cat "$PIDS_DIR/celery_worker.pid")
        if ! kill -0 $PID 2>/dev/null; then
            log "⚠️ Celery Worker توقف - إعادة تشغيل..."
            # تنظيف العمليات القديمة
            pkill -f "celery.*worker" 2>/dev/null
            sleep 2
            # إعادة التشغيل
            celery -A crm worker \
                --loglevel=warning \
                --queues=celery,file_uploads \
                --pidfile="$PIDS_DIR/celery_worker.pid" \
                --logfile="$LOGS_DIR/celery_worker.log" \
                --pool=solo \
                --concurrency=1 \
                --max-memory-per-child=200000 \
                --time-limit=300 \
                --soft-time-limit=270 \
                --detach
            sleep 2
            if [ -f "$PIDS_DIR/celery_worker.pid" ] && kill -0 $(cat "$PIDS_DIR/celery_worker.pid") 2>/dev/null; then
                log "✅ تم إعادة تشغيل Celery Worker بنجاح"
            else
                log "❌ فشل في إعادة تشغيل Celery Worker"
            fi
        fi
    fi

    # فحص Celery Beat
    if [ -f "$PIDS_DIR/celery_beat.pid" ]; then
        PID=$(cat "$PIDS_DIR/celery_beat.pid")
        if ! kill -0 $PID 2>/dev/null; then
            log "⚠️ Celery Beat توقف - إعادة تشغيل..."
            # تنظيف العمليات القديمة
            pkill -f "celery.*beat" 2>/dev/null
            rm -f "$LOGS_DIR/celerybeat-schedule"*
            sleep 2
            # إعادة التشغيل
            celery -A crm beat \
                --loglevel=warning \
                --pidfile="$PIDS_DIR/celery_beat.pid" \
                --logfile="$LOGS_DIR/celery_beat.log" \
                --schedule="$LOGS_DIR/celerybeat-schedule" \
                --detach
            sleep 2
            if [ -f "$PIDS_DIR/celery_beat.pid" ] && kill -0 $(cat "$PIDS_DIR/celery_beat.pid") 2>/dev/null; then
                log "✅ تم إعادة تشغيل Celery Beat بنجاح"
            else
                log "❌ فشل في إعادة تشغيل Celery Beat"
            fi
        fi
    fi

    # فحص Cloudflare Tunnel
    if [ -f "$PIDS_DIR/cloudflared.pid" ]; then
        PID=$(cat "$PIDS_DIR/cloudflared.pid")
        if ! kill -0 $PID 2>/dev/null; then
            log "⚠️ Cloudflare Tunnel توقف - إعادة تشغيل..."
            # تنظيف العمليات القديمة
            pkill -f cloudflared 2>/dev/null
            sleep 2
            # إعادة التشغيل
            "$PROJECT_DIR/cloudflared" tunnel --config "$PROJECT_DIR/cloudflared.yml" run >> "$LOGS_DIR/cloudflared.log" 2>&1 &
            echo $! > "$PIDS_DIR/cloudflared.pid"
            sleep 2
            if kill -0 $(cat "$PIDS_DIR/cloudflared.pid") 2>/dev/null; then
                log "✅ تم إعادة تشغيل Cloudflare Tunnel بنجاح"
            else
                log "❌ فشل في إعادة تشغيل Cloudflare Tunnel"
            fi
        fi
    fi

    # فحص دوري لقاعدة البيانات
    if [ $((CURRENT_TIME - LAST_DB_CHECK)) -ge $DB_CHECK_INTERVAL ]; then
        DB_OUTPUT=$(python manage.py monitor_db --once 2>&1)
        DB_STATUS=$?
        if [ $DB_STATUS -ne 0 ]; then
            # تصفية رسائل Django العادية
            if [[ ! "$DB_OUTPUT" =~ "Accounting signals" ]] && [[ ! "$DB_OUTPUT" =~ "إيقاف العمليات" ]]; then
                log "⚠️ مشكلة في قاعدة البيانات: $DB_OUTPUT"
            fi
        fi
        LAST_DB_CHECK=$CURRENT_TIME
    fi

    # تنظيف دوري للإشعارات
    if [ $((CURRENT_TIME - LAST_NOTIFICATION_CLEANUP)) -ge $NOTIFICATION_CLEANUP_INTERVAL ]; then
        python manage.py cleanup_notifications 2>/dev/null
        LAST_NOTIFICATION_CLEANUP=$CURRENT_TIME
    fi

    # رفع تلقائي للملفات المعلقة
    if [ $((CURRENT_TIME - LAST_UPLOAD_CHECK)) -ge $UPLOAD_CHECK_INTERVAL ]; then
        if [ -f "$PROJECT_DIR/auto_upload_system.py" ]; then
            python "$PROJECT_DIR/auto_upload_system.py" single 2>/dev/null
        fi
        LAST_UPLOAD_CHECK=$CURRENT_TIME
    fi

done
