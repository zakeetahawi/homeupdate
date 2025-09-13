#!/usr/bin/env python3
"""
اختبار رفع معاينة حقيقية بملف موجود
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection

def find_real_inspection():
    """البحث عن معاينة بملف حقيقي"""
    print("🔍 البحث عن معاينة بملف حقيقي...")
    
    inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )[:20]  # أول 20 معاينة
    
    for inspection in inspections:
        if inspection.inspection_file:
            file_path = inspection.inspection_file.path
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ معاينة {inspection.id}: {file_path} ({file_size:,} bytes)")
                return inspection
            else:
                print(f"❌ معاينة {inspection.id}: ملف مفقود - {file_path}")
        else:
            print(f"❌ معاينة {inspection.id}: لا يوجد ملف")
    
    return None

def test_inspection_upload(inspection):
    """اختبار رفع معاينة محددة"""
    print(f"\n🧪 اختبار رفع المعاينة {inspection.id}...")
    
    try:
        print(f"📁 مسار الملف: {inspection.inspection_file.path}")
        print(f"📊 حجم الملف: {os.path.getsize(inspection.inspection_file.path):,} bytes")
        
        # اختبار الرفع
        result = inspection.upload_to_google_drive_async()
        
        if result:
            print(f"🎉 نجح رفع المعاينة {inspection.id}!")
            
            # التحقق من التحديث
            inspection.refresh_from_db()
            print(f"🔗 Google Drive ID: {inspection.google_drive_file_id}")
            print(f"🌐 URL: {inspection.google_drive_file_url}")
            
            return True
        else:
            print(f"❌ فشل رفع المعاينة {inspection.id}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في الرفع: {e}")
        import traceback
        traceback.print_exc()
        return False

def schedule_batch_upload():
    """جدولة رفع مجموعة من المعاينات"""
    print("\n📤 جدولة رفع مجموعة من المعاينات...")
    
    from orders.tasks import upload_inspection_to_drive_async
    
    # البحث عن 5 معاينات بملفات حقيقية
    real_inspections = []
    inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )[:50]  # فحص أول 50
    
    for inspection in inspections:
        if inspection.inspection_file and os.path.exists(inspection.inspection_file.path):
            real_inspections.append(inspection.id)
            if len(real_inspections) >= 5:
                break
    
    print(f"📋 وجدت {len(real_inspections)} معاينة بملفات حقيقية")
    
    # جدولة الرفع
    for inspection_id in real_inspections:
        try:
            upload_inspection_to_drive_async.delay(inspection_id)
            print(f"✅ تم جدولة المعاينة {inspection_id}")
        except Exception as e:
            print(f"❌ خطأ في جدولة المعاينة {inspection_id}: {e}")

def main():
    """الدالة الرئيسية"""
    print("🧪 اختبار رفع معاينة حقيقية")
    print("=" * 50)
    
    # البحث عن معاينة حقيقية
    inspection = find_real_inspection()
    
    if inspection:
        # اختبار الرفع
        success = test_inspection_upload(inspection)
        
        if success:
            print("\n🎉 الاختبار نجح! النظام يعمل بشكل صحيح")
            
            # جدولة المزيد
            schedule_batch_upload()
        else:
            print("\n❌ الاختبار فشل - يحتاج مراجعة")
    else:
        print("\n❌ لم أجد معاينات بملفات حقيقية")
    
    print("\n" + "=" * 50)
    print("🎯 انتهى الاختبار")

if __name__ == "__main__":
    main()
