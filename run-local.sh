#!/bin/bash

# ألوان للنص
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# التأكد من وجود البيئة الافتراضية
if [ ! -d "venv" ]; then
    print_warning "البيئة الافتراضية غير موجودة"
    exit 1
fi

# تفعيل البيئة الافتراضية
source venv/bin/activate

print_info "🚀 تشغيل النظام المحلي مع جميع الخدمات..."
print_info "📍 الموقع: http://localhost:8000"
print_info "👤 المستخدم: admin | كلمة المرور: admin123"
print_info "🔄 Redis + Celery + Django سيتم تشغيلهم تلقائياً"
print_info "📊 مراقبة Celery: tail -f /tmp/celery_worker_dev.log"
print_info "⏰ مراقبة المهام الدورية: tail -f /tmp/celery_beat_dev.log"
print_success "استخدم Ctrl+C لإيقاف جميع الخدمات"

echo
print_success "🎯 بدء التشغيل..."

# تشغيل Celery Worker في الخلفية
print_info "🔄 تشغيل Celery Worker..."
celery -A crm worker --loglevel=info --logfile=/tmp/celery_worker_dev.log &
CELERY_WORKER_PID=$!

# تشغيل Celery Beat في الخلفية
print_info "⏰ تشغيل Celery Beat..."
celery -A crm beat --loglevel=info --logfile=/tmp/celery_beat_dev.log &
CELERY_BEAT_PID=$!

# دالة لإيقاف الخدمات عند الخروج
cleanup() {
    print_warning "إيقاف الخدمات..."
    kill $CELERY_WORKER_PID 2>/dev/null
    kill $CELERY_BEAT_PID 2>/dev/null
    exit 0
}

# التقاط إشارة Ctrl+C
trap cleanup SIGINT

# تشغيل Django
python manage.py runserver 0.0.0.0:8000
