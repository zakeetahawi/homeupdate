#!/bin/bash
# سكريبت تشغيل بيئة التطوير

cd "$(dirname "$0")"

echo "🚀 بدء تشغيل بيئة التطوير"
echo "================================"

# تفعيل البيئة الافتراضية
source venv/bin/activate

# إيقاف العمليات القديمة
echo "🧹 تنظيف العمليات القديمة..."
pkill -f "celery -A crm worker" 2>/dev/null
pkill -f "celery -A crm beat" 2>/dev/null
sleep 1

# تشغيل Redis إذا لم يكن يعمل
if ! pgrep -x "redis-server" > /dev/null; then
    echo "📦 تشغيل Redis..."
    redis-server --daemonize yes
fi

# تشغيل Celery Worker
echo "⚙️  تشغيل Celery Worker..."
celery -A crm worker -l info --pool=solo \
    --pidfile=/tmp/celery_worker_dev.pid \
    --logfile=/tmp/celery_worker_dev.log \
    --detach

sleep 2

# تشغيل Celery Beat
echo "⏰ تشغيل Celery Beat..."
celery -A crm beat -l info \
    --pidfile=/tmp/celery_beat_dev.pid \
    --logfile=/tmp/celery_beat_dev.log \
    --schedule=/tmp/celerybeat-schedule-dev \
    --detach

sleep 1

# فحص Celery
if pgrep -f "celery -A crm worker" > /dev/null; then
    echo "✅ Celery Worker يعمل"
else
    echo "❌ فشل تشغيل Celery Worker"
fi

# تشغيل Django
echo ""
echo "🌐 تشغيل Django Server..."
echo "================================"
echo "📍 الموقع: http://localhost:8000"
echo "⚠️  اضغط Ctrl+C للإيقاف"
echo ""

python manage.py runserver
