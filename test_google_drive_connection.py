#!/usr/bin/env python3
"""
سكريبت اختبار اتصال Google Drive وتشخيص المشاكل
"""

import os
import sys
import django
import json
from pathlib import Path

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from odoo_db_manager.models import GoogleDriveConfig
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_google_drive_config():
    """اختبار إعدادات Google Drive"""
    print("🔍 فحص إعدادات Google Drive...")
    
    try:
        # الحصول على الإعدادات النشطة
        config = GoogleDriveConfig.get_active_config()
        
        if not config:
            print("❌ لا توجد إعدادات Google Drive نشطة")
            return False
            
        print(f"✅ وجدت إعدادات نشطة: {config.name}")
        print(f"   - مجلد المعاينات: {config.inspections_folder_id}")
        print(f"   - مجلد العقود: {config.contracts_folder_id}")
        
        # فحص ملف الاعتماد
        if not config.credentials_file:
            print("❌ ملف اعتماد Google غير موجود")
            return False
            
        credentials_path = config.credentials_file.path
        print(f"   - مسار ملف الاعتماد: {credentials_path}")
        
        if not os.path.exists(credentials_path):
            print("❌ ملف اعتماد Google غير موجود في المسار المحدد")
            return False
            
        print("✅ ملف الاعتماد موجود")
        
        # فحص محتوى ملف الاعتماد
        try:
            with open(credentials_path, 'r') as f:
                credentials_data = json.load(f)
                
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
            missing_fields = [field for field in required_fields if field not in credentials_data]
            
            if missing_fields:
                print(f"❌ حقول مفقودة في ملف الاعتماد: {', '.join(missing_fields)}")
                return False
                
            if credentials_data.get('type') != 'service_account':
                print(f"❌ نوع الحساب غير صحيح: {credentials_data.get('type')} (يجب أن يكون service_account)")
                return False
                
            print(f"✅ ملف الاعتماد صحيح")
            print(f"   - نوع الحساب: {credentials_data.get('type')}")
            print(f"   - البريد الإلكتروني: {credentials_data.get('client_email')}")
            print(f"   - معرف المشروع: {credentials_data.get('project_id')}")
            
            return True, config, credentials_data
            
        except json.JSONDecodeError:
            print("❌ ملف الاعتماد ليس JSON صحيح")
            return False
        except Exception as e:
            print(f"❌ خطأ في قراءة ملف الاعتماد: {e}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في فحص إعدادات Google Drive: {e}")
        return False

def test_google_api_connection(config, credentials_data):
    """اختبار الاتصال بـ Google Drive API"""
    print("\n🔗 اختبار الاتصال بـ Google Drive API...")
    
    try:
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials
        
        # إنشاء الاعتماد
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = Credentials.from_service_account_info(credentials_data, scopes=scopes)
        
        # إنشاء خدمة Google Drive
        service = build('drive', 'v3', credentials=credentials)
        
        print("✅ تم إنشاء خدمة Google Drive بنجاح")
        
        # اختبار الاتصال بقائمة الملفات
        try:
            results = service.files().list(pageSize=1).execute()
            print("✅ تم الاتصال بـ Google Drive API بنجاح")
            
            # اختبار الوصول للمجلدات
            if config.inspections_folder_id:
                try:
                    folder = service.files().get(fileId=config.inspections_folder_id).execute()
                    print(f"✅ مجلد المعاينات متاح: {folder.get('name')}")
                except Exception as e:
                    print(f"❌ لا يمكن الوصول لمجلد المعاينات: {e}")
                    
            if config.contracts_folder_id:
                try:
                    folder = service.files().get(fileId=config.contracts_folder_id).execute()
                    print(f"✅ مجلد العقود متاح: {folder.get('name')}")
                except Exception as e:
                    print(f"❌ لا يمكن الوصول لمجلد العقود: {e}")
                    
            return True, service
            
        except Exception as e:
            print(f"❌ فشل في الاتصال بـ Google Drive API: {e}")
            return False, None
            
    except ImportError:
        print("❌ مكتبات Google API غير مثبتة")
        return False, None
    except Exception as e:
        print(f"❌ خطأ في إنشاء خدمة Google Drive: {e}")
        return False, None

def test_create_test_folder(service):
    """اختبار إنشاء مجلد تجريبي"""
    print("\n📁 اختبار إنشاء مجلد تجريبي...")
    
    try:
        # إنشاء مجلد تجريبي
        folder_metadata = {
            'name': f'Test Folder - {os.getpid()}',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(body=folder_metadata, fields='id,name').execute()
        folder_id = folder.get('id')
        folder_name = folder.get('name')
        
        print(f"✅ تم إنشاء مجلد تجريبي بنجاح")
        print(f"   - الاسم: {folder_name}")
        print(f"   - المعرف: {folder_id}")
        
        # حذف المجلد التجريبي
        try:
            service.files().delete(fileId=folder_id).execute()
            print("✅ تم حذف المجلد التجريبي بنجاح")
        except Exception as e:
            print(f"⚠️ لم يتم حذف المجلد التجريبي: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ فشل في إنشاء مجلد تجريبي: {e}")
        
        # تحليل نوع الخطأ
        error_str = str(e)
        if "HttpError 500" in error_str:
            print("💡 خطأ 500: مشكلة في خادم Google Drive")
            print("   - قد تكون مشكلة مؤقتة في Google")
            print("   - جرب مرة أخرى بعد دقائق")
        elif "HttpError 403" in error_str:
            print("💡 خطأ 403: مشكلة في الصلاحيات")
            print("   - تأكد من تفعيل Google Drive API")
            print("   - تأكد من صلاحيات Service Account")
        elif "HttpError 401" in error_str:
            print("💡 خطأ 401: مشكلة في المصادقة")
            print("   - تأكد من صحة ملف الاعتماد")
            print("   - تأكد من عدم انتهاء صلاحية المفاتيح")
        
        return False

def test_upload_permissions():
    """اختبار صلاحيات الرفع"""
    print("\n🔐 فحص صلاحيات الرفع...")
    
    try:
        from orders.services.google_drive_service import GoogleDriveService
        
        # إنشاء خدمة Google Drive
        drive_service = GoogleDriveService()
        
        if not drive_service.service:
            print("❌ لم يتم تهيئة خدمة Google Drive")
            return False
            
        print("✅ تم تهيئة خدمة Google Drive للعقود")
        
        # اختبار إنشاء مجلد العقود
        try:
            folder_id = drive_service.get_or_create_contracts_folder()
            if folder_id:
                print(f"✅ مجلد العقود متاح: {folder_id}")
            else:
                print("❌ فشل في الحصول على مجلد العقود")
        except Exception as e:
            print(f"❌ خطأ في الوصول لمجلد العقود: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار صلاحيات الرفع: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار اتصال Google Drive")
    print("=" * 50)
    
    # 1. فحص الإعدادات
    config_result = test_google_drive_config()
    if not config_result:
        print("\n❌ فشل في فحص الإعدادات")
        return 1
        
    success, config, credentials_data = config_result
    
    # 2. اختبار الاتصال
    api_result = test_google_api_connection(config, credentials_data)
    if not api_result[0]:
        print("\n❌ فشل في الاتصال بـ Google Drive API")
        return 1
        
    service = api_result[1]
    
    # 3. اختبار إنشاء مجلد
    folder_result = test_create_test_folder(service)
    
    # 4. اختبار صلاحيات الرفع
    upload_result = test_upload_permissions()
    
    print("\n" + "=" * 50)
    print("📊 ملخص النتائج:")
    print(f"   - إعدادات Google Drive: {'✅' if success else '❌'}")
    print(f"   - اتصال API: {'✅' if api_result[0] else '❌'}")
    print(f"   - إنشاء مجلد: {'✅' if folder_result else '❌'}")
    print(f"   - صلاحيات الرفع: {'✅' if upload_result else '❌'}")
    
    if success and api_result[0] and folder_result and upload_result:
        print("\n🎉 جميع الاختبارات نجحت! Google Drive جاهز للاستخدام")
        return 0
    else:
        print("\n⚠️ بعض الاختبارات فشلت. راجع الأخطاء أعلاه")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
