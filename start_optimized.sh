#!/bin/bash
# 🚀 تشغيل سريع ومحسّن للنظام - بدون Cloudflare Tunnel

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 نظام الخواجة - إصدار محسّن${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$PROJECT_DIR"
mkdir -p "$LOGS_DIR"

# تنظيف العمليات القديمة
print_info "تنظيف العمليات القديمة..."
pkill -9 gunicorn 2>/dev/null || true
pkill -9 celery 2>/dev/null || true
rm -f /tmp/gunicorn.pid 2>/dev/null || true
rm -f "$LOGS_DIR"/*.pid 2>/dev/null || true
print_success "تم التنظيف"

# تفعيل البيئة الافتراضية
print_info "تفعيل البيئة..."
source "$PROJECT_DIR/venv/bin/activate"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
print_success "جاهز"

# Redis
print_info "تشغيل Redis..."
if ! pgrep -x "redis-server\|valkey-server" > /dev/null; then
    if command -v valkey-server &> /dev/null; then
        valkey-server --daemonize yes --port 6379 --dir /tmp --maxmemory 256mb --maxmemory-policy allkeys-lru
    else
        redis-server --daemonize yes --port 6379 --dir /tmp --maxmemory 256mb --maxmemory-policy allkeys-lru
    fi
    sleep 1
    print_success "Redis يعمل"
else
    print_success "Redis يعمل بالفعل"
fi

# Celery Worker (خفيف)
print_info "تشغيل Celery Worker..."
# تنظيف Celery القديم أولاً
pkill -9 -f "celery.*worker" 2>/dev/null || true
rm -f "$LOGS_DIR/celery.pid" 2>/dev/null || true

# التأكد من عدم وجود عملية سابقة
if ! pgrep -f "celery.*worker" > /dev/null; then
    celery -A crm worker \
        --loglevel=error \
        --pool=solo \
        --concurrency=1 \
        --max-memory-per-child=200000 \
        --time-limit=300 \
        --soft-time-limit=270 \
        --queues=celery,file_uploads \
        --pidfile="$LOGS_DIR/celery.pid" \
        --logfile="$LOGS_DIR/celery.log" \
        --detach 2>/dev/null
    sleep 2
    if [ -f "$LOGS_DIR/celery.pid" ]; then
        print_success "Celery جاهز"
    else
        print_warning "Celery غير متاح (اختياري)"
    fi
else
    print_success "Celery يعمل مسبقاً"
fi

# دالة التنظيف
cleanup() {
    echo ""
    print_info "إيقاف..."
    pkill -TERM gunicorn 2>/dev/null || true
    [ -f "$LOGS_DIR/celery.pid" ] && kill $(cat "$LOGS_DIR/celery.pid") 2>/dev/null || true
    print_success "تم الإيقاف"
    exit 0
}
trap cleanup INT TERM

# الحصول على IP
LOCAL_IP=$(ip addr show | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d/ -f1 | head -1)

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 النظام جاهز!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📍 http://localhost:8000${NC}"
echo -e "${BLUE}📍 http://$LOCAL_IP:8000${NC}"
echo -e "${YELLOW}🔐 admin / admin123${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Gunicorn محسّن للسرعة
exec gunicorn crm.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --threads 4 \
    --worker-class gthread \
    --worker-connections 100 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 90 \
    --graceful-timeout 20 \
    --keep-alive 3 \
    --worker-tmp-dir /dev/shm \
    --error-logfile - \
    --access-logfile - \
    --log-level warning \
    --pid /tmp/gunicorn.pid
