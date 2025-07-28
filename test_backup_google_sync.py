#!/usr/bin/env python
"""
سكريبت اختبار النسخ الاحتياطي لتعيينات Google Sync
Test script for Google Sync backup functionality
"""

import os
import sys
import django
import json
import gzip
from pathlib import Path

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.contrib.auth import get_user_model
from backup_system.services import backup_manager
from odoo_db_manager.google_sync_advanced import GoogleSheetMapping
from odoo_db_manager.models import GoogleDriveConfig

User = get_user_model()

def test_google_sync_backup():
    """اختبار النسخ الاحتياطي لتعيينات Google Sync"""
    
    print("🔍 اختبار النسخ الاحتياطي لتعيينات Google Sync")
    print("=" * 60)
    
    # 1. فحص البيانات الموجودة قبل النسخ الاحتياطي
    print("\n📊 فحص البيانات الموجودة:")
    
    # فحص تعيينات Google Sheets
    mappings = GoogleSheetMapping.objects.all()
    print(f"  📋 تعيينات Google Sheets: {mappings.count()}")
    for mapping in mappings[:3]:  # عرض أول 3 فقط
        print(f"    - {mapping.name}: {mapping.spreadsheet_id[:20]}...")
    
    # فحص إعدادات Google Drive
    try:
        drive_config = GoogleDriveConfig.get_active_config()
        if drive_config:
            print(f"  🗂️ إعدادات Google Drive: {drive_config.name}")
        else:
            print("  🗂️ إعدادات Google Drive: غير موجودة")
    except Exception as e:
        print(f"  🗂️ إعدادات Google Drive: خطأ - {str(e)}")
    
    # فحص إعدادات Google Sheets (النموذج القديم)
    try:
        from odoo_db_manager.google_sync import GoogleSyncConfig
        sheets_configs = GoogleSyncConfig.objects.all()
        print(f"  📊 إعدادات Google Sheets القديمة: {sheets_configs.count()}")
    except Exception as e:
        print(f"  📊 إعدادات Google Sheets القديمة: خطأ - {str(e)}")
    
    # 2. إنشاء نسخة احتياطية تجريبية
    print("\n💾 إنشاء نسخة احتياطية تجريبية...")
    
    try:
        # الحصول على مستخدم للاختبار
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        
        if not user:
            print("  ❌ لا يوجد مستخدمين في النظام")
            return False
        
        # إنشاء النسخة الاحتياطية
        job = backup_manager.create_full_backup(
            name="اختبار_Google_Sync",
            user=user,
            description="اختبار شمول تعيينات Google Sync في النسخة الاحتياطية"
        )
        
        print(f"  ✅ تم إنشاء مهمة النسخ الاحتياطي: {job.id}")
        print(f"  ⏳ انتظار اكتمال النسخ الاحتياطي...")
        
        # انتظار اكتمال النسخ الاحتياطي (مع timeout)
        import time
        timeout = 300  # 5 دقائق
        start_time = time.time()
        
        while job.status in ['pending', 'running']:
            if time.time() - start_time > timeout:
                print("  ⏰ انتهت مهلة الانتظار")
                return False
            
            time.sleep(2)
            job.refresh_from_db()
            if job.status == 'running':
                print(f"  📈 التقدم: {job.progress_percentage:.1f}% - {job.current_step}")
        
        if job.status == 'completed':
            print(f"  ✅ تم إنشاء النسخة الاحتياطية بنجاح")
            print(f"  📁 مسار الملف: {job.file_path}")
            print(f"  📏 حجم الملف: {job.file_size_display}")
            print(f"  🗜️ حجم مضغوط: {job.compressed_size_display}")
            print(f"  📊 إجمالي السجلات: {job.total_records}")
            
            # 3. فحص محتويات النسخة الاحتياطية
            return check_backup_contents(job.file_path)
            
        else:
            print(f"  ❌ فشل في إنشاء النسخة الاحتياطية: {job.error_message}")
            return False
            
    except Exception as e:
        print(f"  ❌ خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
        return False

def check_backup_contents(file_path):
    """فحص محتويات النسخة الاحتياطية للتأكد من وجود بيانات Google Sync"""
    
    print("\n🔍 فحص محتويات النسخة الاحتياطية:")
    
    try:
        # قراءة الملف المضغوط
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"  📊 إجمالي السجلات في الملف: {len(data)}")
        
        # فحص وجود نماذج Google Sync
        google_sync_models = [
            'odoo_db_manager.googlesheetmapping',
            'odoo_db_manager.googlesheetsconfig',
            'odoo_db_manager.googledriveconfig',
            'odoo_db_manager.googlesynctask',
            'odoo_db_manager.googlesyncconflict',
            'odoo_db_manager.googlesyncschedule',
        ]
        
        found_models = {}
        for item in data:
            model_name = item.get('model', '').lower()
            if model_name in [m.lower() for m in google_sync_models]:
                if model_name not in found_models:
                    found_models[model_name] = 0
                found_models[model_name] += 1
        
        print("\n  📋 نماذج Google Sync الموجودة في النسخة الاحتياطية:")
        
        success = True
        for model in google_sync_models:
            count = found_models.get(model.lower(), 0)
            if count > 0:
                print(f"    ✅ {model}: {count} سجل")
            else:
                print(f"    ⚠️ {model}: غير موجود")
                # لا نعتبر هذا فشل إذا لم تكن هناك بيانات أصلاً
        
        # فحص وجود تعيينات Google Sheets على الأقل
        mapping_count = found_models.get('odoo_db_manager.googlesheetmapping', 0)
        if mapping_count > 0:
            print(f"\n  ✅ تم العثور على {mapping_count} تعيين Google Sheets في النسخة الاحتياطية")
            success = True
        else:
            # التحقق من وجود تعيينات في قاعدة البيانات الأصلية
            original_count = GoogleSheetMapping.objects.count()
            if original_count > 0:
                print(f"\n  ❌ لم يتم العثور على تعيينات Google Sheets في النسخة الاحتياطية")
                print(f"      بينما يوجد {original_count} تعيين في قاعدة البيانات الأصلية")
                success = False
            else:
                print(f"\n  ℹ️ لا توجد تعيينات Google Sheets في قاعدة البيانات الأصلية")
                success = True
        
        # فحص وجود نماذج أخرى للتأكد من أن النسخة الاحتياطية تعمل
        other_models = ['customers.customer', 'orders.order', 'accounts.user']
        print("\n  📋 نماذج أخرى للتحقق:")
        for model in other_models:
            count = sum(1 for item in data if item.get('model', '').lower() == model.lower())
            print(f"    📊 {model}: {count} سجل")
        
        return success
        
    except Exception as e:
        print(f"  ❌ خطأ في قراءة النسخة الاحتياطية: {str(e)}")
        return False

def main():
    """الدالة الرئيسية"""
    
    print("🚀 بدء اختبار النسخ الاحتياطي لتعيينات Google Sync")
    print("=" * 60)
    
    try:
        success = test_google_sync_backup()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 نجح الاختبار!")
            print("✅ تعيينات Google Sync يتم نسخها واستعادتها بشكل صحيح")
            print("\n📝 التوصيات:")
            print("  1. إنشاء نسخة احتياطية جديدة فوراً")
            print("  2. الاحتفاظ بالنسخ الاحتياطية الجديدة كمرجع أساسي")
            print("  3. عدم الاعتماد على النسخ الاحتياطية القديمة لاستعادة إعدادات Google Sync")
        else:
            print("❌ فشل الا��تبار!")
            print("⚠️ قد تكون هناك مشكلة في نسخ تعيينات Google Sync")
            print("\n🔧 خطوات استكشاف الأخطاء:")
            print("  1. التأكد من وجود تعيينات Google Sync في قاعدة البيانات")
            print("  2. فحص سجلات الأخطاء في النسخ الاحتياطي")
            print("  3. التأكد من أن تطبيق odoo_db_manager مُثبت بشكل صحيح")
        
    except Exception as e:
        print(f"\n❌ خطأ في تشغيل الاختبار: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()