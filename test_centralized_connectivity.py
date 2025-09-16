#!/usr/bin/env python3
"""
اختبار الاتصال من الصفحة المركزية
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def test_inspections_folder_connectivity():
    """اختبار الاتصال بمجلد المعاينات"""
    print("🧪 اختبار الاتصال بمجلد المعاينات...")
    
    try:
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار مجلد المعاينات")
            print(f"   📁 المجلد: {result.get('folder_id')}")
            print(f"   📄 الملف التجريبي: {result.get('file_name')}")
            print(f"   💬 الرسالة: {result.get('message')}")
        else:
            print(f"❌ فشل اختبار مجلد المعاينات")
            print(f"   💬 الرسالة: {result.get('message')}")
            
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ خطأ في اختبار مجلد المعاينات: {e}")
        return False

def test_contracts_folder_connectivity():
    """اختبار الاتصال بمجلد العقود"""
    print("\n🧪 اختبار الاتصال بمجلد العقود...")
    
    try:
        from orders.services.google_drive_service import test_contract_file_upload_to_folder
        
        result = test_contract_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار مجلد العقود")
            print(f"   📁 المجلد: {result.get('folder_id')}")
            print(f"   📄 الملف التجريبي: {result.get('file_name')}")
            print(f"   💬 الرسالة: {result.get('message')}")
        else:
            print(f"❌ فشل اختبار مجلد العقود")
            print(f"   💬 الرسالة: {result.get('message')}")
            
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ خطأ في اختبار مجلد العقود: {e}")
        return False

def test_upload_real_file():
    """اختبار رفع ملف حقيقي"""
    print("\n🧪 اختبار رفع ملف معاينة حقيقي...")
    
    try:
        from inspections.models import Inspection
        
        # البحث عن معاينة بملف حقيقي
        inspection = Inspection.objects.filter(
            inspection_file__isnull=False,
            google_drive_file_id__isnull=True
        ).first()
        
        if not inspection:
            print("❌ لا توجد معاينات بملفات للاختبار")
            return False
        
        if not inspection.inspection_file:
            print("❌ المعاينة لا تحتوي على ملف")
            return False
        
        file_path = inspection.inspection_file.path
        if not os.path.exists(file_path):
            print(f"❌ الملف غير موجود: {file_path}")
            return False
        
        print(f"📁 اختبار رفع المعاينة {inspection.id}")
        print(f"📄 الملف: {os.path.basename(file_path)}")
        print(f"📊 الحجم: {os.path.getsize(file_path):,} bytes")
        
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
        print(f"❌ خطأ في اختبار الرفع: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_folder_contents():
    """التحقق من محتويات المجلدات"""
    print("\n📊 التحقق من محتويات المجلدات...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # فحص مجلد المعاينات
        inspections_folder = service.config.inspections_folder_id
        print(f"\n📁 مجلد المعاينات: {inspections_folder}")
        
        results = service.service.files().list(
            q=f"'{inspections_folder}' in parents and trashed=false",
            fields='files(id,name,size)',
            pageSize=10,
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        print(f"   📊 عدد الملفات: {len(files)}")
        
        if files:
            print("   📋 آخر 5 ملفات:")
            for file in files[:5]:
                size = int(file.get('size', 0)) if file.get('size') else 0
                size_mb = size / (1024 * 1024) if size > 0 else 0
                print(f"      - {file.get('name')} ({size_mb:.1f} MB)")
        
        # فحص مجلد العقود
        contracts_folder = service.config.contracts_folder_id
        print(f"\n📄 مجلد العقود: {contracts_folder}")
        
        results = service.service.files().list(
            q=f"'{contracts_folder}' in parents and trashed=false",
            fields='files(id,name,size)',
            pageSize=10,
            orderBy='createdTime desc'
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
        print(f"❌ خطأ في فحص المحتويات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🧪 اختبار شامل للاتصال بالإعدادات المركزية")
    print("=" * 60)
    
    # اختبار الاتصال بمجلد المعاينات
    inspections_test = test_inspections_folder_connectivity()
    
    # اختبار الاتصال بمجلد العقود
    contracts_test = test_contracts_folder_connectivity()
    
    # اختبار رفع ملف حقيقي
    real_upload_test = test_upload_real_file()
    
    # التحقق من محتويات المجلدات
    contents_check = verify_folder_contents()
    
    print("\n" + "=" * 60)
    print("🎯 نتائج الاختبارات:")
    
    print(f"📁 اختبار مجلد المعاينات: {'✅ نجح' if inspections_test else '❌ فشل'}")
    print(f"📄 اختبار مجلد العقود: {'✅ نجح' if contracts_test else '❌ فشل'}")
    print(f"📤 اختبار رفع ملف حقيقي: {'✅ نجح' if real_upload_test else '❌ فشل'}")
    print(f"📊 فحص محتويات المجلدات: {'✅ نجح' if contents_check else '❌ فشل'}")
    
    all_tests_passed = all([inspections_test, contracts_test, real_upload_test, contents_check])
    
    if all_tests_passed:
        print("\n🎉 جميع الاختبارات نجحت!")
        print("✅ النظام يستخدم الإعدادات المركزية بشكل صحيح")
        print("✅ يمكن الوصول للمجلدات والرفع إليها")
        print("✅ الصفحة المركزية تعمل بشكل مثالي")
    else:
        print("\n⚠️ بعض الاختبارات فشلت")
        print("🔧 قد تحتاج لمراجعة الإعدادات")
    
    print("\n🔗 روابط المجلدات:")
    print("📁 المعاينات: https://drive.google.com/drive/folders/1jMeDl6AqrS-pzX_ECfXGACOekiW0b7Av")
    print("📄 العقود: https://drive.google.com/drive/folders/1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG")
    print("⚙️ الصفحة المركزية: https://elkhawaga.uk/odoo-db-manager/google-drive/settings/")

if __name__ == "__main__":
    main()
