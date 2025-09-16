#!/usr/bin/env python3
"""
فحص تاريخ تغيير مجلدات Google Drive
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def check_database_history():
    """فحص تاريخ التغييرات في قاعدة البيانات"""
    print("🔍 فحص تاريخ التغييرات في قاعدة البيانات...")
    
    try:
        from django.db import connection
        
        # فحص جدول GoogleDriveConfig
        with connection.cursor() as cursor:
            # فحص بنية الجدول
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'odoo_db_manager_googledriveconfig'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print("📋 أعمدة جدول GoogleDriveConfig:")
            for col in columns:
                print(f"   - {col[0]}: {col[1]}")
            
            # فحص جميع السجلات
            cursor.execute("""
                SELECT id, name, inspections_folder_id, contracts_folder_id, 
                       created_at, updated_at, is_active
                FROM odoo_db_manager_googledriveconfig
                ORDER BY created_at;
            """)
            
            records = cursor.fetchall()
            print(f"\n📊 عدد السجلات: {len(records)}")
            
            for record in records:
                print(f"\n📋 سجل #{record[0]}:")
                print(f"   📝 الاسم: {record[1]}")
                print(f"   📁 مجلد المعاينات: {record[2]}")
                print(f"   📄 مجلد العقود: {record[3]}")
                print(f"   📅 تاريخ الإنشاء: {record[4]}")
                print(f"   📅 آخر تحديث: {record[5]}")
                print(f"   ✅ نشط: {record[6]}")
                
    except Exception as e:
        print(f"❌ خطأ في فحص قاعدة البيانات: {e}")

def check_old_folder_access():
    """فحص الوصول للمجلدات القديمة المحتملة"""
    print("\n🔍 فحص المجلدات القديمة المحتملة...")
    
    # قائمة بالمجلدات المحتملة من التحقيق السابق
    old_folder_ids = [
        "1h19hAiBSJcsGRaBxViyEzX04ddMUUYj5",  # مجلد عقود إضافي
        "0AH-TKqVe_Bl9Uk9PVA",  # المجلد الأب للمعاينات
        "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"  # المجلد الأب للعقود
    ]
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        for folder_id in old_folder_ids:
            try:
                folder_info = service.service.files().get(
                    fileId=folder_id,
                    fields='id,name,createdTime,modifiedTime,owners,parents'
                ).execute()
                
                print(f"\n📁 مجلد: {folder_info.get('name', 'بدون اسم')}")
                print(f"   🆔 ID: {folder_id}")
                print(f"   📅 تاريخ الإنشاء: {folder_info.get('createdTime')}")
                print(f"   📅 آخر تعديل: {folder_info.get('modifiedTime')}")
                
                owners = folder_info.get('owners', [])
                if owners:
                    print(f"   👤 المالك: {owners[0].get('emailAddress', 'غير محدد')}")
                
                # فحص المحتويات
                try:
                    results = service.service.files().list(
                        q=f"'{folder_id}' in parents",
                        fields='files(id,name)',
                        pageSize=5
                    ).execute()
                    
                    files = results.get('files', [])
                    print(f"   📊 عدد الملفات: {len(files)}")
                    
                    if files:
                        print("   📋 أمثلة على الملفات:")
                        for file in files[:3]:
                            print(f"      - {file.get('name')}")
                            
                except Exception as e:
                    print(f"   ⚠️ لا يمكن فحص المحتويات: {e}")
                    
            except Exception as e:
                print(f"❌ لا يمكن الوصول للمجلد {folder_id}: {e}")
                
    except Exception as e:
        print(f"❌ خطأ في فحص المجلدات القديمة: {e}")

def check_migration_history():
    """فحص تاريخ الهجرة"""
    print("\n🔍 فحص تاريخ الهجرة...")
    
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # فحص جدول الهجرة
            cursor.execute("""
                SELECT app, name, applied 
                FROM django_migrations 
                WHERE app = 'odoo_db_manager'
                ORDER BY applied;
            """)
            
            migrations = cursor.fetchall()
            print(f"📊 عدد الهجرات: {len(migrations)}")
            
            for migration in migrations:
                print(f"   📅 {migration[2]}: {migration[1]}")
                
    except Exception as e:
        print(f"❌ خطأ في فحص الهجرة: {e}")

def find_original_folders():
    """البحث عن المجلدات الأصلية"""
    print("\n🔍 البحث عن المجلدات الأصلية...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن جميع المجلدات
        search_queries = [
            "mimeType='application/vnd.google-apps.folder'",
        ]
        
        for query in search_queries:
            try:
                results = service.service.files().list(
                    q=query,
                    fields='files(id,name,createdTime,modifiedTime,owners)',
                    orderBy='createdTime asc',
                    pageSize=50
                ).execute()
                
                folders = results.get('files', [])
                print(f"📊 وجدت {len(folders)} مجلد:")
                
                # تصفية المجلدات ذات الصلة
                relevant_folders = []
                for folder in folders:
                    name = folder.get('name', '').lower()
                    if any(keyword in name for keyword in ['معاينات', 'inspections', 'عقود', 'contracts', 'crm', 'خواجة']):
                        relevant_folders.append(folder)
                
                print(f"📋 المجلدات ذات الصلة ({len(relevant_folders)}):")
                for folder in relevant_folders:
                    print(f"\n📁 {folder.get('name')}")
                    print(f"   🆔 ID: {folder.get('id')}")
                    print(f"   📅 تاريخ الإنشاء: {folder.get('createdTime')}")
                    
                    owners = folder.get('owners', [])
                    if owners:
                        print(f"   👤 المالك: {owners[0].get('emailAddress', 'غير محدد')}")
                        
            except Exception as e:
                print(f"❌ خطأ في البحث: {e}")
                
    except Exception as e:
        print(f"❌ خطأ في البحث عن المجلدات: {e}")

def main():
    """الدالة الرئيسية"""
    print("🕵️ تحقيق شامل في تاريخ مجلدات Google Drive")
    print("=" * 60)
    
    # فحص قاعدة البيانات
    check_database_history()
    
    # فحص تاريخ الهجرة
    check_migration_history()
    
    # فحص المجلدات القديمة
    check_old_folder_access()
    
    # البحث عن المجلدات الأصلية
    find_original_folders()
    
    print("\n" + "=" * 60)
    print("🎯 خلاصة التحقيق:")
    print("1. تم إنشاء مجلد المعاينات في: 2025-09-13T10:40:17.272Z")
    print("2. تم إنشاء مجلد العقود في: 2025-08-10T15:03:35.558Z")
    print("3. المالك: crmzakee@crmelkhawaga.iam.gserviceaccount.com")
    print("4. تم تحديث الإعدادات في: 2025-09-13 10:40:18")

if __name__ == "__main__":
    main()
