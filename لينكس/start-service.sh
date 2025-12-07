#!/bin/bash
# 🚀 سكريبت تشغيل النظام كخدمة systemd
# يعمل تلقائياً عند إقلاع الجهاز

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PIDS_DIR="$LOGS_DIR/pids"

# إنشاء المجلدات
mkdir -p "$LOGS_DIR" "$PIDS_DIR"

# ملف سجل بدء التشغيل
STARTUP_LOG="$LOGS_DIR/startup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$STARTUP_LOG"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ ERROR: $1" >> "$STARTUP_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ ERROR: $1" >> "$LOGS_DIR/error.log"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1" >> "$STARTUP_LOG"
}

# بدء التسجيل
echo "========================================" >> "$STARTUP_LOG"
log "🚀 بدء تشغيل نظام HomeUpdate"
log "📁 مجلد المشروع: $PROJECT_DIR"

# التحقق من المجلد
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "مجلد المشروع غير موجود: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# تفعيل البيئة الافتراضية
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    log_success "تم تفعيل البيئة الافتراضية"
else
    log_error "البيئة الافتراضية غير موجودة"
    exit 1
fi

# إعدادات الإنتاج
export DEBUG=False
export DJANGO_LOG_LEVEL=WARNING
export PYTHONUNBUFFERED=1

# انتظار قاعدة البيانات
log "⏳ انتظار قاعدة البيانات..."
for i in {1..30}; do
    if pg_isready -q 2>/dev/null; then
        log_success "قاعدة البيانات جاهزة"
        break
    fi
    sleep 1
done

# تطبيق التحديثات
log "📦 تطبيق التحديثات..."
python manage.py migrate --noinput >> "$STARTUP_LOG" 2>&1
if [ $? -eq 0 ]; then
    log_success "تم تطبيق التحديثات"
else
    log_error "فشل في تطبيق التحديثات"
fi

# تجميع الملفات الثابتة
log "📁 تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput --clear >> "$STARTUP_LOG" 2>&1
if [ $? -eq 0 ]; then
    log_success "تم تجميع الملفات الثابتة"
else
    log_error "فشل في تجميع الملفات الثابتة"
fi

# تنظيف الإشعارات القديمة
log "🧹 تنظيف الإشعارات القديمة..."
python manage.py cleanup_notifications >> "$STARTUP_LOG" 2>&1

# تشغيل Redis إذا لم يكن يعمل
log "🔴 فحص Redis..."
if ! pgrep -x "redis-server" > /dev/null; then
    redis-server --daemonize yes --port 6379 --dir /tmp >> "$STARTUP_LOG" 2>&1
    log_success "تم تشغيل Redis"
else
    log_success "Redis يعمل بالفعل"
fi

# تنظيف ملفات PID القديمة والعمليات المتبقية
log "🧹 تنظيف العمليات القديمة..."
pkill -f "gunicorn crm.wsgi" 2>/dev/null
pkill -f "celery.*worker" 2>/dev/null
pkill -f "celery.*beat" 2>/dev/null
pkill -f cloudflared 2>/dev/null
sleep 2

rm -f "$PIDS_DIR"/*.pid 2>/dev/null
rm -f "$LOGS_DIR/celerybeat-schedule"* 2>/dev/null
log_success "تم التنظيف"

# تشغيل Celery Worker
log "⚙️ تشغيل Celery Worker..."
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
    --detach >> "$STARTUP_LOG" 2>&1

sleep 3
if [ -f "$PIDS_DIR/celery_worker.pid" ] && kill -0 $(cat "$PIDS_DIR/celery_worker.pid") 2>/dev/null; then
    log_success "تم تشغيل Celery Worker (PID: $(cat $PIDS_DIR/celery_worker.pid))"
else
    log_error "فشل في تشغيل Celery Worker"
    # لا نوقف التنفيذ، سيحاول monitor إعادة التشغيل
fi

# تشغيل Celery Beat
log "⏰ تشغيل Celery Beat..."
celery -A crm beat \
    --loglevel=warning \
    --pidfile="$PIDS_DIR/celery_beat.pid" \
    --logfile="$LOGS_DIR/celery_beat.log" \
    --schedule="$LOGS_DIR/celerybeat-schedule" \
    --detach >> "$STARTUP_LOG" 2>&1

sleep 3
if [ -f "$PIDS_DIR/celery_beat.pid" ] && kill -0 $(cat "$PIDS_DIR/celery_beat.pid") 2>/dev/null; then
    log_success "تم تشغيل Celery Beat (PID: $(cat $PIDS_DIR/celery_beat.pid))"
else
    log_error "فشل في تشغيل Celery Beat"
    # لا نوقف التنفيذ، سيحاول monitor إعادة التشغيل
fi

# تشغيل Cloudflare Tunnel
log "🌐 تشغيل Cloudflare Tunnel..."
if [ -f "$PROJECT_DIR/cloudflared" ]; then
    chmod +x "$PROJECT_DIR/cloudflared"
    "$PROJECT_DIR/cloudflared" tunnel --config "$PROJECT_DIR/cloudflared.yml" run >> "$LOGS_DIR/cloudflared.log" 2>&1 &
    echo $! > "$PIDS_DIR/cloudflared.pid"
    sleep 5
    
    if kill -0 $(cat "$PIDS_DIR/cloudflared.pid") 2>/dev/null; then
        log_success "تم تشغيل Cloudflare Tunnel (PID: $(cat $PIDS_DIR/cloudflared.pid))"
        log "🌐 الموقع متاح على: https://elkhawaga.uk"
    else
        log_error "فشل في تشغيل Cloudflare Tunnel"
    fi
else
    log_error "ملف cloudflared غير موجود"
fi

# تشغيل سكريبت النسخ الاحتياطي
log "💾 تشغيل خدمة النسخ الاحتياطي..."
if [ -f "$PROJECT_DIR/لينكس/db-backup.sh" ]; then
    # تصدير متغيرات قاعدة البيانات
    eval $(python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','crm.settings')
import django
django.setup()
from django.conf import settings
print(f"export DB_NAME='{settings.DATABASES['default'].get('NAME','')}'")
print(f"export DB_USER='{settings.DATABASES['default'].get('USER','')}'")
print(f"export DB_HOST='{settings.DATABASES['default'].get('HOST','')}'")
print(f"export DB_PORT='{settings.DATABASES['default'].get('PORT','')}'")
print(f"export DB_PASSWORD='{settings.DATABASES['default'].get('PASSWORD','')}'")
PY
)
    chmod +x "$PROJECT_DIR/لينكس/db-backup.sh"
    "$PROJECT_DIR/لينكس/db-backup.sh" >> "$LOGS_DIR/db_backup.log" 2>&1 &
    echo $! > "$PIDS_DIR/db_backup.pid"
    log_success "تم تشغيل خدمة النسخ الاحتياطي"
fi

# تشغيل Gunicorn
log "🚀 تشغيل خادم الويب Gunicorn..."
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
    --daemon >> "$STARTUP_LOG" 2>&1

sleep 3
if [ -f "$PIDS_DIR/gunicorn.pid" ] && kill -0 $(cat "$PIDS_DIR/gunicorn.pid") 2>/dev/null; then
    log_success "تم تشغيل Gunicorn (PID: $(cat $PIDS_DIR/gunicorn.pid))"
    log "🌐 الموقع المحلي: http://localhost:8000"
else
    log_error "فشل في تشغيل Gunicorn"
    exit 1
fi

log "========================================"
log "🎉 تم تشغيل جميع الخدمات بنجاح!"
log "📊 السجلات في: $LOGS_DIR"
log "========================================"

# بدء المراقبة في الخلفية
"$PROJECT_DIR/لينكس/monitor-service.sh" >> "$LOGS_DIR/monitor.log" 2>&1 &
echo $! > "$PIDS_DIR/monitor.pid"

exit 0
