#!/usr/bin/env python3
"""
اختبار إصلاح رفع المعاينات
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection
from orders.tasks import upload_inspection_to_drive_async

def test_single_inspection_upload():
    """اختبار رفع معاينة واحدة"""
    print("🧪 اختبار رفع معاينة واحدة...")
    
    # البحث عن معاينة تحتاج رفع
    inspection = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    ).first()
    
    if not inspection:
        print("❌ لا توجد معاينات تحتاج رفع")
        return
    
    print(f"📋 اختبار المعاينة {inspection.id}")
    
    # التحقق من وجود الملف
    if not inspection.inspection_file or not os.path.exists(inspection.inspection_file.path):
        print(f"❌ الملف غير موجود: {inspection.inspection_file}")
        return
    
    print(f"✅ الملف موجود: {inspection.inspection_file.path}")
    
    # اختبار الرفع مباشرة
    try:
        result = inspection.upload_to_google_drive_async()
        if result:
            print(f"✅ تم رفع المعاينة {inspection.id} بنجاح!")
            
            # التحقق من التحديث في قاعدة البيانات
            inspection.refresh_from_db()
            print(f"🔗 Google Drive ID: {inspection.google_drive_file_id}")
            print(f"🌐 URL: {inspection.google_drive_file_url}")
        else:
            print(f"❌ فشل في رفع المعاينة {inspection.id}")
            
    except Exception as e:
        print(f"❌ خطأ في الرفع: {e}")

def test_google_drive_service():
    """اختبار خدمة Google Drive مباشرة"""
    print("\n🔧 اختبار خدمة Google Drive...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        if service.service:
            print("✅ تم إنشاء خدمة Google Drive بنجاح")
            
            # اختبار الاتصال
            test_result = service.test_connection()
            if test_result.get('success'):
                print("✅ اختبار الاتصال نجح")
            else:
                print(f"❌ فشل اختبار الاتصال: {test_result.get('message')}")
        else:
            print("❌ فشل في إنشاء خدمة Google Drive")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الخدمة: {e}")

def test_celery_task():
    """اختبار مهمة Celery"""
    print("\n⚙️ اختبار مهمة Celery...")
    
    # البحث عن معاينة تحتاج رفع
    inspection = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    ).first()
    
    if not inspection:
        print("❌ لا توجد معاينات تحتاج رفع")
        return
    
    print(f"📋 جدولة المعاينة {inspection.id} عبر Celery...")
    
    try:
        # جدولة المهمة
        result = upload_inspection_to_drive_async.delay(inspection.id)
        print(f"✅ تم جدولة المهمة: {result.id}")
        
        # انتظار النتيجة (مع timeout)
        try:
            task_result = result.get(timeout=30)
            print(f"📊 نتيجة المهمة: {task_result}")
        except Exception as e:
            print(f"⏰ انتهت مهلة انتظار المهمة: {e}")
            
    except Exception as e:
        print(f"❌ خطأ في جدولة المهمة: {e}")

def show_upload_statistics():
    """عرض إحصائيات الرفع"""
    print("\n📊 إحصائيات الرفع:")
    print("-" * 40)
    
    # المعاينات
    total_inspections = Inspection.objects.filter(inspection_file__isnull=False).count()
    uploaded_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=False
    ).count()
    pending_inspections = total_inspections - uploaded_inspections
    
    print(f"📋 المعاينات:")
    print(f"  📁 المجموع: {total_inspections}")
    print(f"  ✅ مرفوعة: {uploaded_inspections}")
    print(f"  ⏳ معلقة: {pending_inspections}")
    
    # العقود
    from orders.models import Order
    total_contracts = Order.objects.filter(contract_file__isnull=False).count()
    uploaded_contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=False
    ).count()
    pending_contracts = total_contracts - uploaded_contracts
    
    print(f"📄 العقود:")
    print(f"  📁 المجموع: {total_contracts}")
    print(f"  ✅ مرفوعة: {uploaded_contracts}")
    print(f"  ⏳ معلقة: {pending_contracts}")

def main():
    """الدالة الرئيسية"""
    print("🧪 اختبار إصلاح رفع المعاينات")
    print("=" * 50)
    
    # عرض الإحصائيات
    show_upload_statistics()
    
    # اختبار خدمة Google Drive
    test_google_drive_service()
    
    # اختبار الرفع المباشر
    test_single_inspection_upload()
    
    # اختبار مهمة Celery
    test_celery_task()
    
    print("\n" + "=" * 50)
    print("🎯 انتهى الاختبار")

if __name__ == "__main__":
    main()
