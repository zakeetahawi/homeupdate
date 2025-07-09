#!/bin/bash
# 🏠 تشغيل السيرفر المحلي مع مراقبة مفصلة

RED='\033[0;31m'
GREEN='\033[0;32m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"

print_status() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }
print_info() { echo -e "${WHITE}$1${NC}"; }
print_local() { echo -e "${PURPLE}$1${NC}"; }
print_debug() { echo -e "${CYAN}$1${NC}"; }

if [ ! -d "$PROJECT_DIR" ]; then print_error "مجلد المشروع غير موجود: $PROJECT_DIR"; exit 1; fi
cd "$PROJECT_DIR"

print_info "عرض معلومات النظام..."
print_debug "مسار المشروع: $PROJECT_DIR"
print_debug "إصدار Python: $(python --version)"
print_debug "إصدار Django: $(python -c 'import django; print(django.get_version())')"

print_info "تشغيل التحديثات..."
python manage.py migrate --noinput
print_status "✔️ تم تطبيق التحديثات"

print_info "تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput
print_status "✔️ تم تجميع الملفات الثابتة"

print_info "فحص المستخدمين..."
USER_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; print(User.objects.count())")
if [ "$USER_COUNT" -eq 0 ]; then
  print_status "لا يوجد مستخدمين، سيتم إنشاء admin/admin123"
  python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); print('تم إنشاء المستخدم admin/admin123')"
else
  print_status "عدد المستخدمين الحالي: $USER_COUNT (لن يتم إنشاء مستخدم جديد)"
fi

cleanup() {
    print_info "إيقاف العمليات..."
    if [ ! -z "$DJANGO_PID" ]; then kill $DJANGO_PID 2>/dev/null; print_status "تم إيقاف خادم Django"; fi
    exit 0
}
trap cleanup INT TERM

print_status "🏠 بدء خادم Django المحلي..."
print_local "الموقع: http://localhost:8000"
print_local "المستخدم: admin | كلمة المرور: admin123"
print_local "وضع التطوير - تحديث تلقائي للملفات"
print_debug "بدون Cloudflare Tunnel - وصول محلي فقط"
print_info "Ctrl+C للإيقاف"

python manage.py runserver 0.0.0.0:8000 &
DJANGO_PID=$!
print_status "خادم Django يعمل (PID: $DJANGO_PID)"

COUNTER=0
while true; do
    sleep 10
    COUNTER=$((COUNTER + 1))
    if ! kill -0 $DJANGO_PID 2>/dev/null; then print_error "❌ خادم Django توقف!"; break; fi
    if [ $((COUNTER % 6)) -eq 0 ]; then print_status "✅ النظام يعمل بشكل طبيعي"; print_debug "الذاكرة: $(ps -o pid,vsz,rss,comm -p $DJANGO_PID | tail -1)"; fi
    if [ $((COUNTER % 30)) -eq 0 ]; then print_info "تقرير دوري - النظام يعمل منذ $((COUNTER * 10)) ثانية"; print_debug "الاتصالات: $(netstat -an | grep :8000 | grep ESTABLISHED | wc -l)"; fi
done

cleanup 