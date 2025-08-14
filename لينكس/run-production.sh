#!/bin/bash
# 🚀 تشغيل النظام للإنتاج مع مراقبة مبسطة

RED='\033[0;31m'
GREEN='\033[0;32m'
WHITE='\033[1;37m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD_BLUE='\033[1;34m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"

print_status() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }
print_info() { echo -e "${WHITE}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }
print_tunnel() { echo -e "${BLUE}$1${NC}"; }
print_login() { echo -e "${BOLD_BLUE}$1${NC}"; }

# متغيرات لمراقبة التانل
TUNNEL_STATUS="unknown"
TUNNEL_CHECK_INTERVAL=30

# دالة فحص حالة التانل
check_tunnel_status() {
    if [ ! -z "$TUNNEL_PID" ] && kill -0 $TUNNEL_PID 2>/dev/null; then
        # فحص الاتصال بالموقع
        if curl -s --max-time 10 https://elkhawaga.uk > /dev/null 2>&1; then
            if [ "$TUNNEL_STATUS" != "connected" ]; then
                TUNNEL_STATUS="connected"
                print_tunnel "🌐 الجسر متصل - الموقع متاح على: https://elkhawaga.uk"
            fi
            return 0
        else
            if [ "$TUNNEL_STATUS" != "disconnected" ]; then
                TUNNEL_STATUS="disconnected"
                print_warning "⚠️ الجسر منقطع - الموقع غير متاح حالياً"
            fi
            return 1
        fi
    else
        if [ "$TUNNEL_STATUS" != "stopped" ]; then
            TUNNEL_STATUS="stopped"
            print_error "❌ عملية الجسر متوقفة"
        fi
        return 1
    fi
}

if [ ! -d "$PROJECT_DIR" ]; then print_error "مجلد المشروع غير موجود: $PROJECT_DIR"; exit 1; fi
cd "$PROJECT_DIR"

# تفعيل البيئة الافتراضية للمشروع
source "$PROJECT_DIR/venv/bin/activate"

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
    if [ ! -z "$GUNICORN_PID" ]; then kill $GUNICORN_PID 2>/dev/null; print_status "تم إيقاف خادم الويب"; fi
    exit 0
}
trap cleanup INT TERM

print_status "🚀 بدء خادم الإنتاج..."
print_info "الموقع: https://elkhawaga.uk"
print_info "المستخدم: admin | كلمة المرور: admin123"
print_info "Ctrl+C للإيقاف"

gunicorn crm.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --keep-alive 2 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --access-logformat '[%(t)s] "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' 2>&1 | while read line; do
        # تطبيق فلتر logs أولاً
        # تجاهل رسائل gunicorn access logs التي تبدأ بـ [[
        if [[ "$line" =~ ^\[\[.*\]\] ]]; then
            continue
        fi

        if [[ "$line" == *"/accounts/notifications/data/"* ]] || \
           [[ "$line" == *"/accounts/api/online-users/"* ]] || \
           [[ "$line" == *"/media/users/"* ]] || \
           [[ "$line" == *"/media/"* ]] || \
           [[ "$line" == *"/static/"* ]] || \
           [[ "$line" == *"favicon.ico"* ]]; then
            continue
        fi

        # معالجة رسائل تسجيل الدخول والخروج
        if [[ "$line" == *"🔐"* && "$line" == *"login"* ]]; then
            # استخراج اسم المستخدم من رسالة تسجيل الدخول
            username=$(echo "$line" | sed -n 's/.*🔐 \([^ ]*\) -.*/\1/p')
            if [ -n "$username" ]; then
                print_login "🔐 قام المستخدم $username بتسجيل الدخول"
            fi
        elif [[ "$line" == *"🚪"* && "$line" == *"logout"* ]]; then
            # استخراج اسم المستخدم من رسالة تسجيل الخروج
            username=$(echo "$line" | sed -n 's/.*🚪 \([^ ]*\) -.*/\1/p')
            if [ -n "$username" ]; then
                print_login "🚪 قام المستخدم $username بتسجيل الخروج"
            fi
        elif [[ "$line" == *"👁️"* && "$line" == *"page_view"* ]]; then
            # استخراج اسم المستخدم من رسالة عرض الصفحة
            username=$(echo "$line" | sed -n 's/.*👁️ \([^ ]*\) -.*/\1/p')
            if [ -n "$username" ]; then
                # عرض نشاط المستخدم المسجل
                page=$(echo "$line" | sed -n 's/.*page_view - \([^ ]*\).*/\1/p')
                echo -e "${WHITE}👁️ المستخدم $username يتصفح: $page${NC}"
            else
                # مستخدم غير معروف - استخراج IP
                ip=$(echo "$line" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
                if [ -n "$ip" ]; then
                    print_warning "🌐 تم فتح صفحة الموقع من مستخدم غير معروف - IP: $ip"
                fi
            fi
        elif [[ "$line" == *"🔄"* ]]; then
            # عرض عمليات تبديل الحالة والتحديثات
            username=$(echo "$line" | sed -n 's/.*🔄 \([^ ]*\) -.*/\1/p')
            if [ -n "$username" ]; then
                action=$(echo "$line" | sed -n 's/.*🔄 [^ ]* - \([^(]*\).*/\1/p')
                # استخراج كود الطلب إذا كان موجوداً
                order_code=$(echo "$line" | grep -oE 'ORD-[0-9]+' | head -1)
                if [ -n "$order_code" ]; then
                    echo -e "${YELLOW}🔄 المستخدم $username قام بـ: $action - الطلب: $order_code${NC}"
                else
                    echo -e "${YELLOW}🔄 المستخدم $username قام بـ: $action${NC}"
                fi
            fi
        elif [[ "$line" == *"✅"* || "$line" == *"❌"* || "$line" == *"⚠️"* ]]; then
            # عرض العمليات المهمة الأخرى
            username=$(echo "$line" | sed -n 's/.*[✅❌⚠️] \([^ ]*\) -.*/\1/p')
            if [ -n "$username" ]; then
                action=$(echo "$line" | sed -n 's/.*[✅❌⚠️] [^ ]* - \([^(]*\).*/\1/p')
                # استخراج كود الطلب إذا كان موجوداً
                order_code=$(echo "$line" | grep -oE 'ORD-[0-9]+' | head -1)
                if [ -n "$order_code" ]; then
                    echo -e "${GREEN}المستخدم $username: $action - الطلب: $order_code${NC}"
                else
                    echo -e "${GREEN}المستخدم $username: $action${NC}"
                fi
            fi
        else
            # عرض الرسائل الأخرى المهمة
            echo "$line"
        fi
    done &
GUNICORN_PID=$!
print_status "خادم الإنتاج يعمل (PID: $GUNICORN_PID)"

while true; do
    sleep 30

    # فحص خادم الويب
    if ! kill -0 $GUNICORN_PID 2>/dev/null; then
        print_error "❌ خادم الويب توقف!"
        break
    fi

    # فحص حالة التانل
    check_tunnel_status
    tunnel_ok=$?

    if [ $tunnel_ok -eq 0 ]; then
        print_status "✅ النظام يعمل بشكل طبيعي - الجسر متصل"
    else
        print_warning "⚠️ النظام يعمل محلياً - الجسر منقطع"
    fi
done

cleanup