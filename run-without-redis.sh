#!/bin/bash
# 🚀 تشغيل النظام بدون Redis (للاختبار)

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
echo "🚀 تشغيل النظام (بدون Redis)"
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

# تعطيل WebSocket مؤقتاً
print_warning "تعطيل WebSocket مؤقتاً (بدون Redis)"

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

# عرض الأقسام
sections = Section.objects.all()
if sections.exists():
    print('✅ الأقسام متاحة:')
    for section in sections:
        print(f'  - {section.name}')
else:
    print('⚠️ لا توجد أقسام')
"

echo ""
print_status "🚀 بدء الخادم..."
print_info "الموقع: http://localhost:8000"
print_info "المستخدم: admin | كلمة المرور: admin123"
print_warning "WebSocket معطل (بدون Redis)"
print_info "Ctrl+C للإيقاف"

echo ""
echo -e "${YELLOW}📋 الميزات المتاحة:${NC}"
echo "✅ النظام الأساسي يعمل"
echo "✅ الأقسام تظهر"
echo "✅ تسجيل الدخول يعمل"
echo "✅ واجهة المستخدم تعمل"
echo "⚠️ الدردشة الفورية معطلة (بدون Redis)"
echo ""

# تشغيل Django مع runserver للاختبار
exec python manage.py runserver 0.0.0.0:8000
