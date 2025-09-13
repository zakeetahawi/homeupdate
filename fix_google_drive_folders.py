#!/usr/bin/env python3
"""
إصلاح مشكلة مجلدات Google Drive المفقودة
"""

import os
import sys
import django
import json

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from odoo_db_manager.models import GoogleDriveConfig
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_google_drive_folders():
    """إصلاح مجلدات Google Drive"""
    print("🔧 إصلاح مجلدات Google Drive...")
    
    try:
        # الحصول على الإعدادات
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات Google Drive")
            return False
            
        # تحميل الاعتماد
        credentials_path = config.credentials_file.path
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
            
        # إنشاء الخدمة
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = Credentials.from_service_account_info(credentials_data, scopes=scopes)
        service = build('drive', 'v3', credentials=credentials)
        
        print("✅ تم الاتصال بـ Google Drive")
        
        # إنشاء مجلد المعاينات الجديد
        inspections_folder = create_folder(service, "المعاينات - Inspections")
        if inspections_folder:
            config.inspections_folder_id = inspections_folder['id']
            config.inspections_folder_name = inspections_folder['name']
            print(f"✅ تم إنشاء مجلد المعاينات: {inspections_folder['name']} ({inspections_folder['id']})")
        
        # إنشاء مجلد العقود الجديد
        contracts_folder = create_folder(service, "العقود - Contracts")
        if contracts_folder:
            config.contracts_folder_id = contracts_folder['id']
            config.contracts_folder_name = contracts_folder['name']
            print(f"✅ تم إنشاء مجلد العقود: {contracts_folder['name']} ({contracts_folder['id']})")
        
        # حفظ الإعدادات
        config.save()
        print("✅ تم حفظ الإعدادات الجديدة")
        
        # اختبار رفع ملف تجريبي
        test_upload(service, config)
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إصلاح المجلدات: {e}")
        return False

def create_folder(service, folder_name):
    """إنشاء مجلد في Google Drive"""
    try:
        # البحث عن المجلد أولاً
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        if folders:
            print(f"📁 المجلد موجود بالفعل: {folder_name}")
            return folders[0]
        
        # إنشاء المجلد
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(body=folder_metadata, fields='id,name').execute()
        print(f"📁 تم إنشاء مجلد جديد: {folder_name}")
        return folder
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء المجلد {folder_name}: {e}")
        return None

def test_upload(service, config):
    """اختبار رفع ملف تجريبي"""
    print("\n📤 اختبار رفع ملف تجريبي...")
    
    try:
        # إنشاء ملف تجريبي
        test_content = f"ملف تجريبي - {os.getpid()}\nتم الإنشاء في: {os.getcwd()}"
        test_file_path = "/tmp/test_upload.txt"
        
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # رفع الملف إلى مجلد المعاينات
        from googleapiclient.http import MediaFileUpload
        
        file_metadata = {
            'name': f'test_file_{os.getpid()}.txt',
            'parents': [config.inspections_folder_id]
        }
        
        media = MediaFileUpload(test_file_path, mimetype='text/plain')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()
        
        print(f"✅ تم رفع الملف التجريبي بنجاح!")
        print(f"   - الاسم: {file.get('name')}")
        print(f"   - المعرف: {file.get('id')}")
        print(f"   - الرابط: {file.get('webViewLink')}")
        
        # حذف الملف التجريبي من Google Drive
        try:
            service.files().delete(fileId=file.get('id')).execute()
            print("✅ تم حذف الملف التجريبي من Google Drive")
        except:
            pass
            
        # حذف الملف المحلي
        try:
            os.remove(test_file_path)
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"❌ فشل في اختبار الرفع: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء إصلاح مجلدات Google Drive")
    print("=" * 50)
    
    success = fix_google_drive_folders()
    
    if success:
        print("\n🎉 تم إصلاح مجلدات Google Drive بنجاح!")
        print("💡 الآن يمكن للنظام رفع الملفات بشكل طبيعي")
    else:
        print("\n❌ فشل في إصلاح المجلدات")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
