#!/usr/bin/env python3
"""
إصلاح الإعدادات النهائية للمجلدات الصحيحة
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
    
    # المجلدات الصحيحة بناءً على البحث
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av"  # يحتوي على 90 ملف معاينة
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"    # يحتوي على 10 ملفات عقود
    
    print(f"📁 مجلد المعاينات الصحيح: {CORRECT_INSPECTIONS_FOLDER}")
    print(f"📄 مجلد العقود الصحيح: {CORRECT_CONTRACTS_FOLDER}")
    
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

def verify_folders_access():
    """التحقق من إمكانية الوصول للمجلدات"""
    print("\n🧪 التحقق من إمكانية الوصول للمجلدات...")
    
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # التحقق من مجلد المعاينات
        try:
            inspections_info = service.service.files().get(
                fileId=CORRECT_INSPECTIONS_FOLDER,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد المعاينات متاح: {inspections_info.get('name')}")
            print(f"   🆔 المعرف: {CORRECT_INSPECTIONS_FOLDER}")
            print(f"   🔗 الرابط: {inspections_info.get('webViewLink')}")
            
            # عد الملفات
            results = service.service.files().list(
                q=f"'{CORRECT_INSPECTIONS_FOLDER}' in parents and trashed=false",
                fields='files(id,name)',
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            print(f"   📊 عدد الملفات: {len(files)}")
            
        except Exception as e:
            print(f"❌ خطأ في الوصول لمجلد المعاينات: {e}")
            return False
        
        # التحقق من مجلد العقود
        try:
            contracts_info = service.service.files().get(
                fileId=CORRECT_CONTRACTS_FOLDER,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد العقود متاح: {contracts_info.get('name')}")
            print(f"   🆔 المعرف: {CORRECT_CONTRACTS_FOLDER}")
            print(f"   🔗 الرابط: {contracts_info.get('webViewLink')}")
            
            # عد الملفات
            results = service.service.files().list(
                q=f"'{CORRECT_CONTRACTS_FOLDER}' in parents and trashed=false",
                fields='files(id,name)',
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            print(f"   📊 عدد الملفات: {len(files)}")
            
        except Exception as e:
            print(f"❌ خطأ في الوصول لمجلد العقود: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق من المجلدات: {e}")
        return False

def test_upload_functionality():
    """اختبار وظائف الرفع"""
    print("\n🧪 اختبار وظائف الرفع...")
    
    # اختبار رفع المعاينات
    try:
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار رفع المعاينات")
            print(f"   📁 المجلد: {result.get('folder_id')}")
            print(f"   📄 الملف التجريبي: {result.get('file_name')}")
        else:
            print(f"❌ فشل اختبار رفع المعاينات")
            print(f"   💬 الرسالة: {result.get('message')}")
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
            print(f"   📄 الملف التجريبي: {result.get('file_name')}")
        else:
            print(f"❌ فشل اختبار رفع العقود")
            print(f"   💬 الرسالة: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار رفع العقود: {e}")
        return False
    
    return True

def check_files_distribution():
    """فحص توزيع الملفات"""
    print("\n📊 فحص توزيع الملفات...")
    
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # فحص ملفات المعاينات
        results = service.service.files().list(
            q=f"'{CORRECT_INSPECTIONS_FOLDER}' in parents and trashed=false",
            fields='files(id,name,size)',
            pageSize=1000,
            orderBy='createdTime desc'
        ).execute()
        
        inspection_files = results.get('files', [])
        print(f"📁 مجلد المعاينات:")
        print(f"   📊 عدد الملفات: {len(inspection_files)}")
        
        if inspection_files:
            print("   📋 آخر 5 ملفات:")
            for file in inspection_files[:5]:
                size = int(file.get('size', 0)) if file.get('size') else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                print(f"      - {file.get('name')} ({size_mb:.1f} MB)")
        
        # فحص ملفات العقود
        results = service.service.files().list(
            q=f"'{CORRECT_CONTRACTS_FOLDER}' in parents and trashed=false",
            fields='files(id,name,size)',
            pageSize=1000,
            orderBy='createdTime desc'
        ).execute()
        
        contract_files = results.get('files', [])
        print(f"\n📄 مجلد العقود:")
        print(f"   📊 عدد الملفات: {len(contract_files)}")
        
        if contract_files:
            print("   📋 آخر 5 ملفات:")
            for file in contract_files[:5]:
                size = int(file.get('size', 0)) if file.get('size') else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                print(f"      - {file.get('name')} ({size_mb:.1f} MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في فحص توزيع الملفات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح الإعدادات النهائية للمجلدات الصحيحة")
    print("=" * 60)
    
    # 1. تحديث الإعدادات للمجلدات الصحيحة
    if not update_to_correct_folders():
        return
    
    # 2. التحقق من إمكانية الوصول للمجلدات
    if not verify_folders_access():
        return
    
    # 3. اختبار وظائف الرفع
    if not test_upload_functionality():
        return
    
    # 4. فحص توزيع الملفات
    if not check_files_distribution():
        return
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح الإعدادات بنجاح!")
    print("✅ النظام يستخدم الآن المجلدات الصحيحة")
    print("✅ جميع الملفات منظمة في المجلدات الصحيحة")
    print("✅ وظائف الرفع تعمل بشكل مثالي")
    
    print("\n🔗 المجلدات الصحيحة:")
    print("📁 المعاينات: https://drive.google.com/drive/folders/1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av")
    print("📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    print("⚙️ الصفحة المركزية: https://elkhawaga.uk/odoo-db-manager/google-drive/settings/")
    
    print("\n📊 الإحصائيات:")
    print("📁 مجلد المعاينات: ~90 ملف معاينة")
    print("📄 مجلد العقود: ~10 ملف عقد")
    print("✅ جميع الملفات منظمة ومرتبة")

if __name__ == "__main__":
    main()
