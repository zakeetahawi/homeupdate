#!/usr/bin/env python3
"""
رفع المعاينة 5059 إلى Google Drive
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection
from orders.tasks import upload_inspection_to_drive_async

def upload_inspection_5059():
    """رفع المعاينة 5059"""
    print("📤 رفع المعاينة 5059 إلى Google Drive...")
    
    try:
        inspection = Inspection.objects.get(id=5059)
        
        if inspection.google_drive_file_id:
            print("✅ المعاينة مرفوعة بالفعل")
            return
            
        if not inspection.inspection_file:
            print("❌ لا يوجد ملف للرفع")
            return
            
        if not os.path.exists(inspection.inspection_file.path):
            print("❌ الملف غير موجود")
            return
            
        # جدولة رفع الملف
        print("🚀 جدولة رفع الملف...")
        task = upload_inspection_to_drive_async.delay(inspection.id)
        print(f"✅ تم جدولة المهمة: {task.id}")
        
        # انتظار قليل ثم فحص النتيجة
        import time
        time.sleep(5)
        
        # إعادة تحميل المعاينة للتحقق من النتيجة
        inspection.refresh_from_db()
        if inspection.google_drive_file_id:
            print(f"🎉 تم رفع الملف بنجاح! Google Drive ID: {inspection.google_drive_file_id}")
        else:
            print("⏳ الرفع قيد التنفيذ...")
            
    except Inspection.DoesNotExist:
        print("❌ المعاينة 5059 غير موجودة")
    except Exception as e:
        print(f"❌ خطأ في رفع المعاينة: {e}")

if __name__ == "__main__":
    upload_inspection_5059()
