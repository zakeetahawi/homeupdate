#!/usr/bin/env python3
"""
إصلاح الإعدادات بالمعرف الصحيح
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def update_to_correct_folders():
    """تحديث الإعدادات للمجلدات الصحيحة"""
    print("🔧 تحديث الإعدادات للمجلدات الصحيحة...")
    
    # المجلدات الصحيحة - نسخ مباشر من النتائج
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    print(f"📁 مجلد المعاينات: {CORRECT_INSPECTIONS_FOLDER}")
    print(f"📄 مجلد العقود: {CORRECT_CONTRACTS_FOLDER}")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات للتحديث")
            return False
        
        old_inspections = config.inspections_folder_id
        old_contracts = config.contracts_folder_id
        
        config.inspections_folder_id = CORRECT_INSPECTIONS_FOLDER
        config.contracts_folder_id = CORRECT_CONTRACTS_FOLDER
        config.save()
        
        print(f"✅ تم تحديث الإعدادات:")
        print(f"   📁 المعاينات: {old_inspections} → {CORRECT_INSPECTIONS_FOLDER}")
        print(f"   📄 العقود: {old_contracts} → {CORRECT_CONTRACTS_FOLDER}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث الإعدادات: {e}")
        return False

def test_access():
    """اختبار الوصول للمجلدات"""
    print("\n🧪 اختبار الوصول للمجلدات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        config = service.config
        
        print(f"📁 مجلد المعاينات في الإعدادات: {config.inspections_folder_id}")
        print(f"📄 مجلد العقود في الإعدادات: {config.contracts_folder_id}")
        
        # اختبار مجلد المعاينات
        try:
            inspections_info = service.service.files().get(
                fileId=config.inspections_folder_id,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد المعاينات متاح: {inspections_info.get('name')}")
            print(f"   🔗 الرابط: {inspections_info.get('webViewLink')}")
            
        except Exception as e:
            print(f"❌ خطأ في مجلد المعاينات: {e}")
            return False
        
        # اختبار مجلد العقود
        try:
            contracts_info = service.service.files().get(
                fileId=config.contracts_folder_id,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد العقود متاح: {contracts_info.get('name')}")
            print(f"   🔗 الرابط: {contracts_info.get('webViewLink')}")
            
        except Exception as e:
            print(f"❌ خطأ في مجلد العقود: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الوصول: {e}")
        return False

def count_files():
    """عد الملفات في المجلدات"""
    print("\n📊 عد الملفات في المجلدات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        config = service.config
        
        # عد ملفات المعاينات
        results = service.service.files().list(
            q=f"'{config.inspections_folder_id}' in parents and trashed=false",
            fields='files(id,name)',
            pageSize=1000
        ).execute()
        
        inspection_files = results.get('files', [])
        print(f"📁 مجلد المعاينات: {len(inspection_files)} ملف")
        
        # عد ملفات العقود
        results = service.service.files().list(
            q=f"'{config.contracts_folder_id}' in parents and trashed=false",
            fields='files(id,name)',
            pageSize=1000
        ).execute()
        
        contract_files = results.get('files', [])
        print(f"📄 مجلد العقود: {len(contract_files)} ملف")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في عد الملفات: {e}")
        return False

def test_upload():
    """اختبار الرفع"""
    print("\n🧪 اختبار الرفع...")
    
    # اختبار رفع المعاينات
    try:
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار رفع المعاينات")
            print(f"   📁 المجلد: {result.get('folder_id')}")
        else:
            print(f"❌ فشل اختبار رفع المعاينات: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار رفع المعاينات: {e}")
        return False
    
    # اختبار رفع العقود
    try:
        from orders.services.google_drive_service import test_contract_file_upload_to_folder
        
        result = test_contract_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار رفع العقود")
            print(f"   📁 المجلد: {result.get('folder_id')}")
        else:
            print(f"❌ فشل اختبار رفع العقود: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار رفع العقود: {e}")
        return False
    
    return True

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح الإعدادات بالمعرف الصحيح")
    print("=" * 60)
    
    # 1. تحديث الإعدادات
    if not update_to_correct_folders():
        return
    
    # 2. اختبار الوصول
    if not test_access():
        return
    
    # 3. عد الملفات
    if not count_files():
        return
    
    # 4. اختبار الرفع
    if not test_upload():
        return
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح الإعدادات بنجاح!")
    print("✅ النظام يستخدم الآن المجلدات الصحيحة")
    print("✅ جميع الاختبارات نجحت")
    
    print("\n🔗 المجلدات الصحيحة:")
    print("📁 المعاينات: https://drive.google.com/drive/folders/1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av")
    print("📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")

if __name__ == "__main__":
    main()
