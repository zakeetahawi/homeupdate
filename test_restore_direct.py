#!/usr/bin/env python3
"""
سكريبت لاختبار عملية الاستعادة مباشرة
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from odoo_db_manager.models import Database, RestoreProgress
from odoo_db_manager.views import _restore_json_simple_with_progress

User = get_user_model()


def test_restore():
    """اختبار عملية الاستعادة"""
    
    print("🔍 [TEST] بدء اختبار عملية الاستعادة...")
    
    # إنشاء مستخدم تجريبي إذا لم يكن موجوداً
    try:
        user = User.objects.get(username='admin')
        print(f"✅ [TEST] المستخدم موجود: {user.username}")
    except User.DoesNotExist:
        print("❌ [TEST] المستخدم غير موجود")
        return
    
    # إنشاء قاعدة بيانات تجريبية إذا لم تكن موجودة
    try:
        database = Database.objects.get(name='test_db')
        print(f"✅ [TEST] قاعدة البيانات موجودة: {database.name}")
    except Database.DoesNotExist:
        database = Database.objects.create(
            name='test_db',
            db_type='postgresql',
            connection_info={
                'HOST': 'localhost',
                'PORT': '5432',
                'NAME': 'test_db',
                'USER': 'postgres',
                'PASSWORD': 'password'
            },
            is_active=True
        )
        print(f"✅ [TEST] تم إنشاء قاعدة البيانات: {database.name}")
    
    # إنشاء RestoreProgress
    session_id = 'test_session_123'
    
    # حذف أي progress سابق
    RestoreProgress.objects.filter(session_id=session_id).delete()
    
    progress = RestoreProgress.objects.create(
        session_id=session_id,
        user=user,
        database=database,
        filename='test_backup_small.json',
        status='starting'
    )
    
    print(f"✅ [TEST] تم إنشاء RestoreProgress: {progress.id}")
    
    # دالة تحديث التقدم
    def update_progress(status=None, current_step=None, processed_items=None, 
                        total_items=None, success_count=None, error_count=None):
        """دالة تحديث التقدم"""
        print(f"🔍 [TEST] تحديث التقدم: {status} - {current_step} - {processed_items}")
        progress.update_progress(
            status=status,
            current_step=current_step,
            processed_items=processed_items,
            success_count=success_count,
            error_count=error_count
        )
        if total_items is not None:
            progress.total_items = total_items
            progress.save()
    
    # اختبار الاستعادة
    try:
        file_path = 'test_backup_small.json'
        
        if not os.path.exists(file_path):
            print(f"❌ [TEST] الملف غير موجود: {file_path}")
            return
        
        print(f"🔍 [TEST] بدء استعادة الملف: {file_path}")
        
        result = _restore_json_simple_with_progress(
            file_path, 
            clear_existing=False, 
            progress_callback=update_progress
        )
        
        print("✅ [TEST] تمت الاستعادة بنجاح!")
        print(f"📊 [TEST] النتائج: {result}")
        
        # تحديث التقدم النهائي
        progress.set_completed(result)
        
    except Exception as e:
        print(f"❌ [TEST] خطأ في الاستعادة: {str(e)}")
        progress.set_failed(str(e))
    
    print("🔍 [TEST] انتهى الاختبار")


if __name__ == '__main__':
    test_restore() 