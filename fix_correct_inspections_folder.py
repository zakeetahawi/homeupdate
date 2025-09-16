#!/usr/bin/env python3
"""
إصلاح مجلد المعاينات الصحيح ونقل جميع الملفات إليه
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def update_inspections_folder_config():
    """تحديث مجلد المعاينات في الإعدادات"""
    print("🔧 تحديث مجلد المعاينات في الإعدادات...")
    
    # المجلد الصحيح للمعاينات
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

def find_all_inspection_files():
    """البحث عن جميع ملفات المعاينات في جميع المجلدات"""
    print("\n🔍 البحث عن جميع ملفات المعاينات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # المجلدات المحتملة للبحث فيها
        folders_to_search = [
            "1jMeDl6AqrS-pzX_ECfXGACOekiW0b7Av",  # المجلد القديم
            "1h19hAiBSJcsGRaBxViyEzX04ddMUUYj5",   # مجلد إضافي
            "root"  # المجلد الجذر
        ]
        
        all_inspection_files = []
        
        for folder_id in folders_to_search:
            try:
                print(f"\n📁 البحث في المجلد: {folder_id}")
                
                if folder_id == "root":
                    # البحث في الجذر
                    query = "trashed=false and mimeType='application/pdf'"
                else:
                    # البحث في مجلد محدد
                    query = f"'{folder_id}' in parents and trashed=false and mimeType='application/pdf'"
                
                results = service.service.files().list(
                    q=query,
                    fields='files(id,name,parents)',
                    pageSize=1000
                ).execute()
                
                files = results.get('files', [])
                print(f"   📊 وجد {len(files)} ملف PDF")
                
                # فلترة ملفات المعاينات (تحتوي على أسماء عملاء وليس "عقد")
                for file in files:
                    file_name = file.get('name', '')
                    if ('عقد' not in file_name and 
                        'contract' not in file_name.lower() and
                        '.pdf' in file_name.lower() and
                        any(keyword in file_name for keyword in ['فرع', 'Open_Air', '_20', '-0'])):
                        
                        all_inspection_files.append({
                            'id': file.get('id'),
                            'name': file_name,
                            'current_folder': folder_id,
                            'parents': file.get('parents', [])
                        })
                        
            except Exception as e:
                print(f"❌ خطأ في البحث في المجلد {folder_id}: {e}")
        
        print(f"\n📊 إجمالي ملفات المعاينات الموجودة: {len(all_inspection_files)}")
        
        # عرض عينة من الملفات
        if all_inspection_files:
            print("\n📋 عينة من الملفات الموجودة:")
            for file in all_inspection_files[:5]:
                print(f"   - {file['name']}")
                print(f"     📁 في المجلد: {file['current_folder']}")
        
        return all_inspection_files
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن الملفات: {e}")
        return []

def move_inspections_to_correct_folder(inspection_files):
    """نقل جميع ملفات المعاينات للمجلد الصحيح"""
    print("\n📦 نقل ملفات المعاينات للمجلد الصحيح...")
    
    if not inspection_files:
        print("✅ لا توجد ملفات للنقل")
        return True
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        moved_count = 0
        skipped_count = 0
        
        for file_info in inspection_files:
            try:
                file_name = file_info['name']
                file_id = file_info['id']
                current_parents = file_info.get('parents', [])
                
                # تحقق إذا كان الملف بالفعل في المجلد الصحيح
                if CORRECT_INSPECTIONS_FOLDER in current_parents:
                    print(f"⏭️ تم تخطي (موجود بالفعل): {file_name}")
                    skipped_count += 1
                    continue
                
                # نقل الملف للمجلد الصحيح
                # إزالة من المجلدات الحالية وإضافة للمجلد الصحيح
                remove_parents = ','.join(current_parents) if current_parents else None
                
                service.service.files().update(
                    fileId=file_id,
                    addParents=CORRECT_INSPECTIONS_FOLDER,
                    removeParents=remove_parents,
                    fields='id,parents'
                ).execute()
                
                print(f"✅ تم نقل: {file_name}")
                moved_count += 1
                
            except Exception as e:
                print(f"❌ خطأ في نقل الملف {file_info['name']}: {e}")
        
        print(f"\n🎉 تم نقل {moved_count} ملف بنجاح")
        print(f"⏭️ تم تخطي {skipped_count} ملف (موجود بالفعل)")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في نقل الملفات: {e}")
        return False

def verify_correct_folder():
    """التحقق من المجلد الصحيح"""
    print("\n🧪 التحقق من المجلد الصحيح...")
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # التحقق من وجود المجلد
        folder_info = service.service.files().get(
            fileId=CORRECT_INSPECTIONS_FOLDER,
            fields='id,name,webViewLink'
        ).execute()
        
        print(f"✅ المجلد الصحيح متاح: {folder_info.get('name')}")
        print(f"   🆔 المعرف: {CORRECT_INSPECTIONS_FOLDER}")
        print(f"   🔗 الرابط: {folder_info.get('webViewLink')}")
        
        # عد الملفات في المجلد
        results = service.service.files().list(
            q=f"'{CORRECT_INSPECTIONS_FOLDER}' in parents and trashed=false",
            fields='files(id,name,size)',
            pageSize=1000
        ).execute()
        
        files = results.get('files', [])
        print(f"   📊 عدد الملفات: {len(files)}")
        
        if files:
            print("   📋 آخر 5 ملفات:")
            for file in files[:5]:
                size = int(file.get('size', 0)) if file.get('size') else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                print(f"      - {file.get('name')} ({size_mb:.1f} MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق من المجلد: {e}")
        return False

def test_upload_to_correct_folder():
    """اختبار رفع ملف للمجلد الصحيح"""
    print("\n🧪 اختبار رفع ملف للمجلد الصحيح...")
    
    try:
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار الرفع للمجلد الصحيح")
            print(f"   📁 المجلد: {result.get('folder_id')}")
            print(f"   📄 الملف التجريبي: {result.get('file_name')}")
        else:
            print(f"❌ فشل اختبار الرفع")
            print(f"   💬 الرسالة: {result.get('message')}")
            
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الرفع: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح مجلد المعاينات الصحيح")
    print("=" * 60)
    print("📁 المجلد الصحيح للمعاينات: 1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("📄 مجلد العقود (صحيح): 1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    print("=" * 60)
    
    # 1. تحديث الإعدادات
    if not update_inspections_folder_config():
        return
    
    # 2. التحقق من المجلد الصحيح
    if not verify_correct_folder():
        return
    
    # 3. البحث عن جميع ملفات المعاينات
    inspection_files = find_all_inspection_files()
    
    # 4. نقل الملفات للمجلد الصحيح
    if inspection_files:
        if not move_inspections_to_correct_folder(inspection_files):
            return
    
    # 5. اختبار الرفع للمجلد الصحيح
    if not test_upload_to_correct_folder():
        return
    
    # 6. التحقق النهائي
    verify_correct_folder()
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح مجلد المعاينات بنجاح!")
    print("✅ جميع ملفات المعاينات الآن في المجلد الصحيح")
    print("✅ النظام يستخدم المجلد الصحيح للرفعات الجديدة")
    
    print("\n🔗 المجلدات الصحيحة:")
    print("📁 المعاينات: https://drive.google.com/drive/folders/1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")

if __name__ == "__main__":
    main()
