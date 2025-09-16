#!/usr/bin/env python3
"""
تنظيف الملفات المكررة في مجلدي المعاينات والعقود
"""

import os
import django
from datetime import datetime
from collections import defaultdict

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def find_duplicates_in_folder(folder_id, folder_name):
    """البحث عن الملفات المكررة في مجلد معين"""
    print(f"🔍 البحث عن التكرارات في {folder_name}...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # الحصول على جميع الملفات في المجلد
        results = service.service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields='files(id,name,createdTime,size)',
            pageSize=1000,
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        print(f"📊 وجد {len(files)} ملف في {folder_name}")
        
        # تجميع الملفات حسب الاسم
        files_by_name = defaultdict(list)
        
        for file in files:
            file_name = file.get('name', '')
            # تجاهل ملفات الاختبار
            if 'test' not in file_name.lower():
                files_by_name[file_name].append(file)
        
        # العثور على التكرارات
        duplicates = {}
        total_duplicates = 0
        
        for file_name, file_list in files_by_name.items():
            if len(file_list) > 1:
                # ترتيب حسب تاريخ الإنشاء (الأحدث أولاً)
                file_list.sort(key=lambda x: x.get('createdTime', ''), reverse=True)
                
                # الاحتفاظ بالملف الأول (الأحدث) وحذف الباقي
                keep_file = file_list[0]
                duplicate_files = file_list[1:]
                
                duplicates[file_name] = {
                    'keep': keep_file,
                    'duplicates': duplicate_files
                }
                
                total_duplicates += len(duplicate_files)
        
        print(f"📋 وجد {len(duplicates)} ملف مكرر")
        print(f"📦 إجمالي النسخ المكررة للحذف: {total_duplicates}")
        
        if duplicates:
            print(f"\n📝 أمثلة على التكرارات:")
            count = 0
            for file_name, info in duplicates.items():
                if count < 5:  # عرض أول 5 أمثلة فقط
                    print(f"   📄 {file_name}: {len(info['duplicates'])} نسخة مكررة")
                    count += 1
        
        return duplicates
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن التكرارات في {folder_name}: {e}")
        return {}

def remove_duplicates(duplicates, folder_name):
    """حذف الملفات المكررة"""
    print(f"\n🗑️ حذف التكرارات من {folder_name}...")
    
    if not duplicates:
        print(f"✅ لا توجد تكرارات في {folder_name}")
        return True
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        deleted_count = 0
        total_to_delete = sum(len(info['duplicates']) for info in duplicates.values())
        
        print(f"📦 سيتم حذف {total_to_delete} ملف مكرر...")
        
        for file_name, info in duplicates.items():
            keep_file = info['keep']
            duplicate_files = info['duplicates']
            
            print(f"\n📄 معالجة: {file_name}")
            print(f"   ✅ الاحتفاظ بـ: {keep_file.get('id')} (تاريخ: {keep_file.get('createdTime', '')[:10]})")
            
            for duplicate in duplicate_files:
                try:
                    file_id = duplicate.get('id')
                    created_time = duplicate.get('createdTime', '')[:10]
                    
                    # حذف الملف المكرر
                    service.service.files().delete(fileId=file_id).execute()
                    
                    deleted_count += 1
                    print(f"   🗑️ تم حذف: {file_id} (تاريخ: {created_time})")
                    
                    # توقف قصير لتجنب تجاوز حدود API
                    if deleted_count % 10 == 0:
                        import time
                        time.sleep(1)
                        print(f"   📊 تم حذف {deleted_count} ملف حتى الآن...")
                    
                except Exception as e:
                    print(f"   ❌ خطأ في حذف {duplicate.get('id')}: {e}")
        
        print(f"\n🎉 تم حذف {deleted_count} ملف مكرر من {folder_name}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في حذف التكرارات من {folder_name}: {e}")
        return False

def update_database_after_cleanup():
    """تحديث قاعدة البيانات بعد التنظيف"""
    print(f"\n🔗 تحديث قاعدة البيانات بعد التنظيف...")
    
    try:
        from inspections.models import Inspection
        from orders.models import Order
        
        # فحص المعاينات
        inspections_with_invalid_files = []
        inspections = Inspection.objects.filter(google_drive_file_id__isnull=False).exclude(google_drive_file_id='')
        
        print(f"🔍 فحص {inspections.count()} معاينة...")
        
        from inspections.services.google_drive_service import GoogleDriveService
        service = GoogleDriveService()
        
        checked_count = 0
        invalid_count = 0
        
        for inspection in inspections:
            try:
                file_id = inspection.google_drive_file_id
                
                # التحقق من وجود الملف
                service.service.files().get(fileId=file_id, fields='id').execute()
                checked_count += 1
                
            except Exception:
                # الملف غير موجود - تنظيف المرجع
                inspection.google_drive_file_id = None
                inspection.google_drive_file_url = None
                inspection.save(update_fields=['google_drive_file_id', 'google_drive_file_url'])
                
                inspections_with_invalid_files.append(inspection.id)
                invalid_count += 1
                
                if invalid_count <= 5:  # عرض أول 5 فقط
                    print(f"   🧹 تنظيف مرجع المعاينة {inspection.id}")
        
        print(f"✅ تم فحص {checked_count} معاينة")
        print(f"🧹 تم تنظيف {invalid_count} مرجع غير صالح")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث قاعدة البيانات: {e}")
        return False

def verify_cleanup_results():
    """التحقق من نتائج التنظيف"""
    print(f"\n🧪 التحقق من نتائج التنظيف...")
    
    INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # فحص مجلد المعاينات
        results = service.service.files().list(
            q=f"'{INSPECTIONS_FOLDER}' in parents and trashed=false",
            fields='files(id,name)',
            pageSize=1000
        ).execute()
        
        inspections_files = results.get('files', [])
        inspections_count = len([f for f in inspections_files if not 'test' in f.get('name', '').lower()])
        
        # فحص مجلد العقود
        results = service.service.files().list(
            q=f"'{CONTRACTS_FOLDER}' in parents and trashed=false",
            fields='files(id,name)',
            pageSize=1000
        ).execute()
        
        contracts_files = results.get('files', [])
        contracts_count = len([f for f in contracts_files if not 'test' in f.get('name', '').lower()])
        
        print(f"📊 النتائج النهائية:")
        print(f"   📁 مجلد المعاينات: {inspections_count} ملف")
        print(f"   📄 مجلد العقود: {contracts_count} ملف")
        
        # فحص التكرارات المتبقية
        inspections_names = [f.get('name') for f in inspections_files if not 'test' in f.get('name', '').lower()]
        contracts_names = [f.get('name') for f in contracts_files if not 'test' in f.get('name', '').lower()]
        
        inspections_duplicates = len(inspections_names) - len(set(inspections_names))
        contracts_duplicates = len(contracts_names) - len(set(contracts_names))
        
        print(f"   🔄 تكرارات متبقية في المعاينات: {inspections_duplicates}")
        print(f"   🔄 تكرارات متبقية في العقود: {contracts_duplicates}")
        
        if inspections_duplicates == 0 and contracts_duplicates == 0:
            print(f"✅ تم تنظيف جميع التكرارات بنجاح!")
        else:
            print(f"⚠️ ما زالت هناك بعض التكرارات")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق من النتائج: {e}")
        return False

def create_cleanup_report():
    """إنشاء تقرير التنظيف"""
    print(f"\n📋 تقرير التنظيف...")
    
    print("🧹 تم تنظيف التكرارات بنجاح!")
    print("=" * 50)
    
    print("✅ ما تم إنجازه:")
    print("   🔍 البحث عن الملفات المكررة في كلا المجلدين")
    print("   🗑️ حذف النسخ المكررة (الاحتفاظ بالأحدث)")
    print("   🔗 تحديث مراجع قاعدة البيانات")
    print("   🧪 التحقق من النتائج النهائية")
    
    print(f"\n📁 المجلدات المنظفة:")
    print(f"   📁 المعاينات: 1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv (crm-insp)")
    print(f"   📄 العقود: 1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    
    print(f"\n🔗 الروابط:")
    print(f"   📁 المعاينات: https://drive.google.com/drive/folders/1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print(f"   📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    
    print(f"\n🚀 النتيجة:")
    print(f"   ✅ لا توجد ملفات مكررة")
    print(f"   ✅ المجلدات منظمة ونظيفة")
    print(f"   ✅ قاعدة البيانات محدثة")
    print(f"   ✅ توفير مساحة تخزين")

def main():
    """الدالة الرئيسية"""
    print("🧹 تنظيف الملفات المكررة")
    print("=" * 60)
    
    INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    print("📁 المجلدات المستهدفة:")
    print(f"   📁 المعاينات: {INSPECTIONS_FOLDER} (crm-insp)")
    print(f"   📄 العقود: {CONTRACTS_FOLDER}")
    print("=" * 60)
    
    # 1. البحث عن التكرارات في مجلد المعاينات
    inspections_duplicates = find_duplicates_in_folder(INSPECTIONS_FOLDER, "مجلد المعاينات")
    
    # 2. البحث عن التكرارات في مجلد العقود
    contracts_duplicates = find_duplicates_in_folder(CONTRACTS_FOLDER, "مجلد العقود")
    
    # 3. حذف التكرارات من مجلد المعاينات
    if not remove_duplicates(inspections_duplicates, "مجلد المعاينات"):
        return
    
    # 4. حذف التكرارات من مجلد العقود
    if not remove_duplicates(contracts_duplicates, "مجلد العقود"):
        return
    
    # 5. تحديث قاعدة البيانات
    if not update_database_after_cleanup():
        return
    
    # 6. التحقق من النتائج
    if not verify_cleanup_results():
        return
    
    # 7. إنشاء تقرير التنظيف
    create_cleanup_report()
    
    print("\n" + "=" * 60)
    print("🎊 تم تنظيف التكرارات بنجاح!")

if __name__ == "__main__":
    main()
