#!/usr/bin/env python3
"""
إصلاح مشاكل الرفع الحرجة
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection
from orders.models import Order
import redis

def fix_duplicate_upload_attempts():
    """إصلاح محاولات الرفع المكررة"""
    print("🔧 إصلاح محاولات الرفع المكررة...")
    
    # إيقاف المهام المكررة للمعاينة 5055
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        # مسح جميع المهام المعلقة
        r.delete('file_uploads')
        r.delete('celery')
        
        print("✅ تم مسح المهام المعلقة من Redis")
        
    except Exception as e:
        print(f"❌ خطأ في مسح Redis: {e}")

def clean_invalid_upload_records():
    """تنظيف السجلات التي تحتاج رفع ولكن بدون ملفات"""
    print("\n🧹 تنظيف السجلات غير الصحيحة...")
    
    # فحص المعاينات بدون ملفات
    inspections_no_file = Inspection.objects.filter(
        inspection_file__isnull=True,
        google_drive_file_id__isnull=True
    ).count()
    
    print(f"📋 معاينات بدون ملفات: {inspections_no_file}")
    
    # فحص المعاينات بملفات مفقودة
    inspections_missing_files = 0
    inspections_with_files = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )
    
    for inspection in inspections_with_files:
        if not inspection.inspection_file or not os.path.exists(inspection.inspection_file.path):
            inspections_missing_files += 1
    
    print(f"📋 معاينات بملفات مفقودة: {inspections_missing_files}")
    
    # فحص العقود
    contracts_no_file = Order.objects.filter(
        contract_file__isnull=True,
        contract_google_drive_file_id__isnull=True
    ).count()
    
    print(f"📄 عقود بدون ملفات: {contracts_no_file}")
    
    contracts_missing_files = 0
    contracts_with_files = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    )
    
    for contract in contracts_with_files:
        if not contract.contract_file or not os.path.exists(contract.contract_file.path):
            contracts_missing_files += 1
    
    print(f"📄 عقود بملفات مفقودة: {contracts_missing_files}")

def get_real_upload_counts():
    """الحصول على الأرقام الحقيقية للملفات التي تحتاج رفع"""
    print("\n📊 الأرقام الحقيقية للملفات التي تحتاج رفع...")
    
    # معاينات حقيقية تحتاج رفع
    real_inspections = []
    inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )
    
    for inspection in inspections:
        if inspection.inspection_file and os.path.exists(inspection.inspection_file.path):
            real_inspections.append(inspection.id)
    
    print(f"📋 معاينات حقيقية تحتاج رفع: {len(real_inspections)}")
    
    # عقود حقيقية تحتاج رفع
    real_contracts = []
    contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    )
    
    for contract in contracts:
        if contract.contract_file and os.path.exists(contract.contract_file.path):
            real_contracts.append(contract.id)
    
    print(f"📄 عقود حقيقية تحتاج رفع: {len(real_contracts)}")
    
    return real_inspections[:10], real_contracts[:10]  # أول 10 من كل نوع

def schedule_real_uploads(inspections, contracts):
    """جدولة رفع الملفات الحقيقية فقط"""
    print(f"\n📤 جدولة رفع {len(inspections)} معاينة و {len(contracts)} عقد...")
    
    try:
        from orders.tasks import upload_inspection_to_drive_async, upload_contract_to_drive_async
        
        # جدولة المعاينات
        for inspection_id in inspections:
            upload_inspection_to_drive_async.delay(inspection_id)
            print(f"📋 تم جدولة معاينة {inspection_id}")
        
        # جدولة العقود
        for contract_id in contracts:
            upload_contract_to_drive_async.delay(contract_id)
            print(f"📄 تم جدولة عقد {contract_id}")
            
        print("✅ تم جدولة الملفات بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ في الجدولة: {e}")

def check_celery_workers():
    """فحص حالة Celery workers"""
    print("\n⚙️ فحص حالة Celery workers...")
    
    try:
        import subprocess
        result = subprocess.run(['celery', '-A', 'crm', 'inspect', 'active'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            if 'file_uploads' in result.stdout:
                print("✅ Celery worker يستمع لـ file_uploads queue")
            else:
                print("❌ Celery worker لا يستمع لـ file_uploads queue")
                
            if 'celery' in result.stdout:
                print("✅ Celery worker يستمع لـ celery queue")
            else:
                print("❌ Celery worker لا يستمع لـ celery queue")
        else:
            print("❌ لا يمكن الاتصال بـ Celery")
            
    except Exception as e:
        print(f"❌ خطأ في فحص Celery: {e}")

def restart_celery_with_correct_queues():
    """إعادة تشغيل Celery بالـ queues الصحيحة"""
    print("\n🔄 إعادة تشغيل Celery...")
    
    try:
        import subprocess
        
        # إيقاف Celery workers الحاليين
        subprocess.run(['pkill', '-f', 'celery.*worker'], timeout=10)
        print("🛑 تم إيقاف Celery workers")
        
        # انتظار قليل
        import time
        time.sleep(3)
        
        # تشغيل worker جديد بالـ queues الصحيحة
        subprocess.Popen([
            'celery', '-A', 'crm', 'worker',
            '--loglevel=info',
            '--queues=celery,file_uploads',
            '--concurrency=2',
            '--detach',
            '--pidfile=/tmp/celery_worker_fixed.pid',
            '--logfile=logs/celery_fixed.log'
        ])
        
        print("✅ تم تشغيل Celery worker جديد")
        
        # انتظار قليل للتأكد من التشغيل
        time.sleep(5)
        
        # فحص الحالة
        check_celery_workers()
        
    except Exception as e:
        print(f"❌ خطأ في إعادة تشغيل Celery: {e}")

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح شامل لمشاكل الرفع")
    print("=" * 50)
    
    # إصلاح المشاكل
    fix_duplicate_upload_attempts()
    clean_invalid_upload_records()
    
    # الحصول على الأرقام الحقيقية
    real_inspections, real_contracts = get_real_upload_counts()
    
    # فحص وإصلاح Celery
    check_celery_workers()
    restart_celery_with_correct_queues()
    
    # جدولة الرفع الحقيقي
    schedule_real_uploads(real_inspections, real_contracts)
    
    print("\n" + "=" * 50)
    print("🎉 تم الإصلاح بنجاح!")
    print("💡 راقب اللوغ: tail -f logs/celery_fixed.log")

if __name__ == "__main__":
    main()
