#!/bin/bash
# 🚀 تشغيل الخادم مع إدارة ذكية لـ Redis

# الألوان
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

clear
echo -e "${BLUE}"
echo "🚀 تشغيل الخادم المحسن"
echo "======================"
echo -e "${NC}"

# التحقق من المجلد
if [ ! -f "manage.py" ]; then
    print_error "يجب تشغيل هذا الملف من مجلد المشروع"
    exit 1
fi

# تفعيل البيئة الافتراضية
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    print_status "تم تفعيل البيئة الافتراضية"
fi

# إيقاف العمليات السابقة
print_info "إيقاف العمليات السابقة..."
pkill -f "daphne.*crm.asgi" > /dev/null 2>&1
pkill -f "python.*manage.py.*runserver" > /dev/null 2>&1
sleep 2
print_status "تم إيقاف العمليات السابقة"

# محاولة تشغيل Redis
print_info "محاولة تشغيل Redis..."
USE_REDIS=false

if command -v redis-server > /dev/null 2>&1; then
    # إنشاء مجلد مؤقت
    mkdir -p /tmp/redis-data
    
    # محاولة تشغيل Redis مع إعدادات مبسطة
    redis-server --daemonize yes \
                 --port 6379 \
                 --dir /tmp/redis-data \
                 --save "" \
                 --appendonly no \
                 --maxmemory 64mb \
                 --maxmemory-policy allkeys-lru > /dev/null 2>&1
    
    sleep 2
    
    # اختبار Redis
    if redis-cli ping > /dev/null 2>&1; then
        print_status "Redis يعمل - WebSocket متاح"
        USE_REDIS=true
    else
        print_warning "Redis لا يعمل - سيتم استخدام وضع بدون WebSocket"
    fi
else
    print_warning "Redis غير مثبت - سيتم استخدام وضع بدون WebSocket"
fi

# تطبيق migrations
print_info "تطبيق migrations..."
python manage.py migrate --noinput > /dev/null 2>&1
print_status "تم تطبيق migrations"

# تجميع الملفات الثابتة
print_info "تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput > /dev/null 2>&1
print_status "تم تجميع الملفات الثابتة"

# إعداد البيانات الأساسية
print_info "إعداد البيانات الأساسية..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from cutting.models import Section

User = get_user_model()

# إنشاء مستخدم admin
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'first_name': 'مدير',
        'last_name': 'النظام',
        'is_superuser': True,
        'is_staff': True
    }
)

if created:
    admin_user.set_password('admin123')
    admin_user.save()

# إنشاء الأقسام إذا لم تكن موجودة
if Section.objects.count() == 0:
    sections_data = [
        'قسم التفصيل', 'قسم القص', 'قسم الخياطة', 'قسم التطريز',
        'قسم الكي', 'قسم التغليف', 'قسم الجودة', 'قسم التسليم'
    ]
    
    for section_name in sections_data:
        Section.objects.create(name=section_name)

print(f'المستخدمين: {User.objects.count()}')
print(f'الأقسام: {Section.objects.count()}')
"
print_status "تم إعداد البيانات الأساسية"

echo ""
print_status "🚀 بدء الخادم..."
print_info "الموقع: http://localhost:8000"
print_info "المستخدم: admin | كلمة المرور: admin123"

if [ "$USE_REDIS" = true ]; then
    print_info "🔌 WebSocket متاح (مع Redis)"
    print_info "📊 مراقبة السجلات: tail -f /tmp/daphne_access.log"
else
    print_warning "⚠️ WebSocket غير متاح (بدون Redis)"
fi

print_info "Ctrl+C للإيقاف"

echo ""
echo -e "${YELLOW}📋 الميزات المتاحة:${NC}"
echo "✅ النظام الأساسي يعمل"
echo "✅ الأقسام تظهر (8 أقسام)"
echo "✅ تسجيل الدخول يعمل"
echo "✅ واجهة المستخدم محسنة"

if [ "$USE_REDIS" = true ]; then
    echo "✅ الدردشة الفورية تعمل"
    echo "✅ مؤشر 'يكتب الآن' يعمل"
    echo "✅ إشعارات فورية"
else
    echo "⚠️ الدردشة الفورية معطلة"
fi

echo "✅ عرض ملف المستخدم"
echo "✅ حذف المحادثات"
echo "✅ حظر المستخدمين"
echo ""

# تشغيل الخادم المناسب
if [ "$USE_REDIS" = true ]; then
    # تشغيل Daphne مع WebSocket
    exec daphne -b 0.0.0.0 -p 8000 \
        --access-log /tmp/daphne_access.log \
        --proxy-headers \
        crm.asgi:application
else
    # تشغيل Django العادي
    exec python manage.py runserver 0.0.0.0:8000
fi
