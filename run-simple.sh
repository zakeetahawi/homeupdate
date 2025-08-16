#!/bin/bash

# ألوان للنص
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
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

print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

# التأكد من وجود البيئة الافتراضية
if [ ! -d "venv" ]; then
    print_warning "البيئة الافتراضية غير موجودة"
    exit 1
fi

# تفعيل البيئة الافتراضية
source venv/bin/activate

print_header "🚀 تشغيل النظام المحلي البسيط"

print_info "🔧 إعداد الذاكرة..."
sudo sysctl vm.overcommit_memory=1 > /dev/null 2>&1

print_info "📦 تطبيق الترحيلات..."
python manage.py migrate --noinput > /dev/null 2>&1

print_info "📁 تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput > /dev/null 2>&1

print_success "🎯 النظام جاهز!"
print_info "📍 الموقع: http://localhost:8000"
print_info "👤 المستخدم: admin | كلمة المرور: admin123"
print_info "🔄 Redis + Celery + Django سيتم تشغيلهم تلقائياً"
print_success "استخدم Ctrl+C لإيقاف جميع الخدمات"

echo
print_header "🎯 بدء التشغيل"

# تشغيل Django مع جميع الخدمات (manage.py محسن ليشغل كل شيء)
python manage.py runserver 0.0.0.0:8000
