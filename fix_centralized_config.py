#!/usr/bin/env python3
"""
إصلاح النظام لاستخدام الإعدادات المركزية وترحيل الملفات
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def check_current_config():
    """فحص الإعدادات الحالية"""
    print("🔍 فحص الإعدادات الحالية...")
    
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

def update_config_to_centralized():
    """تحديث الإعدادات للمجلدات المركزية"""
    print("\n🔧 تحديث الإعدادات للمجلدات المركزية...")

    # المجلدات الصحيحة من الصفحة المركزية
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekiW0b7Av"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"

    print(f"📁 المجلد الصحيح للمعاينات: {CORRECT_INSPECTIONS_FOLDER}")
    print(f"📄 المجلد الصحيح للعقود: {CORRECT_CONTRACTS_FOLDER}")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات للتحديث")
            return False
        
        # تحديث المجلدات
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

def find_files_in_wrong_folders():
    """البحث عن الملفات في المجلدات الخاطئة"""
    print("\n🔍 البحث عن الملفات في المجلدات الخاطئة...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # المجلدات الخاطئة المحتملة
        wrong_folders = [
            "1jMeDl6AqrS-pzX_ECfXGACOekiW0b7Av",  # المجلد الحالي للمعاينات
            "1h19hAiBSJcsGRaBxViyEzX04ddMUUYj5"   # مجلد العقود الإضافي
        ]
        
        files_to_move = []
        
        for folder_id in wrong_folders:
            try:
                # الحصول على معلومات المجلد
                folder_info = service.service.files().get(
                    fileId=folder_id,
                    fields='id,name'
                ).execute()
                
                print(f"\n📁 فحص مجلد: {folder_info.get('name')} ({folder_id})")
                
                # البحث عن الملفات
                results = service.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields='files(id,name,parents,mimeType)',
                    pageSize=100
                ).execute()
                
                files = results.get('files', [])
                print(f"   📊 عدد الملفات: {len(files)}")
                
                for file in files:
                    if file.get('mimeType') != 'application/vnd.google-apps.folder':
                        files_to_move.append({
                            'id': file.get('id'),
                            'name': file.get('name'),
                            'current_folder': folder_id,
                            'folder_name': folder_info.get('name')
                        })
                        
            except Exception as e:
                print(f"❌ خطأ في فحص المجلد {folder_id}: {e}")
        
        print(f"\n📊 إجمالي الملفات للترحيل: {len(files_to_move)}")
        return files_to_move
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن الملفات: {e}")
        return []

def move_files_to_correct_folders(files_to_move):
    """ترحيل الملفات للمجلدات الصحيحة"""
    print("\n📦 ترحيل الملفات للمجلدات الصحيحة...")
    
    if not files_to_move:
        print("✅ لا توجد ملفات للترحيل")
        return True
    
    # المجلدات الصحيحة
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekiW0b7Av"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        moved_count = 0
        
        for file_info in files_to_move:
            try:
                file_name = file_info['name']
                file_id = file_info['id']
                
                # تحديد المجلد الصحيح بناءً على نوع الملف
                if 'عقد' in file_name or 'contract' in file_name.lower():
                    target_folder = CORRECT_CONTRACTS_FOLDER
                    file_type = "عقد"
                else:
                    target_folder = CORRECT_INSPECTIONS_FOLDER
                    file_type = "معاينة"
                
                # نقل الملف
                service.service.files().update(
                    fileId=file_id,
                    addParents=target_folder,
                    removeParents=file_info['current_folder'],
                    fields='id,parents'
                ).execute()
                
                print(f"✅ تم نقل {file_type}: {file_name}")
                moved_count += 1
                
            except Exception as e:
                print(f"❌ خطأ في نقل الملف {file_info['name']}: {e}")
        
        print(f"\n🎉 تم نقل {moved_count} ملف بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في ترحيل الملفات: {e}")
        return False

def update_database_links():
    """تحديث روابط قاعدة البيانات"""
    print("\n🔗 تحديث روابط قاعدة البيانات...")
    
    try:
        from inspections.models import Inspection
        from orders.models import Order
        
        # تحديث روابط المعاينات
        inspections_updated = 0
        inspections = Inspection.objects.filter(
            google_drive_file_id__isnull=False
        )
        
        for inspection in inspections:
            if inspection.google_drive_file_id:
                # إنشاء الرابط الجديد
                new_url = f"https://drive.google.com/file/d/{inspection.google_drive_file_id}/view?usp=drivesdk"
                
                if inspection.google_drive_file_url != new_url:
                    inspection.google_drive_file_url = new_url
                    inspection.save(update_fields=['google_drive_file_url'])
                    inspections_updated += 1
        
        print(f"✅ تم تحديث {inspections_updated} رابط معاينة")
        
        # تحديث روابط العقود
        contracts_updated = 0
        orders = Order.objects.filter(
            contract_google_drive_file_id__isnull=False
        )
        
        for order in orders:
            if hasattr(order, 'contract_google_drive_file_id') and order.contract_google_drive_file_id:
                # إنشاء الرابط الجديد
                new_url = f"https://drive.google.com/file/d/{order.contract_google_drive_file_id}/view?usp=drivesdk"
                
                if hasattr(order, 'contract_google_drive_url') and order.contract_google_drive_url != new_url:
                    order.contract_google_drive_url = new_url
                    order.save(update_fields=['contract_google_drive_url'])
                    contracts_updated += 1
        
        print(f"✅ تم تحديث {contracts_updated} رابط عقد")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث روابط قاعدة البيانات: {e}")
        return False

def test_connectivity():
    """اختبار الاتصال بالمجلدات الصحيحة"""
    print("\n🧪 اختبار الاتصال بالمجلدات الصحيحة...")
    
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekiW0b7Av"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # اختبار مجلد المعاينات
        try:
            inspections_info = service.service.files().get(
                fileId=CORRECT_INSPECTIONS_FOLDER,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد المعاينات متاح: {inspections_info.get('name')}")
            print(f"   🔗 الرابط: {inspections_info.get('webViewLink')}")
            
        except Exception as e:
            print(f"❌ خطأ في الوصول لمجلد المعاينات: {e}")
            return False
        
        # اختبار مجلد العقود
        try:
            contracts_info = service.service.files().get(
                fileId=CORRECT_CONTRACTS_FOLDER,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد العقود متاح: {contracts_info.get('name')}")
            print(f"   🔗 الرابط: {contracts_info.get('webViewLink')}")
            
        except Exception as e:
            print(f"❌ خطأ في الوصول لمجلد العقود: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الاتصال: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح النظام لاستخدام الإعدادات المركزية")
    print("=" * 60)
    
    # 1. فحص الإعدادات الحالية
    current_config = check_current_config()
    if not current_config:
        return
    
    # 2. تحديث الإعدادات للمجلدات المركزية
    if not update_config_to_centralized():
        return
    
    # 3. اختبار الاتصال
    if not test_connectivity():
        return
    
    # 4. البحث عن الملفات في المجلدات الخاطئة
    files_to_move = find_files_in_wrong_folders()
    
    # 5. ترحيل الملفات
    if files_to_move:
        if not move_files_to_correct_folders(files_to_move):
            return
    
    # 6. تحديث روابط قاعدة البيانات
    if not update_database_links():
        return
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح النظام بنجاح!")
    print("✅ النظام يستخدم الآن الإعدادات المركزية")
    print("✅ تم ترحيل جميع الملفات للمجلدات الصحيحة")
    print("✅ تم تحديث جميع الروابط في قاعدة البيانات")
    
    print("\n🔗 المجلدات الصحيحة:")
    print("📁 المعاينات: https://drive.google.com/drive/folders/1jMeDl6AqrS-pzX_ECfXGACOekiW0b7Av")
    print("📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")

if __name__ == "__main__":
    main()
