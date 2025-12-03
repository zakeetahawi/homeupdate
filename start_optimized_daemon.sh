#!/bin/bash
# 🚀 تشغيل النظام كخدمة خلفية مع تسجيل كامل للسجلات
# يمكن تشغيله كـ systemd service للبدء التلقائي

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"

# إنشاء المجلدات المطلوبة
mkdir -p "$LOGS_DIR"
mkdir -p "$PID_DIR"

print_success() { 
    echo -e "${GREEN}✅ $1${NC}" 
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1" >> "$LOGS_DIR/startup.log"
}

print_error() { 
    echo -e "${RED}❌ $1${NC}" 
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1" >> "$LOGS_DIR/startup.log"
}

print_info() { 
    echo -e "${BLUE}ℹ️  $1${NC}" 
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1" >> "$LOGS_DIR/startup.log"
}

print_warning() { 
    echo -e "${YELLOW}⚠️  $1${NC}" 
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1" >> "$LOGS_DIR/startup.log"
}

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 نظام الخواجة - تشغيل كخدمة خلفية${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$PROJECT_DIR"

# تنظيف العمليات القديمة
print_info "تنظيف العمليات القديمة..."
pkill -9 gunicorn 2>/dev/null || true
pkill -9 celery 2>/dev/null || true
rm -f "$PID_DIR"/*.pid 2>/dev/null || true
sleep 2
print_success "تم التنظيف"

# تفعيل البيئة الافتراضية
print_info "تفعيل البيئة الافتراضية..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    print_error "البيئة الافتراضية غير موجودة في $PROJECT_DIR/venv"
    exit 1
fi

source "$PROJECT_DIR/venv/bin/activate"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export DJANGO_SETTINGS_MODULE=crm.settings
print_success "تم تفعيل البيئة"

# Redis
print_info "تشغيل Redis..."
if ! pgrep -x "redis-server\|valkey-server" > /dev/null; then
    if command -v valkey-server &> /dev/null; then
        valkey-server --daemonize yes \
            --port 6379 \
            --dir /tmp \
            --maxmemory 256mb \
            --maxmemory-policy allkeys-lru \
            --logfile "$LOGS_DIR/redis.log" \
            --pidfile "$PID_DIR/redis.pid"
    else
        redis-server --daemonize yes \
            --port 6379 \
            --dir /tmp \
            --maxmemory 256mb \
            --maxmemory-policy allkeys-lru \
            --logfile "$LOGS_DIR/redis.log" \
            --pidfile "$PID_DIR/redis.pid"
    fi
    sleep 2
    print_success "Redis يعمل الآن"
else
    print_success "Redis يعمل بالفعل"
fi

# Celery Worker (خلفي مع تسجيل كامل)
print_info "تشغيل Celery Worker..."
pkill -9 -f "celery.*worker" 2>/dev/null || true
sleep 1

celery -A crm worker \
    --loglevel=info \
    --pool=solo \
    --concurrency=1 \
    --max-memory-per-child=200000 \
    --time-limit=300 \
    --soft-time-limit=270 \
    --queues=celery,file_uploads \
    --pidfile="$PID_DIR/celery.pid" \
    --logfile="$LOGS_DIR/celery.log" \
    --detach

sleep 3

if [ -f "$PID_DIR/celery.pid" ] && kill -0 $(cat "$PID_DIR/celery.pid") 2>/dev/null; then
    print_success "Celery Worker جاهز - PID: $(cat $PID_DIR/celery.pid)"
else
    print_warning "Celery غير متاح (اختياري)"
fi

# Celery Beat (للمهام المجدولة - اختياري)
if [ -f "$PROJECT_DIR/crm/celery.py" ] && grep -q "beat_schedule" "$PROJECT_DIR/crm/celery.py" 2>/dev/null; then
    print_info "تشغيل Celery Beat للمهام المجدولة..."
    pkill -9 -f "celery.*beat" 2>/dev/null || true
    
    celery -A crm beat \
        --loglevel=info \
        --pidfile="$PID_DIR/celery-beat.pid" \
        --logfile="$LOGS_DIR/celery-beat.log" \
        --detach
    
    sleep 2
    if [ -f "$PID_DIR/celery-beat.pid" ]; then
        print_success "Celery Beat جاهز"
    fi
fi

# الحصول على IP
LOCAL_IP=$(ip addr show | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d/ -f1 | head -1)

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
print_info "بدء Gunicorn في الخلفية..."

# Gunicorn كخدمة خلفية مع تسجيل كامل
gunicorn crm.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --worker-connections 100 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 90 \
    --graceful-timeout 20 \
    --keep-alive 3 \
    --worker-tmp-dir /dev/shm \
    --error-logfile "$LOGS_DIR/gunicorn-error.log" \
    --access-logfile "$LOGS_DIR/gunicorn-access.log" \
    --log-level info \
    --pid "$PID_DIR/gunicorn.pid" \
    --daemon

sleep 3

# التحقق من التشغيل
if [ -f "$PID_DIR/gunicorn.pid" ] && kill -0 $(cat "$PID_DIR/gunicorn.pid") 2>/dev/null; then
    GUNICORN_PID=$(cat "$PID_DIR/gunicorn.pid")
    print_success "Gunicorn يعمل - PID: $GUNICORN_PID"
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 النظام يعمل في الخلفية بنجاح!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📍 http://localhost:8000${NC}"
    echo -e "${BLUE}📍 http://$LOCAL_IP:8000${NC}"
    echo -e "${YELLOW}🔐 admin / admin123${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}📊 ملفات السجلات:${NC}"
    echo -e "   • النظام: $LOGS_DIR/gunicorn-error.log"
    echo -e "   • الوصول: $LOGS_DIR/gunicorn-access.log"
    echo -e "   • Celery: $LOGS_DIR/celery.log"
    echo -e "   • بدء التشغيل: $LOGS_DIR/startup.log"
    echo ""
    echo -e "${BLUE}🔍 المراقبة:${NC}"
    echo -e "   tail -f $LOGS_DIR/gunicorn-error.log"
    echo -e "   tail -f $LOGS_DIR/celery.log"
    echo ""
    echo -e "${BLUE}⏹️  الإيقاف:${NC}"
    echo -e "   kill \$(cat $PID_DIR/gunicorn.pid)"
    echo -e "   kill \$(cat $PID_DIR/celery.pid)"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # حفظ معلومات التشغيل
    cat > "$PID_DIR/service_info.txt" <<EOF
تم بدء النظام: $(date '+%Y-%m-%d %H:%M:%S')
Gunicorn PID: $GUNICORN_PID
Celery PID: $(cat $PID_DIR/celery.pid 2>/dev/null || echo "غير متاح")
العنوان المحلي: http://localhost:8000
عنوان الشبكة: http://$LOCAL_IP:8000
EOF
    
    exit 0
else
    print_error "فشل تشغيل Gunicorn - راجع $LOGS_DIR/gunicorn-error.log"
    exit 1
fi
