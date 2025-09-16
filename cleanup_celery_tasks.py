#!/usr/bin/env python3
"""
سكريبت تنظيف مهام Celery المعلقة والمكررة
"""

import os
import sys
import django
import subprocess
from datetime import datetime, timedelta

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import transaction
from orders.models import Order
from inspections.models import Inspection
from orders.tasks import upload_contract_to_drive_async, upload_inspection_to_drive_async

def clear_celery_queue():
    """مسح طابور Celery"""
    try:
        print("🧹 مسح طابور Celery...")
        result = subprocess.run(['celery', '-A', 'crm', 'purge', '-f'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ تم مسح طابور Celery بنجاح")
            return True
        else:
            print(f"❌ فشل في مسح طابور Celery: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في مسح طابور Celery: {e}")
        return False

def restart_celery_worker():
    """إعادة تشغيل عامل Celery"""
    try:
        print("🔄 إعادة تشغيل عامل Celery...")
        
        # إيقاف العامل الحالي
        subprocess.run(['pkill', '-f', 'celery.*worker'], timeout=10)
        
        # انتظار قليل
        import time
        time.sleep(3)
        
        # تشغيل عامل جديد
        cmd = [
            'celery', '-A', 'crm', 'worker',
            '--loglevel=info',
            '-n', 'worker1@%h',
            '--concurrency=2',
            '--max-tasks-per-child=50',
            '--pidfile=/tmp/celery_worker_optimized.pid',
            '--logfile=logs/celery_optimized.log',
            '--detach'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ تم إعادة تشغيل عامل Celery بنجاح")
            return True
        else:
            print(f"❌ فشل في إعادة تشغيل عامل Celery: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في إعادة تشغيل عامل Celery: {e}")
        return False

def reschedule_failed_uploads():
    """إعادة جدولة رفع الملفات الفاشلة"""
    print("📤 إعادة جدولة رفع الملفات الفاشلة...")
    
    # العثور على الطلبات التي لديها ملفات ولم يتم رفعها
    failed_contracts = Order.objects.filter(
        contract_file__isnull=False,
        is_contract_uploaded_to_drive=False
    ).exclude(contract_file='')[:50]  # أول 50 فقط لتجنب الحمل الزائد
    
    failed_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        is_uploaded_to_drive=False
    ).exclude(inspection_file='')[:50]  # أول 50 فقط
    
    contract_count = 0
    inspection_count = 0
    
    # إعادة جدولة ملفات العقود
    for order in failed_contracts:
        try:
            if order.contract_file and hasattr(order.contract_file, 'path'):
                from pathlib import Path
                if Path(order.contract_file.path).exists():
                    upload_contract_to_drive_async.delay(order.pk)
                    contract_count += 1
                    print(f"✅ تم جدولة رفع ملف العقد للطلب {order.order_number}")
        except Exception as e:
            print(f"❌ خطأ في جدولة الطلب {order.order_number}: {e}")
    
    # إعادة جدولة ملفات المعاينات
    for inspection in failed_inspections:
        try:
            if inspection.inspection_file and hasattr(inspection.inspection_file, 'path'):
                from pathlib import Path
                if Path(inspection.inspection_file.path).exists():
                    upload_inspection_to_drive_async.delay(inspection.pk)
                    inspection_count += 1
                    print(f"✅ تم جدولة رفع ملف المعاينة {inspection.pk}")
        except Exception as e:
            print(f"❌ خطأ في جدولة المعاينة {inspection.pk}: {e}")
    
    print(f"\n📊 النتائج:")
    print(f"   - ملفات عقود مجدولة: {contract_count}")
    print(f"   - ملفات معاينات مجدولة: {inspection_count}")
    print(f"   - إجمالي المجدولة: {contract_count + inspection_count}")
    
    return contract_count + inspection_count

def check_celery_status():
    """فحص حالة Celery"""
    try:
        result = subprocess.run(['celery', '-A', 'crm', 'inspect', 'active'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            active_tasks = result.stdout.count('uuid')
            workers_online = 1 if 'worker1@' in result.stdout else 0
            
            print(f"📊 حالة Celery:")
            print(f"   - العمال النشطين: {workers_online}")
            print(f"   - المهام النشطة: {active_tasks}")
            
            return workers_online > 0
        else:
            print("❌ Celery غير متاح")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في فحص حالة Celery: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء تنظيف وتحسين مهام Celery")
    print("=" * 50)
    
    # 1. فحص الحالة الحالية
    print("\n1️⃣ فحص الحالة الحالية...")
    celery_running = check_celery_status()
    
    # 2. مسح الطابور إذا لزم الأمر
    if celery_running:
        print("\n2️⃣ مسح طابور Celery...")
        clear_celery_queue()
    
    # 3. إعادة تشغيل العامل
    print("\n3️⃣ إعادة تشغيل عامل Celery...")
    if restart_celery_worker():
        # انتظار قليل للتأكد من بدء التشغيل
        import time
        time.sleep(5)
        
        # 4. فحص الحالة بعد إعادة التشغيل
        print("\n4️⃣ فحص الحالة بعد إعادة التشغيل...")
        if check_celery_status():
            # 5. إعادة جدولة المهام الفاشلة
            print("\n5️⃣ إعادة جدولة المهام الفاشلة...")
            rescheduled = reschedule_failed_uploads()
            
            print(f"\n✅ تم التنظيف بنجاح!")
            print(f"   - تم إعادة جدولة {rescheduled} مهمة")
            print(f"   - يمكنك مراقبة التقدم في logs/celery_optimized.log")
        else:
            print("\n❌ فشل في تشغيل Celery بعد إعادة التشغيل")
    else:
        print("\n❌ فشل في إعادة تشغيل عامل Celery")

if __name__ == "__main__":
    main()
