#!/bin/bash
# 🚀 تشغيل مبسط للنظام

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
echo "🚀 تشغيل النظام مع WebSocket"
echo "============================="
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

# التحقق من Redis
print_info "فحص Redis..."
if pgrep -x "redis-server" > /dev/null; then
    print_status "Redis يعمل"
else
    print_info "تشغيل Redis..."

    # إنشاء مجلد مؤقت لـ Redis
    mkdir -p /tmp/redis-data

    # تشغيل Redis مع إعدادات محسنة
    redis-server --daemonize yes \
                 --port 6379 \
                 --dir /tmp/redis-data \
                 --save "" \
                 --appendonly no \
                 --maxmemory 128mb \
                 --maxmemory-policy allkeys-lru \
                 --tcp-keepalive 60 \
                 --timeout 0 > /dev/null 2>&1

    sleep 3

    if pgrep -x "redis-server" > /dev/null; then
        print_status "تم تشغيل Redis"
    else
        print_warning "فشل في تشغيل Redis - سيتم المحاولة بدون Redis"
        print_info "النظام سيعمل بدون WebSocket"
    fi
fi

# تطبيق migrations
print_info "تطبيق migrations..."
python manage.py migrate --noinput > /dev/null 2>&1
print_status "تم تطبيق migrations"

# تجميع الملفات الثابتة
print_info "تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput > /dev/null 2>&1
print_status "تم تجميع الملفات الثابتة"

# اختبار سريع
print_info "اختبار سريع..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from cutting.models import Section

User = get_user_model()
print(f'المستخدمين: {User.objects.count()}')
print(f'الأقسام: {Section.objects.count()}')

# إنشاء مستخدم admin إذا لم يكن موجوداً
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
    print('✅ تم إنشاء مستخدم admin')
else:
    print('✅ مستخدم admin موجود')
"

echo ""
print_status "🚀 بدء الخادم..."
print_info "الموقع: http://localhost:8000"
print_info "المستخدم: admin | كلمة المرور: admin123"
print_info "🔌 دعم WebSocket للدردشة الفورية"
print_info "Ctrl+C للإيقاف"

echo ""
echo -e "${YELLOW}🆕 الميزات الجديدة:${NC}"
echo "✅ رسائل فورية بدون تأخير"
echo "✅ مؤشر 'يكتب الآن' يعمل"
echo "✅ عرض ملف المستخدم"
echo "✅ حذف المحادثات"
echo "✅ حظر المستخدمين"
echo "✅ إشعارات محسنة"
echo "✅ أداء أفضل مع Daphne"
echo ""

# تشغيل Daphne
exec daphne -b 0.0.0.0 -p 8000 crm.asgi:application
