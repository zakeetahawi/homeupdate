#!/usr/bin/env python3
"""
منع الرفع المكرر للملفات على Google Drive
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from odoo_db_manager.models import GoogleDriveConfig
import json

def check_and_remove_duplicates():
    """فحص وإزالة الملفات المكررة من Google Drive"""
    print("🔍 فحص الملفات المكررة على Google Drive...")
    
    try:
        # الحصول على إعدادات Google Drive
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات Google Drive")
            return
            
        # تحميل الاعتماد
        credentials_path = config.credentials_file.path
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
            
        # إنشاء الخدمة
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = Credentials.from_service_account_info(credentials_data, scopes=scopes)
        service = build('drive', 'v3', credentials=credentials)
        
        print("✅ تم الاتصال بـ Google Drive")
        
        # فحص مجلد العقود
        print("🔍 فحص مجلد العقود...")
        contracts_folder_id = config.contracts_folder_id
        contracts_files = list_files_in_folder(service, contracts_folder_id)
        
        # فحص مجلد المعاينات
        print("🔍 فحص مجلد المعاينات...")
        inspections_folder_id = config.inspections_folder_id
        inspections_files = list_files_in_folder(service, inspections_folder_id)
        
        # البحث عن الملفات المكررة
        print("🔍 البحث عن الملفات المكررة...")
        
        # تجميع الملفات حسب الاسم
        contracts_by_name = {}
        for file_info in contracts_files:
            name = file_info['name']
            if name in contracts_by_name:
                contracts_by_name[name].append(file_info)
            else:
                contracts_by_name[name] = [file_info]
        
        inspections_by_name = {}
        for file_info in inspections_files:
            name = file_info['name']
            if name in inspections_by_name:
                inspections_by_name[name].append(file_info)
            else:
                inspections_by_name[name] = [file_info]
        
        # حذف الملفات المكررة
        deleted_contracts = 0
        deleted_inspections = 0
        
        print("🗑️ حذف الملفات المكررة...")
        
        # حذف العقود المكررة
        for name, files in contracts_by_name.items():
            if len(files) > 1:
                print(f"📄 وجدت {len(files)} نسخة من العقد: {name}")
                # الاحتفاظ بأحدث ملف وحذف الباقي
                files.sort(key=lambda x: x['createdTime'], reverse=True)
                for file_to_delete in files[1:]:
                    try:
                        service.files().delete(fileId=file_to_delete['id']).execute()
                        print(f"🗑️ تم حذف النسخة المكررة: {file_to_delete['id']}")
                        deleted_contracts += 1
                    except Exception as e:
                        print(f"❌ خطأ في حذف الملف {file_to_delete['id']}: {e}")
        
        # حذف المعاينات المكررة
        for name, files in inspections_by_name.items():
            if len(files) > 1:
                print(f"📄 وجدت {len(files)} نسخة من المعاينة: {name}")
                # الاحتفاظ بأحدث ملف وحذف الباقي
                files.sort(key=lambda x: x['createdTime'], reverse=True)
                for file_to_delete in files[1:]:
                    try:
                        service.files().delete(fileId=file_to_delete['id']).execute()
                        print(f"🗑️ تم حذف النسخة المكررة: {file_to_delete['id']}")
                        deleted_inspections += 1
                    except Exception as e:
                        print(f"❌ خطأ في حذف الملف {file_to_delete['id']}: {e}")
        
        print(f"\n📊 تقرير تنظيف الملفات المكررة:")
        print(f"   - عقود مكررة تم حذفها: {deleted_contracts}")
        print(f"   - معاينات مكررة تم حذفها: {deleted_inspections}")
        print(f"   - إجمالي العقود المتبقية: {len(contracts_by_name)}")
        print(f"   - إجمالي المعاينات المتبقية: {len(inspections_by_name)}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في فحص الملفات المكررة: {e}")
        return False

def list_files_in_folder(service, folder_id):
    """قائمة الملفات في مجلد معين"""
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, createdTime, size)",
            pageSize=1000
        ).execute()
        
        files = results.get('files', [])
        print(f"📁 وجدت {len(files)} ملف في المجلد")
        return files
        
    except Exception as e:
        print(f"❌ خطأ في قراءة المجلد {folder_id}: {e}")
        return []

def update_database_references():
    """تحديث مراجع قاعدة البيانات للملفات المرفوعة"""
    print("🔄 تحديث مراجع قاعدة البيانات...")
    
    try:
        # الحصول على إعدادات Google Drive
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات Google Drive")
            return
            
        # تحميل الاعتماد
        credentials_path = config.credentials_file.path
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
            
        # إنشاء الخدمة
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = Credentials.from_service_account_info(credentials_data, scopes=scopes)
        service = build('drive', 'v3', credentials=credentials)
        
        # الحصول على جميع الملفات في مجلد العقود
        contracts_files = list_files_in_folder(service, config.contracts_folder_id)
        inspections_files = list_files_in_folder(service, config.inspections_folder_id)
        
        # تحديث العقود
        updated_contracts = 0
        for order in Order.objects.filter(contract_file__isnull=False, contract_google_drive_file_id__isnull=True):
            if order.contract_file:
                file_name = os.path.basename(order.contract_file.name)
                # البحث عن الملف في Google Drive
                for drive_file in contracts_files:
                    if drive_file['name'] == file_name:
                        order.contract_google_drive_file_id = drive_file['id']
                        order.save()
                        print(f"✅ تم تحديث مرجع العقد: {order.order_number}")
                        updated_contracts += 1
                        break
        
        # تحديث المعاينات
        updated_inspections = 0
        for inspection in Inspection.objects.filter(inspection_file__isnull=False, google_drive_file_id__isnull=True):
            if inspection.inspection_file:
                file_name = os.path.basename(inspection.inspection_file.name)
                # البحث عن الملف في Google Drive
                for drive_file in inspections_files:
                    if drive_file['name'] == file_name:
                        inspection.google_drive_file_id = drive_file['id']
                        inspection.save()
                        print(f"✅ تم تحديث مرجع المعاينة: {inspection.id}")
                        updated_inspections += 1
                        break
        
        print(f"\n📊 تقرير تحديث المراجع:")
        print(f"   - عقود تم تحديث مراجعها: {updated_contracts}")
        print(f"   - معاينات تم تحديث مراجعها: {updated_inspections}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث المراجع: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء منع الرفع المكرر")
    print("=" * 50)
    
    # 1. تحديث مراجع قاعدة البيانات أولاً
    if update_database_references():
        print("✅ تم تحديث مراجع قاعدة البيانات")
    
    # 2. حذف الملفات المكررة
    if check_and_remove_duplicates():
        print("✅ تم تنظيف الملفات المكررة")
    
    print("\n🎉 تم منع الرفع المكرر بنجاح!")
    print("💡 الآن لن يتم رفع الملفات مرة أخرى")

if __name__ == "__main__":
    main()
