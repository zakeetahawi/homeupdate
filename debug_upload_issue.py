#!/usr/bin/env python3
"""
تشخيص مشاكل الرفع بالتفصيل
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection
from orders.models import Order

def check_inspection_5055():
    """فحص المعاينة 5055 التي فشلت في الرفع"""
    print("🔍 فحص المعاينة 5055...")
    
    try:
        inspection = Inspection.objects.get(id=5055)
        print(f"✅ المعاينة موجودة: {inspection}")
        print(f"📄 ملف المعاينة: {inspection.inspection_file}")
        
        if inspection.inspection_file:
            file_path = inspection.inspection_file.path
            print(f"📁 مسار الملف: {file_path}")
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ الملف موجود - الحجم: {file_size:,} bytes")
            else:
                print(f"❌ الملف غير موجود في المسار: {file_path}")
        else:
            print("❌ لا يوجد ملف مرفق بالمعاينة")
            
        print(f"🔗 Google Drive ID: {inspection.google_drive_file_id}")
        
    except Inspection.DoesNotExist:
        print("❌ المعاينة 5055 غير موجودة")
    except Exception as e:
        print(f"❌ خطأ في فحص المعاينة: {e}")

def check_google_drive_config():
    """فحص إعدادات Google Drive"""
    print("\n🔧 فحص إعدادات Google Drive...")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        config = GoogleDriveConfig.objects.first()
        
        if config:
            print(f"✅ إعدادات Google Drive موجودة")
            print(f"📁 مجلد المعاينات: {config.inspections_folder_id}")
            print(f"📁 مجلد العقود: {config.contracts_folder_id}")
        else:
            print("❌ لا توجد إعدادات Google Drive")
            
    except Exception as e:
        print(f"❌ خطأ في فحص إعدادات Google Drive: {e}")

def check_celery_queues():
    """فحص حالة Celery queues"""
    print("\n⚙️ فحص حالة Celery...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        # فحص المهام في queue
        file_uploads_tasks = r.llen('file_uploads')
        celery_tasks = r.llen('celery')
        
        print(f"📤 مهام file_uploads: {file_uploads_tasks}")
        print(f"⚙️ مهام celery: {celery_tasks}")
        
        # فحص المهام الفاشلة
        failed_tasks = r.llen('_kombu.binding.celery.pidbox')
        print(f"❌ مهام فاشلة: {failed_tasks}")
        
    except Exception as e:
        print(f"❌ خطأ في فحص Celery: {e}")

def check_recent_upload_attempts():
    """فحص محاولات الرفع الأخيرة"""
    print("\n📊 فحص محاولات الرفع الأخيرة...")
    
    # فحص المعاينات بدون Google Drive ID
    inspections_without_drive = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    ).count()
    
    print(f"📋 معاينات بحاجة للرفع: {inspections_without_drive}")
    
    # فحص العقود بدون Google Drive ID
    contracts_without_drive = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    ).count()
    
    print(f"📄 عقود بحاجة للرفع: {contracts_without_drive}")
    
    # عرض أول 5 معاينات تحتاج رفع
    print("\n📋 أول 5 معاينات تحتاج رفع:")
    inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )[:5]
    
    for inspection in inspections:
        file_exists = "✅" if inspection.inspection_file and os.path.exists(inspection.inspection_file.path) else "❌"
        print(f"  {file_exists} معاينة {inspection.id}: {inspection.inspection_file}")

def test_google_drive_connection():
    """اختبار الاتصال بـ Google Drive"""
    print("\n🌐 اختبار الاتصال بـ Google Drive...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        print("✅ تم إنشاء خدمة Google Drive بنجاح")
        
        # محاولة الحصول على معلومات المجلد
        from odoo_db_manager.models import GoogleDriveConfig
        config = GoogleDriveConfig.objects.first()
        
        if config and config.inspections_folder_id:
            try:
                folder_info = service.drive_service.files().get(
                    fileId=config.inspections_folder_id
                ).execute()
                print(f"✅ مجلد المعاينات متاح: {folder_info.get('name')}")
            except Exception as e:
                print(f"❌ مشكلة في مجلد المعاينات: {e}")
        
    except Exception as e:
        print(f"❌ خطأ في الاتصال بـ Google Drive: {e}")

def main():
    """الدالة الرئيسية"""
    print("🔍 تشخيص شامل لمشاكل الرفع")
    print("=" * 50)
    
    check_inspection_5055()
    check_google_drive_config()
    check_celery_queues()
    check_recent_upload_attempts()
    test_google_drive_connection()
    
    print("\n" + "=" * 50)
    print("🎯 تم الانتهاء من التشخيص")

if __name__ == "__main__":
    main()
