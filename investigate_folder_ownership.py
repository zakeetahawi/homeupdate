#!/usr/bin/env python3
"""
تحقيق في ملكية المجلدات وإعدادات النظام
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def check_system_settings():
    """فحص إعدادات النظام الحالية"""
    print("🔍 فحص إعدادات النظام...")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        configs = GoogleDriveConfig.objects.all()
        print(f"📊 عدد الإعدادات الموجودة: {configs.count()}")
        
        for i, config in enumerate(configs, 1):
            print(f"\n📋 إعداد #{i}:")
            print(f"   🆔 ID: {config.id}")
            print(f"   📁 مجلد المعاينات: {config.inspections_folder_id}")
            print(f"   📄 مجلد العقود: {config.contracts_folder_id}")
            print(f"   📅 تاريخ الإنشاء: {config.created_at if hasattr(config, 'created_at') else 'غير محدد'}")
            print(f"   📅 آخر تحديث: {config.updated_at if hasattr(config, 'updated_at') else 'غير محدد'}")
            
        return configs.first() if configs.exists() else None
        
    except Exception as e:
        print(f"❌ خطأ في فحص الإعدادات: {e}")
        return None

def get_folder_owner_info(folder_id, folder_name):
    """الحصول على معلومات مالك المجلد"""
    print(f"\n👤 فحص ملكية مجلد {folder_name}...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # الحصول على معلومات المجلد
        folder_info = service.service.files().get(
            fileId=folder_id,
            fields='id,name,createdTime,modifiedTime,owners,parents'
        ).execute()
        
        print(f"📁 اسم المجلد: {folder_info.get('name')}")
        print(f"📅 تاريخ الإنشاء: {folder_info.get('createdTime')}")
        print(f"📅 آخر تعديل: {folder_info.get('modifiedTime')}")
        
        # معلومات المالكين
        owners = folder_info.get('owners', [])
        print(f"👥 عدد المالكين: {len(owners)}")
        
        for i, owner in enumerate(owners, 1):
            print(f"   👤 مالك #{i}:")
            print(f"      📧 البريد: {owner.get('emailAddress', 'غير محدد')}")
            print(f"      👤 الاسم: {owner.get('displayName', 'غير محدد')}")
            print(f"      🔑 النوع: {owner.get('kind', 'غير محدد')}")
            print(f"      📸 الصورة: {owner.get('photoLink', 'لا توجد')}")
        
        # المجلد الأب
        parents = folder_info.get('parents', [])
        if parents:
            print(f"📂 المجلد الأب: {parents[0]}")
        else:
            print("📂 المجلد في الجذر")
            
        return folder_info
        
    except Exception as e:
        print(f"❌ خطأ في فحص الملكية: {e}")
        return None

def check_service_account_info():
    """فحص معلومات حساب الخدمة"""
    print("\n🔧 فحص حساب الخدمة...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # الحصول على معلومات المستخدم الحالي
        about = service.service.about().get(fields='user').execute()
        user = about.get('user', {})
        
        print(f"👤 حساب الخدمة الحالي:")
        print(f"   📧 البريد: {user.get('emailAddress', 'غير محدد')}")
        print(f"   👤 الاسم: {user.get('displayName', 'غير محدد')}")
        print(f"   🔑 النوع: {user.get('kind', 'غير محدد')}")
        
        return user
        
    except Exception as e:
        print(f"❌ خطأ في فحص حساب الخدمة: {e}")
        return None

def check_folder_history():
    """فحص تاريخ إنشاء المجلدات"""
    print("\n📅 فحص تاريخ إنشاء المجلدات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن جميع المجلدات التي تحتوي على "معاينات" أو "عقود"
        search_queries = [
            "name contains 'معاينات' and mimeType='application/vnd.google-apps.folder'",
            "name contains 'Inspections' and mimeType='application/vnd.google-apps.folder'",
            "name contains 'عقود' and mimeType='application/vnd.google-apps.folder'",
            "name contains 'Contracts' and mimeType='application/vnd.google-apps.folder'"
        ]
        
        all_folders = []
        
        for query in search_queries:
            try:
                results = service.service.files().list(
                    q=query,
                    fields='files(id,name,createdTime,modifiedTime,owners)',
                    orderBy='createdTime desc'
                ).execute()
                
                folders = results.get('files', [])
                all_folders.extend(folders)
                
            except Exception as e:
                print(f"⚠️ خطأ في البحث: {e}")
        
        # إزالة المكررات
        unique_folders = {}
        for folder in all_folders:
            unique_folders[folder['id']] = folder
        
        print(f"📊 وجدت {len(unique_folders)} مجلد:")
        
        for folder in sorted(unique_folders.values(), key=lambda x: x.get('createdTime', '')):
            print(f"\n📁 {folder.get('name')}")
            print(f"   🆔 ID: {folder.get('id')}")
            print(f"   📅 تاريخ الإنشاء: {folder.get('createdTime')}")
            print(f"   📅 آخر تعديل: {folder.get('modifiedTime')}")
            
            owners = folder.get('owners', [])
            if owners:
                print(f"   👤 المالك: {owners[0].get('emailAddress', 'غير محدد')}")
        
        return list(unique_folders.values())
        
    except Exception as e:
        print(f"❌ خطأ في فحص التاريخ: {e}")
        return []

def compare_with_old_settings():
    """مقارنة مع الإعدادات القديمة"""
    print("\n🔍 البحث عن الإعدادات القديمة...")
    
    # فحص ملفات الإعدادات
    settings_files = [
        'crm/settings.py',
        'crm/settings_production.py',
        'crm/local_settings.py'
    ]
    
    for settings_file in settings_files:
        if os.path.exists(settings_file):
            print(f"\n📄 فحص {settings_file}...")
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # البحث عن إعدادات Google Drive
                if 'GOOGLE_DRIVE' in content or 'DRIVE_FOLDER' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if any(keyword in line for keyword in ['GOOGLE_DRIVE', 'DRIVE_FOLDER', 'INSPECTIONS_FOLDER', 'CONTRACTS_FOLDER']):
                            print(f"   السطر {i+1}: {line.strip()}")
                            
            except Exception as e:
                print(f"   ❌ خطأ في قراءة الملف: {e}")

def main():
    """الدالة الرئيسية"""
    print("🕵️ تحقيق في ملكية مجلدات Google Drive")
    print("=" * 60)
    
    # فحص إعدادات النظام
    config = check_system_settings()
    
    if not config:
        print("❌ لا توجد إعدادات في النظام")
        return
    
    # فحص حساب الخدمة
    service_account = check_service_account_info()
    
    # فحص ملكية المجلدات الحالية
    if config.inspections_folder_id:
        inspections_info = get_folder_owner_info(config.inspections_folder_id, "المعاينات")
    
    if config.contracts_folder_id:
        contracts_info = get_folder_owner_info(config.contracts_folder_id, "العقود")
    
    # فحص تاريخ المجلدات
    all_folders = check_folder_history()
    
    # مقارنة مع الإعدادات القديمة
    compare_with_old_settings()
    
    print("\n" + "=" * 60)
    print("🎯 خلاصة التحقيق:")
    
    if service_account:
        print(f"👤 حساب الخدمة: {service_account.get('emailAddress', 'غير محدد')}")
    
    print(f"📁 مجلد المعاينات الحالي: {config.inspections_folder_id}")
    print(f"📄 مجلد العقود الحالي: {config.contracts_folder_id}")
    
    print(f"\n📊 إجمالي المجلدات الموجودة: {len(all_folders)}")
    
    print("\n💡 التوصيات:")
    print("1. تحقق من تاريخ إنشاء المجلدات")
    print("2. قارن مع الإعدادات القديمة")
    print("3. تأكد من استخدام المجلدات الصحيحة")

if __name__ == "__main__":
    main()
