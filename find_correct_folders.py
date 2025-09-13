#!/usr/bin/env python3
"""
البحث عن المجلدات الصحيحة في Google Drive
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def search_for_folders():
    """البحث عن جميع المجلدات المتاحة"""
    print("🔍 البحث عن جميع المجلدات المتاحة...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن جميع المجلدات
        query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = service.service.files().list(
            q=query,
            fields='files(id,name,webViewLink,parents)',
            pageSize=100
        ).execute()
        
        folders = results.get('files', [])
        print(f"📊 وجد {len(folders)} مجلد")
        
        print("\n📁 المجلدات المتاحة:")
        for folder in folders:
            folder_name = folder.get('name', 'بدون اسم')
            folder_id = folder.get('id')
            parents = folder.get('parents', [])
            
            print(f"\n📂 {folder_name}")
            print(f"   🆔 المعرف: {folder_id}")
            print(f"   🔗 الرابط: {folder.get('webViewLink')}")
            if parents:
                print(f"   📁 المجلد الأب: {parents[0]}")
            
            # البحث عن الملفات في هذا المجلد
            try:
                file_results = service.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields='files(id,name)',
                    pageSize=5
                ).execute()
                
                files = file_results.get('files', [])
                print(f"   📊 عدد الملفات: {len(files)}")
                
                if files:
                    print("   📋 عينة من الملفات:")
                    for file in files[:3]:
                        print(f"      - {file.get('name')}")
                        
            except Exception as e:
                print(f"   ❌ خطأ في قراءة الملفات: {e}")
        
        return folders
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن المجلدات: {e}")
        return []

def search_for_inspection_files():
    """البحث عن ملفات المعاينات في جميع المجلدات"""
    print("\n🔍 البحث عن ملفات المعاينات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن ملفات PDF التي تبدو كمعاينات
        query = "mimeType='application/pdf' and trashed=false"
        
        results = service.service.files().list(
            q=query,
            fields='files(id,name,parents,size)',
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        print(f"📊 وجد {len(files)} ملف PDF")
        
        # تصنيف الملفات
        inspection_files = []
        contract_files = []
        other_files = []
        
        for file in files:
            file_name = file.get('name', '')
            
            if 'عقد' in file_name or 'contract' in file_name.lower():
                contract_files.append(file)
            elif any(keyword in file_name for keyword in ['فرع', 'Open_Air', '_20', '-0']):
                inspection_files.append(file)
            else:
                other_files.append(file)
        
        print(f"\n📊 تصنيف الملفات:")
        print(f"   📁 ملفات معاينات: {len(inspection_files)}")
        print(f"   📄 ملفات عقود: {len(contract_files)}")
        print(f"   📋 ملفات أخرى: {len(other_files)}")
        
        # عرض ملفات المعاينات وأماكنها
        if inspection_files:
            print(f"\n📁 ملفات المعاينات وأماكنها:")
            folder_counts = {}
            
            for file in inspection_files:
                parents = file.get('parents', ['root'])
                parent = parents[0] if parents else 'root'
                
                if parent not in folder_counts:
                    folder_counts[parent] = []
                folder_counts[parent].append(file.get('name'))
            
            for folder_id, files_in_folder in folder_counts.items():
                print(f"\n📂 المجلد {folder_id}:")
                print(f"   📊 عدد الملفات: {len(files_in_folder)}")
                print("   📋 عينة من الملفات:")
                for file_name in files_in_folder[:3]:
                    print(f"      - {file_name}")
        
        # عرض ملفات العقود وأماكنها
        if contract_files:
            print(f"\n📄 ملفات العقود وأماكنها:")
            folder_counts = {}
            
            for file in contract_files:
                parents = file.get('parents', ['root'])
                parent = parents[0] if parents else 'root'
                
                if parent not in folder_counts:
                    folder_counts[parent] = []
                folder_counts[parent].append(file.get('name'))
            
            for folder_id, files_in_folder in folder_counts.items():
                print(f"\n📂 المجلد {folder_id}:")
                print(f"   📊 عدد الملفات: {len(files_in_folder)}")
                print("   📋 عينة من الملفات:")
                for file_name in files_in_folder[:3]:
                    print(f"      - {file_name}")
        
        return {
            'inspections': inspection_files,
            'contracts': contract_files,
            'others': other_files
        }
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن الملفات: {e}")
        return {}

def check_current_config():
    """فحص الإعدادات الحالية"""
    print("\n⚙️ فحص الإعدادات الحالية...")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات نشطة")
            return None
            
        print(f"✅ الإعدادات النشطة:")
        print(f"   📝 الاسم: {config.name}")
        print(f"   📁 مجلد المعاينات: {config.inspections_folder_id}")
        print(f"   📄 مجلد العقود: {config.contracts_folder_id}")
        print(f"   ✅ نشط: {config.is_active}")
        
        return config
        
    except Exception as e:
        print(f"❌ خطأ في فحص الإعدادات: {e}")
        return None

def main():
    """الدالة الرئيسية"""
    print("🔍 البحث عن المجلدات والملفات الصحيحة")
    print("=" * 60)
    
    # فحص الإعدادات الحالية
    config = check_current_config()
    
    # البحث عن المجلدات
    folders = search_for_folders()
    
    # البحث عن الملفات
    files_info = search_for_inspection_files()
    
    print("\n" + "=" * 60)
    print("🎯 الخلاصة:")
    
    if folders:
        print(f"📁 وجد {len(folders)} مجلد متاح")
    
    if files_info:
        print(f"📊 الملفات:")
        print(f"   📁 معاينات: {len(files_info.get('inspections', []))}")
        print(f"   📄 عقود: {len(files_info.get('contracts', []))}")
        print(f"   📋 أخرى: {len(files_info.get('others', []))}")
    
    print("\n💡 يرجى تحديد المجلد الصحيح للمعاينات من القائمة أعلاه")
    print("   وسأقوم بنقل جميع ملفات المعاينات إليه")

if __name__ == "__main__":
    main()
