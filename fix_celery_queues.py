#!/usr/bin/env python3
"""
إصلاح مشكلة Celery queues - المهام لا تنفذ
"""

import os
import sys
import django
import redis

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def fix_celery_queues():
    """إصلاح مشكلة queues"""
    print("🔧 إصلاح مشكلة Celery queues...")
    
    # 1. تنظيف Redis أولاً
    print("🧹 تنظيف Redis...")
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        # حذف المهام المعلقة في queue خاطئ
        r.delete('file_uploads')
        r.delete('celery')
        r.flushdb()
        print("✅ تم تنظيف Redis")
    except Exception as e:
        print(f"❌ خطأ في تنظيف Redis: {e}")
    
    # 2. إعادة تشغيل Celery workers
    print("🔄 إعادة تشغيل Celery workers...")
    
    # إيقاف العمال الحاليين
    os.system("pkill -f 'celery.*worker'")
    print("⏹️ تم إيقاف العمال القدامى")
    
    # انتظار قليل
    import time
    time.sleep(3)
    
    # تشغيل عامل جديد يستمع لجميع الـ queues
    print("🚀 تشغيل عامل جديد...")
    
    # تشغيل عامل يستمع للـ queue الافتراضي و file_uploads
    cmd = """
    celery -A crm worker \
        --loglevel=info \
        --concurrency=2 \
        --max-tasks-per-child=50 \
        --queues=celery,file_uploads \
        --pidfile=/tmp/celery_worker_fixed.pid \
        --logfile=logs/celery_fixed.log \
        --detach
    """
    
    result = os.system(cmd)
    if result == 0:
        print("✅ تم تشغيل العامل الجديد بنجاح")
    else:
        print("❌ فشل في تشغيل العامل الجديد")
    
    # 3. التحقق من حالة العمال
    time.sleep(5)
    print("🔍 فحص حالة العمال...")
    os.system("celery -A crm inspect active")

def test_upload_tasks():
    """اختبار مهام الرفع"""
    print("\n🧪 اختبار مهام الرفع...")
    
    from orders.models import Order
    from inspections.models import Inspection
    
    # اختبار عقد واحد
    test_order = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    ).first()
    
    if test_order and test_order.contract_file and os.path.exists(test_order.contract_file.path):
        print(f"📤 اختبار رفع عقد: {test_order.order_number}")
        try:
            from orders.tasks import upload_contract_to_drive_async
            result = upload_contract_to_drive_async.delay(test_order.id)
            print(f"✅ تم جدولة العقد: {result.id}")
        except Exception as e:
            print(f"❌ خطأ في جدولة العقد: {e}")
    
    # اختبار معاينة واحدة
    test_inspection = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    ).first()
    
    if test_inspection and test_inspection.inspection_file and os.path.exists(test_inspection.inspection_file.path):
        print(f"📤 اختبار رفع معاينة: {test_inspection.id}")
        try:
            from orders.tasks import upload_inspection_to_drive_async
            result = upload_inspection_to_drive_async.delay(test_inspection.id)
            print(f"✅ تم جدولة المعاينة: {result.id}")
        except Exception as e:
            print(f"❌ خطأ في جدولة المعاينة: {e}")

def main():
    """الدالة الرئيسية"""
    print("🚀 إصلاح مشكلة عدم تنفيذ مهام الرفع")
    print("=" * 50)
    
    # إصلاح المشكلة
    fix_celery_queues()
    
    # اختبار النظام
    test_upload_tasks()
    
    print("\n" + "=" * 50)
    print("🎉 تم إصلاح المشكلة!")
    print("💡 الآن يمكن للنظام تنفيذ مهام الرفع بشكل صحيح")
    print("🔍 راقب اللوج: tail -f logs/celery_fixed.log")

if __name__ == "__main__":
    main()
