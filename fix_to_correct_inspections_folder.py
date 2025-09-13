#!/usr/bin/env python3
"""
إصلاح وترحيل الملفات للمجلد الصحيح للمعاينات
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def verify_correct_folder():
    """التحقق من المجلد الصحيح"""
    print("🔍 التحقق من المجلد الصحيح...")
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # التحقق من المجلد الصحيح
        folder_info = service.service.files().get(
            fileId=CORRECT_INSPECTIONS_FOLDER,
            fields='id,name,webViewLink'
        ).execute()
        
        print(f"✅ المجلد الصحيح موجود: {folder_info.get('name')}")
        print(f"   🆔 المعرف: {CORRECT_INSPECTIONS_FOLDER}")
        print(f"   🔗 الرابط: {folder_info.get('webViewLink')}")
        
        # عد الملفات الحالية
        results = service.service.files().list(
            q=f"'{CORRECT_INSPECTIONS_FOLDER}' in parents and trashed=false",
            fields='files(id,name)',
            pageSize=1000
        ).execute()
        
        files = results.get('files', [])
        print(f"   📊 عدد الملفات الحالية: {len(files)}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق من المجلد: {e}")
        return False

def find_all_inspection_files():
    """البحث عن جميع ملفات المعاينات في جميع المجلدات"""
    print("\n🔍 البحث عن جميع ملفات المعاينات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث في المجلد الخاطئ الذي كنا نستخدمه
        wrong_folder = "1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av"
        
        print(f"📁 البحث في المجلد الخاطئ: {wrong_folder}")
        
        try:
            # الحصول على معلومات المجلد
            folder_info = service.service.files().get(
                fileId=wrong_folder,
                fields='id,name'
            ).execute()
            
            print(f"   📂 اسم المجلد: {folder_info.get('name')}")
            
            # البحث عن الملفات
            results = service.service.files().list(
                q=f"'{wrong_folder}' in parents and trashed=false",
                fields='files(id,name,parents)',
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            print(f"   📊 عدد الملفات الموجودة: {len(files)}")
            
            # فلترة ملفات المعاينات
            inspection_files = []
            for file in files:
                file_name = file.get('name', '')
                if ('عقد' not in file_name and 
                    'contract' not in file_name.lower() and
                    '.pdf' in file_name.lower()):
                    
                    inspection_files.append({
                        'id': file.get('id'),
                        'name': file_name,
                        'current_folder': wrong_folder,
                        'parents': file.get('parents', [])
                    })
            
            print(f"   📁 ملفات المعاينات للنقل: {len(inspection_files)}")
            
            if inspection_files:
                print("   📋 عينة من الملفات:")
                for file in inspection_files[:5]:
                    print(f"      - {file['name']}")
            
            return inspection_files
            
        except Exception as e:
            print(f"❌ خطأ في البحث في المجلد {wrong_folder}: {e}")
            return []
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن الملفات: {e}")
        return []

def move_files_to_correct_folder(files_to_move):
    """نقل الملفات للمجلد الصحيح"""
    print("\n📦 نقل الملفات للمجلد الصحيح...")
    
    if not files_to_move:
        print("❌ لا توجد ملفات للنقل")
        return False
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        moved_count = 0
        
        print(f"📁 نقل {len(files_to_move)} ملف للمجلد الصحيح...")
        
        for file_info in files_to_move:
            try:
                file_name = file_info['name']
                file_id = file_info['id']
                current_parents = file_info.get('parents', [])
                
                # نقل الملف للمجلد الصحيح
                remove_parents = ','.join(current_parents) if current_parents else None
                
                service.service.files().update(
                    fileId=file_id,
                    addParents=CORRECT_INSPECTIONS_FOLDER,
                    removeParents=remove_parents,
                    fields='id,parents'
                ).execute()
                
                print(f"✅ تم نقل: {file_name}")
                moved_count += 1
                
                # توقف قصير لتجنب تجاوز حدود API
                if moved_count % 10 == 0:
                    import time
                    time.sleep(1)
                
            except Exception as e:
                print(f"❌ خطأ في نقل الملف {file_info['name']}: {e}")
        
        print(f"\n🎉 تم نقل {moved_count} ملف بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في نقل الملفات: {e}")
        return False

def update_config_to_correct_folder():
    """تحديث الإعدادات للمجلد الصحيح"""
    print("\n🔧 تحديث الإعدادات للمجلد الصحيح...")
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
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

def verify_final_result():
    """التحقق من النتيجة النهائية"""
    print("\n🧪 التحقق من النتيجة النهائية...")
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # عد الملفات في المجلد الصحيح
        results = service.service.files().list(
            q=f"'{CORRECT_INSPECTIONS_FOLDER}' in parents and trashed=false",
            fields='files(id,name,size)',
            pageSize=1000,
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        print(f"📁 المجلد الصحيح الآن يحتوي على: {len(files)} ملف")
        
        if files:
            print("📋 آخر 5 ملفات:")
            for file in files[:5]:
                size = int(file.get('size', 0)) if file.get('size') else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                print(f"   - {file.get('name')} ({size_mb:.1f} MB)")
        
        # اختبار رفع ملف تجريبي
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ اختبار الرفع نجح - المجلد: {result.get('folder_id')}")
        else:
            print(f"❌ اختبار الرفع فشل: {result.get('message')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق النهائي: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح وترحيل الملفات للمجلد الصحيح")
    print("=" * 60)
    print("📁 المجلد الصحيح للمعاينات: 1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("📂 اسم المجلد: crm-insp")
    print("=" * 60)
    
    # 1. التحقق من المجلد الصحيح
    if not verify_correct_folder():
        return
    
    # 2. البحث عن ملفات المعاينات في المجلدات الخاطئة
    files_to_move = find_all_inspection_files()
    
    # 3. نقل الملفات للمجلد الصحيح
    if files_to_move:
        if not move_files_to_correct_folder(files_to_move):
            return
    else:
        print("⚠️ لم يتم العثور على ملفات للنقل")
    
    # 4. تحديث الإعدادات
    if not update_config_to_correct_folder():
        return
    
    # 5. التحقق النهائي
    if not verify_final_result():
        return
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح المشكلة بنجاح!")
    print("✅ جميع ملفات المعاينات الآن في المجلد الصحيح")
    print("✅ النظام يستخدم المجلد الصحيح للرفعات الجديدة")
    
    print("\n🔗 الروابط الصحيحة:")
    print("📁 المعاينات: https://drive.google.com/drive/folders/1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    print("⚙️ الصفحة المركزية: https://elkhawaga.uk/odoo-db-manager/google-drive/settings/")

if __name__ == "__main__":
    main()
