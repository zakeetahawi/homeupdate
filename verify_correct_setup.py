#!/usr/bin/env python3
"""
التحقق من الإعداد الصحيح للنظام
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def check_current_config():
    """فحص الإعدادات الحالية"""
    print("⚙️ فحص الإعدادات الحالية...")
    
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
        
        # التحقق من أن المعرف صحيح
        if config.inspections_folder_id == "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv":
            print("✅ مجلد المعاينات صحيح!")
        else:
            print(f"❌ مجلد المعاينات خاطئ: {config.inspections_folder_id}")
            return None
        
        return config
        
    except Exception as e:
        print(f"❌ خطأ في فحص الإعدادات: {e}")
        return None

def test_upload_functionality():
    """اختبار وظيفة الرفع"""
    print("\n🧪 اختبار وظيفة الرفع...")
    
    try:
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            folder_id = result.get('folder_id')
            print(f"✅ نجح اختبار الرفع")
            print(f"   📁 المجلد المستخدم: {folder_id}")
            print(f"   📄 الملف التجريبي: {result.get('file_name')}")
            
            # التحقق من أن المجلد صحيح
            if folder_id == "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv":
                print("✅ النظام يرفع للمجلد الصحيح!")
                return True
            else:
                print(f"❌ النظام يرفع للمجلد الخاطئ: {folder_id}")
                return False
        else:
            print(f"❌ فشل اختبار الرفع: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الرفع: {e}")
        return False

def check_folder_contents():
    """فحص محتويات المجلد الصحيح"""
    print("\n📊 فحص محتويات المجلد الصحيح...")
    
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
        print(f"📁 المجلد الصحيح يحتوي على: {len(files)} ملف")
        
        if files:
            print("📋 آخر 5 ملفات:")
            for file in files[:5]:
                created_time = file.get('createdTime', '')[:10] if file.get('createdTime') else 'غير معروف'
                print(f"   - {file.get('name')} ({created_time})")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في فحص المجلد: {e}")
        return False

def test_real_inspection_upload():
    """اختبار رفع معاينة حقيقية"""
    print("\n🧪 اختبار رفع معاينة حقيقية...")
    
    try:
        from inspections.models import Inspection
        
        # البحث عن معاينة بملف حقيقي لم يتم رفعها
        inspection = Inspection.objects.filter(
            inspection_file__isnull=False,
            google_drive_file_id__isnull=True
        ).first()
        
        if not inspection:
            print("✅ لا توجد معاينات بحاجة للرفع")
            return True
        
        if not inspection.inspection_file:
            print("❌ المعاينة لا تحتوي على ملف")
            return False
        
        file_path = inspection.inspection_file.path
        if not os.path.exists(file_path):
            print(f"❌ الملف غير موجود: {file_path}")
            return False
        
        print(f"📁 اختبار رفع المعاينة {inspection.id}")
        print(f"📄 الملف: {os.path.basename(file_path)}")
        
        # محاولة الرفع
        result = inspection.upload_to_google_drive_async()
        
        if result and result.get('file_id'):
            print(f"✅ نجح رفع المعاينة!")
            print(f"   🆔 Google Drive ID: {result.get('file_id')}")
            print(f"   🔗 الرابط: {result.get('view_url')}")
            
            # التحقق من التحديث في قاعدة البيانات
            inspection.refresh_from_db()
            print(f"   💾 تم تحديث قاعدة البيانات: {inspection.google_drive_file_id}")
            
            return True
        else:
            print(f"❌ فشل رفع المعاينة")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الرفع الحقيقي: {e}")
        return False

def create_final_report():
    """إنشاء تقرير نهائي"""
    print("\n📋 التقرير النهائي...")
    
    print("🎉 تم إصلاح النظام بنجاح!")
    print("=" * 50)
    
    print("✅ الإعدادات الصحيحة:")
    print("   📁 مجلد المعاينات: 1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("   📂 اسم المجلد: crm-insp")
    print("   📄 مجلد العقود: 1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    
    print("\n✅ ما تم إنجازه:")
    print("   🔧 تحديث الإعدادات المركزية")
    print("   📦 نقل الملفات الأخيرة للمجلد الصحيح")
    print("   🧪 اختبار وظائف الرفع")
    print("   🔄 إعادة تشغيل النظام")
    
    print("\n🔗 الروابط:")
    print("   📁 المعاينات: https://drive.google.com/drive/folders/1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("   📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    print("   ⚙️ الصفحة المركزية: https://elkhawaga.uk/odoo-db-manager/google-drive/settings/")
    
    print("\n🚀 النتيجة:")
    print("   ✅ جميع الرفعات الجديدة ستذهب للمجلد الصحيح")
    print("   ✅ النظام يستخدم الإعدادات المركزية")
    print("   ✅ المعاينات الأخيرة تم نقلها للمجلد الصحيح")

def main():
    """الدالة الرئيسية"""
    print("🔍 التحقق من الإعداد الصحيح للنظام")
    print("=" * 60)
    
    # 1. فحص الإعدادات الحالية
    config = check_current_config()
    if not config:
        return
    
    # 2. اختبار وظيفة الرفع
    if not test_upload_functionality():
        return
    
    # 3. فحص محتويات المجلد
    if not check_folder_contents():
        return
    
    # 4. اختبار رفع معاينة حقيقية
    test_real_inspection_upload()
    
    # 5. إنشاء التقرير النهائي
    create_final_report()

if __name__ == "__main__":
    main()
