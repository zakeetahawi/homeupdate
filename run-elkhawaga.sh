#!/bin/bash
# Elkhawaga Trading - elkhawaga.uk (Linux)

clear

echo "========================================"
echo "   ELKHAWAGA TRADING SYSTEM"
echo "   https://elkhawaga.uk"
echo "   PRODUCTION SERVER"
echo "========================================"
echo

cd "$(dirname "$0")"

CRED_FILE="$(pwd)/cloudflare-credentials.json"
echo "[INFO] Using credentials file: $CRED_FILE"

if [ ! -f "$CRED_FILE" ]; then
  echo "[ERROR] Credentials file not found at: $CRED_FILE"
  exit 1
fi

# البحث عن البيئة الافتراضية وتفعيلها
VENV_DIR=""

# البحث عن مجلد البيئة الافتراضية
if [ -d ".venv" ]; then
  VENV_DIR=".venv"
elif [ -d "venv" ]; then
  VENV_DIR="venv"
else
  echo "[INFO] Creating Python virtual environment..."
  python3 -m venv .venv || { echo "[ERROR] Failed to create virtual environment"; exit 1; }
  VENV_DIR=".venv"
fi

# تفعيل البيئة الافتراضية
echo "[INFO] Activating Python virtual environment from $VENV_DIR..."
source "$VENV_DIR/bin/activate"

# التأكد من تفعيل البيئة الافتراضية
if [ -z "$VIRTUAL_ENV" ]; then
  echo "[ERROR] Failed to activate virtual environment. Please check venv setup."
  exit 1
else
  echo "[OK] Python virtual environment activated: $VIRTUAL_ENV"
  # تحديث مسار Python ليشير إلى Python الموجود في البيئة الافتراضية
  PYTHON="$VENV_DIR/bin/python3"
  PIP="$VENV_DIR/bin/pip"
fi

# Kill any existing processes
echo "[INFO] Stopping any existing Django and cloudflared processes..."
pkill -f manage.py > /dev/null 2>&1
pkill -f cloudflared > /dev/null 2>&1
sleep 2

echo "[INFO] Checking requirements..."
command -v python3 > /dev/null 2>&1 || { echo "[ERROR] Python3 not found! Please install Python3 first."; exit 1; }
[ -d "venv" ] || { echo "[INFO] Creating Python virtual environment..."; python3 -m venv venv || { echo "[ERROR] Failed to create virtual environment"; exit 1; }; }
[ -f "cloudflared" ] || { echo "[ERROR] cloudflared not found!"; exit 1; }
[ -f "cloudflared.yml" ] || { echo "[ERROR] cloudflared.yml not found!"; exit 1; }
[ -f "$CRED_FILE" ] || { echo "[ERROR] cloudflare-credentials.json not found!"; exit 1; }
echo "[OK] All requirements met"

# تنفيذ الترحيلات
echo -e "\n[INFO] جاري تنفيذ الترحيلات..."
if ! $PYTHON manage.py migrate; then
    echo "[ERROR] فشل في تنفيذ الترحيلات. جاري محاولة إنشاء الترحيلات أولاً..."
    if ! $PYTHON manage.py makemigrations; then
        echo "[ERROR] فشل في إنشاء الترحيلات"
        exit 1
    fi
    if ! $PYTHON manage.py migrate; then
        echo "[ERROR] فشل في تنفيذ الترحيلات بعد المحاولة الثانية"
        exit 1
    fi
fi

# التحقق من وجود مستخدمين وإنشاء مستخدم افتراضي إذا لزم الأمر
USER_COUNT=$($PYTHON -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elkhawaga.settings'); import django; django.setup(); from django.contrib.auth import get_user_model; print(get_user_model().objects.count())" 2>/dev/null || echo "0")

if [ "$USER_COUNT" -eq 0 ]; then
    echo -e "\n[WARNING] لا يوجد مستخدمين في قاعدة البيانات"
    echo -e "[INFO] جاري إنشاء مستخدم افتراضي..."
    
    $PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elkhawaga.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@elkhawaga.uk', 'admin123')
    print('تم إنشاء المستخدم الافتراضي بنجاح')
else:
    print('المستخدم الافتراضي موجود مسبقاً')
"
    if [ $? -ne 0 ]; then
        echo "[WARNING] فشل في إنشاء المستخدم الافتراضي. يمكنك إنشاؤه يدوياً لاحقاً."
    else
        echo -e "[SUCCESS] تم إنشاء المستخدم الافتراضي بنجاح"
        echo -e "  اسم المستخدم: admin"
        echo -e "  كلمة المرور: admin123"
        echo -e "  الرجاء تغيير كلمة المرور فور تسجيل الدخول"
    fi
fi

echo "[INFO] جاري تجميع الملفات الثابتة..."
$PYTHON manage.py collectstatic --noinput --clear

mkdir -p cache

echo
# بدء تشغيل سيرفر Django
for i in {1..3}; do
    echo "[INFO] محاولة تشغيل سيرفر Django (المحاولة $i/3)..."
    $PYTHON manage.py runserver 127.0.0.1:8000 &
    DJANGO_PID=$!
    
    # الانتظار لبدء السيرفر
    sleep 5
    
    # التحقق من أن السيرفر يعمل
    if ps -p $DJANGO_PID > /dev/null; then
        echo "[SUCCESS] تم تشغيل سيرفر Django بنجاح (PID: $DJANGO_PID)"
        break
    else
        echo "[WARNING] فشل تشغيل سيرفر Django (المحاولة $i/3)"
        if [ $i -eq 3 ]; then
            echo "[ERROR] فشل تشغيل سيرفر Django بعد 3 محاولات"
            exit 1
        fi
    fi
done

# Wait for Django to start
echo "[INFO] Waiting for Django to initialize..."
for i in {1..10}; do
    if netstat -an | grep -q ":8000"; then
        echo "[OK] Django server is running successfully (PID: $DJANGO_PID)"
        break
    else
        echo "[INFO] Checking Django startup attempt $i/10..."
        sleep 2
    fi
done

echo "[INFO] Starting Cloudflare Tunnel..."
chmod +x cloudflared
./cloudflared tunnel --config ./cloudflared.yml --credentials-file "$CRED_FILE" run &
CLOUDFLARED_PID=$!

# عرض تفاصيل العمليات في الطرفية
trap 'echo "\n[INFO] Stopping all processes..."; kill $DJANGO_PID $CLOUDFLARED_PID 2>/dev/null; exit' SIGINT SIGTERM

echo "========================================"
echo "  SYSTEM IS NOW LIVE!"
echo "========================================"
echo "Your website is available at:"
echo "  Main Website:    https://elkhawaga.uk"
echo "  WWW Website:     https://www.elkhawaga.uk"
echo "  CRM System:      https://crm.elkhawaga.uk"
echo "  Admin Panel:     https://admin.elkhawaga.uk/admin/"
echo "  API Access:      https://api.elkhawaga.uk"
echo "========================================"
echo "  Status: ONLINE - SSL: ENABLED"
echo "========================================"
echo "Keep this window open while using the website"
echo "Press Ctrl+C to stop the server"
echo

# متابعة تفاصيل العمليات بشكل حي
wait $DJANGO_PID
wait $CLOUDFLARED_PID
