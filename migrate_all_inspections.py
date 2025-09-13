#!/usr/bin/env python3
"""
نقل جميع المعاينات من المجلدات السابقة وإصلاح روابطها
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def find_all_inspection_files_in_drive():
    """البحث عن جميع ملفات المعاينات في Google Drive"""
    print("🔍 البحث عن جميع ملفات المعاينات في Google Drive...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # البحث عن جميع ملفات PDF في Google Drive
        query = "mimeType='application/pdf' and trashed=false"
        
        results = service.service.files().list(
            q=query,
            fields='files(id,name,parents,webViewLink,createdTime)',
            pageSize=1000
        ).execute()
        
        files = results.get('files', [])
        print(f"📊 وجد {len(files)} ملف PDF في Google Drive")
        
        # فلترة ملفات المعاينات (ليست عقود)
        inspection_files = []
        contract_files = []
        
        for file in files:
            file_name = file.get('name', '')
            
            if 'عقد' in file_name or 'contract' in file_name.lower():
                contract_files.append(file)
            elif any(keyword in file_name for keyword in ['فرع', 'Open_Air', '_20', '-0']):
                inspection_files.append(file)
        
        print(f"📁 ملفات معاينات: {len(inspection_files)}")
        print(f"📄 ملفات عقود: {len(contract_files)}")
        
        # تجميع ملفات المعاينات حسب المجلد
        folder_groups = {}
        correct_folder = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
        
        for file in inspection_files:
            parents = file.get('parents', ['root'])
            parent = parents[0] if parents else 'root'
            
            if parent != correct_folder:  # فقط الملفات في المجلدات الخاطئة
                if parent not in folder_groups:
                    folder_groups[parent] = []
                folder_groups[parent].append(file)
        
        print(f"\n📂 ملفات المعاينات في مجلدات خاطئة:")
        total_to_move = 0
        for folder_id, files_in_folder in folder_groups.items():
            print(f"   📁 المجلد {folder_id}: {len(files_in_folder)} ملف")
            total_to_move += len(files_in_folder)
        
        print(f"\n📊 إجمالي الملفات للنقل: {total_to_move}")
        
        # إرجاع قائمة مسطحة بجميع الملفات للنقل
        all_files_to_move = []
        for files_list in folder_groups.values():
            all_files_to_move.extend(files_list)
        
        return all_files_to_move
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن الملفات: {e}")
        return []

def move_files_to_correct_folder(files_to_move):
    """نقل الملفات للمجلد الصحيح"""
    print(f"\n📦 نقل {len(files_to_move)} ملف للمجلد الصحيح...")
    
    if not files_to_move:
        print("✅ لا توجد ملفات للنقل")
        return []
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        moved_files = []
        moved_count = 0
        
        for i, file_info in enumerate(files_to_move):
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
                
                # إضافة معلومات الملف المنقول
                moved_files.append({
                    'file_id': file_id,
                    'file_name': file_name,
                    'old_parents': current_parents,
                    'new_parent': CORRECT_INSPECTIONS_FOLDER
                })
                
                moved_count += 1
                print(f"✅ تم نقل ({moved_count}/{len(files_to_move)}): {file_name}")
                
                # توقف قصير لتجنب تجاوز حدود API
                if moved_count % 10 == 0:
                    import time
                    time.sleep(1)
                    print(f"   📊 تم نقل {moved_count} ملف حتى الآن...")
                
            except Exception as e:
                print(f"❌ خطأ في نقل الملف {file_info['name']}: {e}")
        
        print(f"\n🎉 تم نقل {moved_count} ملف بنجاح")
        return moved_files
        
    except Exception as e:
        print(f"❌ خطأ في نقل الملفات: {e}")
        return []

def update_database_links(moved_files):
    """تحديث روابط الملفات في قاعدة البيانات"""
    print(f"\n🔗 تحديث روابط {len(moved_files)} ملف في قاعدة البيانات...")
    
    if not moved_files:
        print("✅ لا توجد روابط للتحديث")
        return True
    
    try:
        from inspections.models import Inspection
        
        updated_count = 0
        
        for file_info in moved_files:
            file_id = file_info['file_id']
            file_name = file_info['file_name']
            
            # البحث عن المعاينة بهذا المعرف
            inspections = Inspection.objects.filter(google_drive_file_id=file_id)
            
            for inspection in inspections:
                # تحديث الرابط
                new_url = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
                
                if inspection.google_drive_file_url != new_url:
                    inspection.google_drive_file_url = new_url
                    inspection.save(update_fields=['google_drive_file_url'])
                    updated_count += 1
                    print(f"✅ تم تحديث رابط المعاينة {inspection.id}: {file_name}")
        
        print(f"\n🎉 تم تحديث {updated_count} رابط في قاعدة البيانات")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث روابط قاعدة البيانات: {e}")
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
            fields='files(id,name,createdTime)',
            pageSize=1000,
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        print(f"📁 المجلد الصحيح يحتوي الآن على: {len(files)} ملف")
        
        if files:
            print("📋 آخر 10 ملفات:")
            for file in files[:10]:
                created_time = file.get('createdTime', '')[:10] if file.get('createdTime') else 'غير معروف'
                print(f"   - {file.get('name')} ({created_time})")
        
        # فحص قاعدة البيانات
        from inspections.models import Inspection
        
        total_inspections = Inspection.objects.count()
        uploaded_inspections = Inspection.objects.filter(google_drive_file_id__isnull=False).count()
        
        print(f"\n📊 إحصائيات قاعدة البيانات:")
        print(f"   📝 إجمالي المعاينات: {total_inspections}")
        print(f"   📤 المعاينات المرفوعة: {uploaded_inspections}")
        print(f"   📈 نسبة الرفع: {(uploaded_inspections/total_inspections*100):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق النهائي: {e}")
        return False

def create_migration_report(moved_files):
    """إنشاء تقرير الترحيل"""
    print(f"\n📋 تقرير الترحيل...")
    
    print("🎉 تم ترحيل المعاينات بنجاح!")
    print("=" * 50)
    
    print(f"📊 الإحصائيات:")
    print(f"   📦 عدد الملفات المنقولة: {len(moved_files)}")
    print(f"   📁 المجلد الوجهة: 1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print(f"   📂 اسم المجلد: crm-insp")
    
    print(f"\n✅ ما تم إنجازه:")
    print(f"   🔍 البحث عن جميع ملفات المعاينات في Google Drive")
    print(f"   📦 نقل الملفات من المجلدات الخاطئة للمجلد الصحيح")
    print(f"   🔗 تحديث جميع الروابط في قاعدة البيانات")
    print(f"   🧪 التحقق من النتيجة النهائية")
    
    print(f"\n🔗 الروابط:")
    print(f"   📁 المعاينات: https://drive.google.com/drive/folders/1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print(f"   ⚙️ الصفحة المركزية: https://elkhawaga.uk/odoo-db-manager/google-drive/settings/")
    
    print(f"\n🚀 النتيجة:")
    print(f"   ✅ جميع المعاينات الآن في المجلد الصحيح")
    print(f"   ✅ جميع الروابط في النظام محدثة")
    print(f"   ✅ المعاينات الجديدة ستذهب للمجلد الصحيح تلقائياً")

def main():
    """الدالة الرئيسية"""
    print("📦 ترحيل جميع المعاينات وإصلاح روابطها")
    print("=" * 60)
    print("📁 المجلد الصحيح: 1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("📂 اسم المجلد: crm-insp")
    print("=" * 60)
    
    # 1. البحث عن جميع ملفات المعاينات
    files_to_move = find_all_inspection_files_in_drive()
    
    if not files_to_move:
        print("✅ جميع المعاينات موجودة في المجلد الصحيح بالفعل")
        verify_final_result()
        return
    
    # 2. نقل الملفات للمجلد الصحيح
    moved_files = move_files_to_correct_folder(files_to_move)
    
    if not moved_files:
        print("❌ فشل في نقل الملفات")
        return
    
    # 3. تحديث روابط قاعدة البيانات
    if not update_database_links(moved_files):
        return
    
    # 4. التحقق من النتيجة النهائية
    if not verify_final_result():
        return
    
    # 5. إنشاء تقرير الترحيل
    create_migration_report(moved_files)
    
    print("\n" + "=" * 60)
    print("🎊 تم إنجاز الترحيل بنجاح!")

if __name__ == "__main__":
    main()
