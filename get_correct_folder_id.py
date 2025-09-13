#!/usr/bin/env python3
"""
الحصول على المعرف الصحيح للمجلد
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def find_inspections_folder():
    """البحث عن مجلد المعاينات الصحيح"""
    print("🔍 البحث عن مجلد المعاينات الصحيح...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن مجلد بالاسم "المعاينات - Inspections"
        query = "name='المعاينات - Inspections' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = service.service.files().list(
            q=query,
            fields='files(id,name,webViewLink)',
            pageSize=10
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            for folder in folders:
                folder_id = folder.get('id')
                folder_name = folder.get('name')
                folder_link = folder.get('webViewLink')
                
                print(f"📁 وجد مجلد: {folder_name}")
                print(f"   🆔 المعرف: {folder_id}")
                print(f"   🔗 الرابط: {folder_link}")
                
                # عد الملفات في هذا المجلد
                file_results = service.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields='files(id,name)',
                    pageSize=1000
                ).execute()
                
                files = file_results.get('files', [])
                print(f"   📊 عدد الملفات: {len(files)}")
                
                # فحص نوع الملفات
                inspection_count = 0
                contract_count = 0
                
                for file in files:
                    file_name = file.get('name', '')
                    if 'عقد' in file_name or 'contract' in file_name.lower():
                        contract_count += 1
                    else:
                        inspection_count += 1
                
                print(f"   📁 ملفات معاينات: {inspection_count}")
                print(f"   📄 ملفات عقود: {contract_count}")
                
                if inspection_count > contract_count:
                    print(f"✅ هذا هو مجلد المعاينات الصحيح!")
                    return folder_id
        
        print("❌ لم يتم العثور على مجلد المعاينات")
        return None
        
    except Exception as e:
        print(f"❌ خطأ في البحث: {e}")
        return None

def find_contracts_folder():
    """البحث عن مجلد العقود الصحيح"""
    print("\n🔍 البحث عن مجلد العقود الصحيح...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن مجلد بالاسم "العقود - Contracts"
        query = "name='العقود - Contracts' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = service.service.files().list(
            q=query,
            fields='files(id,name,webViewLink)',
            pageSize=10
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            for folder in folders:
                folder_id = folder.get('id')
                folder_name = folder.get('name')
                folder_link = folder.get('webViewLink')
                
                print(f"📄 وجد مجلد: {folder_name}")
                print(f"   🆔 المعرف: {folder_id}")
                print(f"   🔗 الرابط: {folder_link}")
                
                # عد الملفات في هذا المجلد
                file_results = service.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields='files(id,name)',
                    pageSize=1000
                ).execute()
                
                files = file_results.get('files', [])
                print(f"   📊 عدد الملفات: {len(files)}")
                
                # فحص نوع الملفات
                contract_count = 0
                
                for file in files:
                    file_name = file.get('name', '')
                    if 'عقد' in file_name or 'contract' in file_name.lower():
                        contract_count += 1
                
                print(f"   📄 ملفات عقود: {contract_count}")
                
                if contract_count > 0:
                    print(f"✅ هذا هو مجلد العقود الصحيح!")
                    return folder_id
        
        print("❌ لم يتم العثور على مجلد العقود")
        return None
        
    except Exception as e:
        print(f"❌ خطأ في البحث: {e}")
        return None

def update_config(inspections_folder_id, contracts_folder_id):
    """تحديث الإعدادات بالمعرفات الصحيحة"""
    print(f"\n🔧 تحديث الإعدادات...")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات للتحديث")
            return False
        
        old_inspections = config.inspections_folder_id
        old_contracts = config.contracts_folder_id
        
        config.inspections_folder_id = inspections_folder_id
        config.contracts_folder_id = contracts_folder_id
        config.save()
        
        print(f"✅ تم تحديث الإعدادات:")
        print(f"   📁 المعاينات: {old_inspections} → {inspections_folder_id}")
        print(f"   📄 العقود: {old_contracts} → {contracts_folder_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث الإعدادات: {e}")
        return False

def test_final_config():
    """اختبار الإعدادات النهائية"""
    print(f"\n🧪 اختبار الإعدادات النهائية...")
    
    try:
        # اختبار رفع المعاينات
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار رفع المعاينات")
            print(f"   📁 المجلد: {result.get('folder_id')}")
        else:
            print(f"❌ فشل اختبار رفع المعاينات: {result.get('message')}")
            return False
        
        # اختبار رفع العقود
        from orders.services.google_drive_service import test_contract_file_upload_to_folder
        
        result = test_contract_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار رفع العقود")
            print(f"   📁 المجلد: {result.get('folder_id')}")
        else:
            print(f"❌ فشل اختبار رفع العقود: {result.get('message')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الإعدادات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔍 الحصول على المعرفات الصحيحة للمجلدات")
    print("=" * 60)
    
    # البحث عن مجلد المعاينات
    inspections_folder_id = find_inspections_folder()
    if not inspections_folder_id:
        print("❌ لم يتم العثور على مجلد المعاينات")
        return
    
    # البحث عن مجلد العقود
    contracts_folder_id = find_contracts_folder()
    if not contracts_folder_id:
        print("❌ لم يتم العثور على مجلد العقود")
        return
    
    # تحديث الإعدادات
    if not update_config(inspections_folder_id, contracts_folder_id):
        return
    
    # اختبار الإعدادات النهائية
    if not test_final_config():
        return
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح الإعدادات بنجاح!")
    print("✅ النظام يستخدم الآن المجلدات الصحيحة")
    
    print(f"\n🔗 المجلدات الصحيحة:")
    print(f"📁 المعاينات: https://drive.google.com/drive/folders/{inspections_folder_id}")
    print(f"📄 العقود: https://drive.google.com/drive/folders/{contracts_folder_id}")

if __name__ == "__main__":
    main()
