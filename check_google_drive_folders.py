#!/usr/bin/env python3
"""
فحص مجلدات Google Drive والوصول إليها
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def check_drive_config():
    """فحص إعدادات Google Drive الحالية"""
    print("🔍 فحص إعدادات Google Drive...")

    try:
        from odoo_db_manager.models import GoogleDriveConfig
        config = GoogleDriveConfig.objects.first()

        if config:
            print(f"✅ إعدادات Google Drive موجودة")
            print(f"📁 مجلد المعاينات: {config.inspections_folder_id}")
            print(f"📁 مجلد العقود: {config.contracts_folder_id}")

            return config
        else:
            print("❌ لا توجد إعدادات Google Drive")
            return None

    except Exception as e:
        print(f"❌ خطأ في فحص الإعدادات: {e}")
        return None

def test_folder_access(folder_id, folder_name):
    """اختبار الوصول لمجلد محدد"""
    print(f"\n🔍 اختبار الوصول لمجلد {folder_name}...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # محاولة الحصول على معلومات المجلد
        folder_info = service.service.files().get(
            fileId=folder_id,
            fields='id,name,parents,permissions,webViewLink'
        ).execute()
        
        print(f"✅ المجلد متاح: {folder_info.get('name')}")
        print(f"🔗 ID: {folder_info.get('id')}")
        print(f"🌐 رابط المجلد: {folder_info.get('webViewLink')}")
        
        # فحص الصلاحيات
        try:
            permissions = service.service.permissions().list(fileId=folder_id).execute()
            print(f"👥 عدد الصلاحيات: {len(permissions.get('permissions', []))}")
            
            for perm in permissions.get('permissions', []):
                print(f"   - {perm.get('type')}: {perm.get('emailAddress', 'N/A')} ({perm.get('role')})")
                
        except Exception as e:
            print(f"⚠️ لا يمكن فحص الصلاحيات: {e}")
        
        return folder_info
        
    except Exception as e:
        print(f"❌ خطأ في الوصول للمجلد: {e}")
        return None

def check_recent_uploads():
    """فحص الملفات المرفوعة حديثاً"""
    print("\n📊 فحص الملفات المرفوعة حديثاً...")
    
    try:
        from inspections.models import Inspection
        from orders.models import Order
        
        # المعاينات المرفوعة حديثاً
        recent_inspections = Inspection.objects.filter(
            google_drive_file_id__isnull=False
        ).order_by('-id')[:5]
        
        print("📋 آخر 5 معاينات مرفوعة:")
        for inspection in recent_inspections:
            print(f"   - معاينة {inspection.id}: {inspection.google_drive_file_id}")
            print(f"     رابط: {inspection.google_drive_file_url}")
        
        # العقود المرفوعة حديثاً
        recent_contracts = Order.objects.filter(
            contract_google_drive_file_id__isnull=False
        ).order_by('-id')[:5]
        
        print("\n📄 آخر 5 عقود مرفوعة:")
        for contract in recent_contracts:
            print(f"   - عقد {contract.order_number}: {contract.contract_google_drive_file_id}")
            print(f"     رابط: {contract.contract_google_drive_url}")
            
    except Exception as e:
        print(f"❌ خطأ في فحص الملفات: {e}")

def check_folder_contents(folder_id, folder_name):
    """فحص محتويات المجلد"""
    print(f"\n📁 فحص محتويات مجلد {folder_name}...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن الملفات في المجلد
        results = service.service.files().list(
            q=f"'{folder_id}' in parents",
            fields='files(id,name,createdTime,size)',
            orderBy='createdTime desc',
            pageSize=10
        ).execute()
        
        files = results.get('files', [])
        print(f"📊 عدد الملفات: {len(files)}")
        
        if files:
            print("📋 آخر 10 ملفات:")
            for file in files:
                size = int(file.get('size', 0)) if file.get('size') else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                print(f"   - {file.get('name')} ({size_mb:.1f} MB)")
                print(f"     ID: {file.get('id')}")
                print(f"     تاريخ: {file.get('createdTime')}")
        else:
            print("📭 المجلد فارغ")
            
    except Exception as e:
        print(f"❌ خطأ في فحص المحتويات: {e}")

def create_shared_folder(parent_folder_id, folder_name, user_email):
    """إنشاء مجلد مشترك مع المستخدم"""
    print(f"\n🔧 إنشاء مجلد مشترك: {folder_name}...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # إنشاء المجلد
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id] if parent_folder_id else []
        }
        
        folder = service.service.files().create(
            body=folder_metadata,
            fields='id,name,webViewLink'
        ).execute()
        
        print(f"✅ تم إنشاء المجلد: {folder.get('name')}")
        print(f"🔗 ID: {folder.get('id')}")
        print(f"🌐 رابط: {folder.get('webViewLink')}")
        
        # مشاركة المجلد مع المستخدم
        if user_email:
            permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': user_email
            }
            
            service.service.permissions().create(
                fileId=folder.get('id'),
                body=permission,
                sendNotificationEmail=True
            ).execute()
            
            print(f"✅ تم مشاركة المجلد مع: {user_email}")
        
        return folder.get('id')
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء المجلد: {e}")
        return None

def main():
    """الدالة الرئيسية"""
    print("🔍 فحص شامل لمجلدات Google Drive")
    print("=" * 50)
    
    # فحص الإعدادات
    config = check_drive_config()

    if not config:
        print("❌ لا يمكن المتابعة بدون إعدادات")
        return

    # استخدام المجلدات من الإعدادات
    inspections_folder_id = config.inspections_folder_id
    contracts_folder_id = config.contracts_folder_id
    
    # فحص مجلد المعاينات
    if inspections_folder_id:
        inspections_info = test_folder_access(inspections_folder_id, "المعاينات")
        if inspections_info:
            check_folder_contents(inspections_folder_id, "المعاينات")

    # فحص مجلد العقود
    if contracts_folder_id:
        contracts_info = test_folder_access(contracts_folder_id, "العقود")
        if contracts_info:
            check_folder_contents(contracts_folder_id, "العقود")
    
    # فحص الملفات المرفوعة حديثاً
    check_recent_uploads()
    
    print("\n" + "=" * 50)
    print("🎯 انتهى الفحص")
    
    # اقتراح الحل
    print("\n💡 الحلول المقترحة:")
    print("1. مشاركة المجلدات الحالية مع بريدك الإلكتروني")
    print("2. إنشاء مجلدات جديدة مشتركة")
    print("3. نقل الملفات للمجلدات القديمة")

if __name__ == "__main__":
    main()
