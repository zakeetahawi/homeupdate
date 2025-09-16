#!/usr/bin/env python3
"""
إصلاح معرف المجلد الصحيح
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def update_to_correct_folders():
    """تحديث الإعدادات للمجلدات الصحيحة"""
    print("🔧 تحديث الإعدادات للمجلدات الصحيحة...")
    
    # المعرف الصحيح من النتائج السابقة
    CORRECT_INSPECTIONS_FOLDER = "1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    print(f"📁 مجلد المعاينات: {CORRECT_INSPECTIONS_FOLDER}")
    print(f"📄 مجلد العقود: {CORRECT_CONTRACTS_FOLDER}")
    
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

def test_access():
    """اختبار الوصول للمجلدات"""
    print("\n🧪 اختبار الوصول للمجلدات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        config = service.config
        
        print(f"📁 مجلد المعاينات في الإعدادات: {config.inspections_folder_id}")
        print(f"📄 مجلد العقود في الإعدادات: {config.contracts_folder_id}")
        
        # اختبار مجلد المعاينات
        try:
            inspections_info = service.service.files().get(
                fileId=config.inspections_folder_id,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد المعاينات متاح: {inspections_info.get('name')}")
            print(f"   🔗 الرابط: {inspections_info.get('webViewLink')}")
            
        except Exception as e:
            print(f"❌ خطأ في مجلد المعاينات: {e}")
            return False
        
        # اختبار مجلد العقود
        try:
            contracts_info = service.service.files().get(
                fileId=config.contracts_folder_id,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"✅ مجلد العقود متاح: {contracts_info.get('name')}")
            print(f"   🔗 الرابط: {contracts_info.get('webViewLink')}")
            
        except Exception as e:
            print(f"❌ خطأ في مجلد العقود: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الوصول: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح معرف المجلد الصحيح")
    print("=" * 60)
    
    # 1. تحديث الإعدادات
    if not update_to_correct_folders():
        return
    
    # 2. اختبار الوصول
    if not test_access():
        print("\n❌ فشل في الوصول للمجلدات")
        print("💡 يرجى التأكد من المعرف الصحيح للمجلد")
        return
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح الإعدادات بنجاح!")

if __name__ == "__main__":
    main()
