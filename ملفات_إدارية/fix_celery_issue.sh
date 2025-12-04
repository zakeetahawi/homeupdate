#!/bin/bash
# 🔧 إصلاح مشكلة Celery Worker - إعادة التشغيل الكاملة

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"

cd "$PROJECT_DIR"

print_warning "🔧 بدء إصلاح مشكلة Celery Worker..."

# 1. إيقاف جميع عمليات Celery Worker القديمة
print_status "1️⃣ إيقاف جميع عمليات Celery Worker القديمة..."
pkill -f "celery.*worker" 2>/dev/null
sleep 3

# التأكد من إيقافها
if pgrep -f "celery.*worker" > /dev/null; then
    print_warning "⚠️ بعض العمليات لا تزال تعمل - استخدام kill -9..."
    pkill -9 -f "celery.*worker" 2>/dev/null
    sleep 2
fi

if pgrep -f "celery.*worker" > /dev/null; then
    print_error "❌ فشل في إيقاف جميع عمليات Celery"
else
    print_status "✅ تم إيقاف جميع عمليات Celery Worker"
fi

# 2. تنظيف الملفات القديمة
print_status "2️⃣ تنظيف الملفات القديمة..."
rm -f "$LOGS_DIR/celery_worker.pid"
rm -f "$LOGS_DIR/celery_worker.log"
print_status "✅ تم تنظيف الملفات"

# 3. تنظيف السجلات العالقة في قاعدة البيانات
print_status "3️⃣ تنظيف السجلات العالقة في قاعدة البيانات..."
python << 'PYTHON_SCRIPT'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import BulkUploadLog
from django.utils import timezone

# تحديث السجلات العالقة
stuck_logs = BulkUploadLog.objects.filter(status='processing')
count = stuck_logs.count()

if count > 0:
    print(f"   وجدت {count} سجل عالق")
    for log in stuck_logs:
        log.status = 'failed'
        log.completed_at = timezone.now()
        log.summary = f"فشل: Celery Worker كان متوقفاً - تم إعادة تعيين الحالة تلقائياً"
        log.save()
    print(f"   ✅ تم تحديث {count} سجل عالق")
else:
    print("   ✅ لا توجد سجلات عالقة")
PYTHON_SCRIPT

# 4. تنظيف Redis
print_status "4️⃣ تنظيف طوابير Redis..."
redis-cli -n 0 DEL celery 2>/dev/null || true
redis-cli -n 0 DEL file_uploads 2>/dev/null || true
print_status "✅ تم تنظيف Redis"

# 5. تفعيل البيئة الافتراضية
source "$PROJECT_DIR/venv/bin/activate"

# 6. إعادة تشغيل Celery Worker مع تحميل المهام الجديدة
print_status "5️⃣ إعادة تشغيل Celery Worker مع تحميل المهام المحسنة..."
cd "$PROJECT_DIR"

celery -A crm worker \
    --loglevel=info \
    --queues=celery,file_uploads \
    --pidfile="$LOGS_DIR/celery_worker.pid" \
    --logfile="$LOGS_DIR/celery_worker.log" \
    --pool=solo \
    --concurrency=2 \
    --max-tasks-per-child=50 \
    --detach

sleep 5

# 7. التحقق من نجاح التشغيل
if [ -f "$LOGS_DIR/celery_worker.pid" ]; then
    CELERY_PID=$(cat "$LOGS_DIR/celery_worker.pid")
    if ps -p $CELERY_PID > /dev/null; then
        print_status "✅ تم تشغيل Celery Worker بنجاح (PID: $CELERY_PID)"
        
        # 8. اختبار المهمة
        print_status "6️⃣ اختبار تسجيل المهام..."
        python << 'TEST_SCRIPT'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from celery import current_app

# التحقق من تسجيل المهمة
task_name = 'inventory.tasks_optimized.bulk_upload_products_fast'
if task_name in current_app.tasks:
    print(f"   ✅ المهمة {task_name} مسجلة بنجاح!")
else:
    print(f"   ❌ المهمة {task_name} غير مسجلة")
    print("   📋 المهام المسجلة:")
    for task in sorted(current_app.tasks.keys()):
        if 'inventory' in task or 'bulk' in task:
            print(f"      - {task}")
TEST_SCRIPT
    else
        print_error "❌ فشل في تشغيل Celery Worker"
        tail -20 "$LOGS_DIR/celery_worker.log"
    fi
else
    print_error "❌ لم يتم إنشاء ملف PID"
fi

print_status ""
print_status "="*60
print_status "🎉 تم الإصلاح!"
print_status "="*60
print_warning "⚠️ ملاحظات مهمة:"
echo "   1. تم تنظيف جميع السجلات العالقة"
echo "   2. تم إعادة تشغيل Celery Worker"
echo "   3. يمكنك الآن رفع الملفات بالجملة من جديد"
echo ""
print_status "📊 لمتابعة سجلات Celery:"
echo "   tail -f $LOGS_DIR/celery_worker.log"
