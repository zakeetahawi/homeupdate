#!/usr/bin/env python
"""
سكريبت لإصلاح المعاينات المعلقة وإعادة جدولة رفعها
"""

import os
import sys
import django
from datetime import datetime, timedelta

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection
from orders.tasks import upload_inspection_to_drive_async
from django.utils import timezone

def fix_pending_inspections():
    """إصلاح المعاينات المعلقة وإعادة جدولة رفعها"""
    
    print("🔍 البحث عن المعاينات المعلقة...")
    
    # البحث عن المعاينات التي لديها ملفات ولم يتم رفعها
    pending_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        is_uploaded_to_drive=False
    )
    
    print(f"📊 عدد المعاينات المعلقة: {pending_inspections.count()}")
    
    if not pending_inspections.exists():
        print("✅ لا توجد معاينات معلقة")
        return
    
    # عرض تفاصيل المعاينات المعلقة
    print("\n📋 المعاينات المعلقة:")
    for inspection in pending_inspections:
        print(f"  - معاينة #{inspection.id}: {inspection.customer.name if inspection.customer else 'عميل جديد'}")
        print(f"    الطلب: {inspection.order.order_number if inspection.order else 'غير محدد'}")
        print(f"    الملف: {inspection.inspection_file.name if inspection.inspection_file else 'لا يوجد'}")
        print(f"    تاريخ الإنشاء: {inspection.created_at}")
        print()
    
    # إعادة جدولة الرفع
    print("🔄 إعادة جدولة رفع المعاينات...")
    
    success_count = 0
    error_count = 0
    
    for inspection in pending_inspections:
        try:
            # التحقق من وجود الملف فعلياً
            if inspection.inspection_file and os.path.exists(inspection.inspection_file.path):
                # جدولة المهمة
                task = upload_inspection_to_drive_async.delay(inspection.id)
                print(f"✅ تم جدولة رفع المعاينة #{inspection.id} - Task ID: {task.id}")
                success_count += 1
            else:
                print(f"❌ المعاينة #{inspection.id}: الملف غير موجود")
                error_count += 1
                
        except Exception as e:
            print(f"❌ خطأ في جدولة المعاينة #{inspection.id}: {str(e)}")
            error_count += 1
    
    print(f"\n📊 النتائج:")
    print(f"✅ تم جدولة {success_count} معاينة بنجاح")
    print(f"❌ فشل في {error_count} معاينة")
    
    return success_count, error_count

def check_celery_status():
    """فحص حالة Celery"""
    print("🔍 فحص حالة Celery...")
    
    try:
        from celery import current_app
        
        # فحص الاتصال مع Redis
        inspect = current_app.control.inspect()
        
        # الحصول على العمال النشطين
        active_workers = inspect.active()
        if active_workers:
            print("✅ Celery Workers نشطة:")
            for worker, tasks in active_workers.items():
                print(f"  - {worker}: {len(tasks)} مهمة نشطة")
        else:
            print("❌ لا توجد Celery Workers نشطة")
        
        # فحص المهام المجدولة
        scheduled_tasks = inspect.scheduled()
        if scheduled_tasks:
            print("📅 المهام المجدولة:")
            for worker, tasks in scheduled_tasks.items():
                print(f"  - {worker}: {len(tasks)} مهمة مجدولة")
        
        # فحص قوائم الانتظار
        reserved_tasks = inspect.reserved()
        if reserved_tasks:
            print("⏳ المهام في قائمة الانتظار:")
            for worker, tasks in reserved_tasks.items():
                print(f"  - {worker}: {len(tasks)} مهمة في الانتظار")
        
    except Exception as e:
        print(f"❌ خطأ في فحص Celery: {str(e)}")

def main():
    print("🚀 بدء إصلاح المعاينات المعلقة")
    print("=" * 50)
    
    # فحص حالة Celery
    check_celery_status()
    print()
    
    # إصلاح المعاينات المعلقة
    try:
        success_count, error_count = fix_pending_inspections()
        
        if success_count > 0:
            print(f"\n🎉 تم جدولة {success_count} معاينة لإعادة الرفع")
            print("⏰ سيتم رفع الملفات تلقائياً في الخلفية")
            print("🔍 يمكنك مراقبة التقدم من خلال:")
            print("   tail -f /tmp/celery_worker.log")
        
    except Exception as e:
        print(f"❌ خطأ في تنفيذ الإصلاح: {str(e)}")
        sys.exit(1)
    
    print("\n✅ انتهى السكريبت")

if __name__ == "__main__":
    main()
