#!/bin/bash
# 🛠️ تشغيل النظام للتطوير مع مراقبة مبسطة

RED='\033[0;31m'
GREEN='\033[0;32m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"

print_status() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }
print_info() { echo -e "${WHITE}$1${NC}"; }
print_dev() { echo -e "${CYAN}$1${NC}"; }

if [ ! -d "$PROJECT_DIR" ]; then print_error "مجلد المشروع غير موجود: $PROJECT_DIR"; exit 1; fi
cd "$PROJECT_DIR"

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

print_info "تشغيل Cloudflare Tunnel..."
if [ -f "cloudflared" ]; then
    ./cloudflared tunnel --config cloudflared.yml run > /dev/null 2>&1 &
    TUNNEL_PID=$!
    print_status "تم تشغيل Cloudflare Tunnel (PID: $TUNNEL_PID)"
else
    print_error "ملف cloudflared غير موجود"
fi

cleanup() {
    print_info "إيقاف العمليات..."
    if [ ! -z "$TUNNEL_PID" ]; then kill $TUNNEL_PID 2>/dev/null; print_status "تم إيقاف Cloudflare Tunnel"; fi
    if [ ! -z "$GUNICORN_PID" ]; then kill $GUNICORN_PID 2>/dev/null; print_status "تم إيقاف خادم التطوير"; fi
    exit 0
}
trap cleanup INT TERM

print_status "🛠️ بدء خادم التطوير..."
print_info "الموقع: https://elkhawaga.uk"
print_info "المستخدم: admin | كلمة المرور: admin123"
print_dev "وضع التطوير - إعادة تحميل تلقائية"
print_info "Ctrl+C للإيقاف"

gunicorn crm.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --worker-class sync \
    --timeout 60 \
    --keep-alive 5 \
    --reload \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --access-logformat '[%(t)s] "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' &
GUNICORN_PID=$!
print_status "خادم التطوير يعمل (PID: $GUNICORN_PID)"

while true; do
    sleep 30
    if ! kill -0 $GUNICORN_PID 2>/dev/null; then print_error "❌ خادم التطوير توقف!"; break; fi
    print_status "✅ النظام يعمل بشكل طبيعي"
done

cleanup 