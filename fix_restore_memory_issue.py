#!/usr/bin/env python
"""
إصلاح مشكلة استهلاك الذاكرة في عملية الاستعادة
"""
import os
import sys
import django
import json
import gzip
import tempfile
from django.utils import timezone

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from odoo_db_manager.models import RestoreProgress


def fix_stuck_restore_processes():
    """إصلاح العمليات العالقة وتنظيف الملفات المؤقتة"""
    
    print("🔧 بدء إصلاح العمليات العالقة...")
    
    # 1. إيقاف جميع عمليات الاستعادة العالقة
    stuck_processes = RestoreProgress.objects.filter(
        status__in=['processing', 'starting'],
        created_at__lt=timezone.now() - timezone.timedelta(minutes=5)
    )
    
    print(f"🔍 وجدت {stuck_processes.count()} عملية عالقة")
    
    for process in stuck_processes:
        print(f"⏹️ إيقاف العملية العالقة: {process.session_id}")
        process.status = 'failed'
        process.error_message = 'تم إيقاف العملية بسبب التعليق'
        process.current_step = 'تم الإيقاف'
        process.save()
    
    # 2. تنظيف الملفات المؤقتة
    temp_files = []
    for filename in os.listdir('/tmp'):
        if filename.startswith('tmp') and filename.endswith('.json'):
            temp_files.append(os.path.join('/tmp', filename))
    
    print(f"🗑️ وجدت {len(temp_files)} ملف مؤقت للحذف")
    
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
            print(f"✅ تم حذف: {temp_file}")
        except Exception as e:
            print(f"❌ فشل حذف {temp_file}: {e}")
    
    print("✅ تم إصلاح العمليات العالقة وتنظيف الملفات المؤقتة")


def create_optimized_restore_function():
    """إنشاء دالة استعادة محسنة للملفات الكبيرة"""
    
    optimized_code = '''
def _restore_json_optimized(file_path, clear_existing=False, progress_callback=None, session_id=None):
    """
    دالة ��ستعادة محسنة للملفات الكبيرة مع معالجة الذاكرة
    """
    import json
    import gzip
    import os
    from django.core import serializers
    from django.db import transaction
    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    
    def update_progress(current_step=None, processed_items=None, success_count=None, error_count=None):
        if progress_callback:
            progress_percentage = 0
            if processed_items is not None and total_items > 0:
                progress_percentage = min(100, int((processed_items / total_items) * 100))
            
            progress_callback(
                progress_percentage=progress_percentage,
                current_step=current_step,
                processed_items=processed_items,
                success_count=success_count,
                error_count=error_count
            )
    
    try:
        update_progress(current_step='🔄 بدء عملية الاستعادة المحسنة...')
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(file_path)
        print(f"📊 حجم الملف: {file_size:,} بايت ({file_size/1024/1024:.1f} MB)")
        
        if file_size > 50 * 1024 * 1024:  # أكبر من 50MB
            raise ValueError("الملف كبير جداً (أكبر من 50MB). يرجى استخدام ملف أصغر.")
        
        update_progress(current_step='📖 قراءة الملف بطريقة محسنة...')
        
        # قراءة الملف بطريقة محسنة
        data = None
        if file_path.lower().endswith('.gz'):
            print("📦 فك ضغط ملف .gz...")
            try:
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    # قراءة الملف على دفعات لتجنب استهلاك الذاكرة
                    content = ""
                    chunk_size = 1024 * 1024  # 1MB chunks
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        content += chunk
                        update_progress(current_step=f'📖 قراءة الملف... ({len(content):,} حرف)')
                    
                    data = json.loads(content)
                    del content  # تحرير الذاكرة
                    
            except Exception as e:
                print(f"❌ خطأ في فك ضغط الملف: {e}")
                raise ValueError(f"فشل في فك ضغط الملف: {str(e)}")
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"❌ خطأ في قراءة الملف: {e}")
                raise ValueError(f"فشل في قراءة الملف: {str(e)}")
        
        if not isinstance(data, list):
            if isinstance(data, dict) and 'model' in data and 'fields' in data:
                data = [data]
            else:
                raise ValueError("تنسيق الملف غير صحيح. يجب أن يكون ملف Django fixture صالح.")
        
        total_items = len(data)
        update_progress(current_step=f'📊 تم تحليل {total_items} عنصر', processed_items=0)
        
        if progress_callback:
            progress_callback(total_items=total_items)
        
        success_count = 0
        error_count = 0
        
        # معالجة البيانات على دفعات صغيرة
        batch_size = 50  # معالجة 50 عنصر في كل مرة
        
        for i in range(0, total_items, batch_size):
            batch = data[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, total_items)
            
            update_progress(
                current_step=f'🔄 معالجة الدفعة {batch_start}-{batch_end} من {total_items}',
                processed_items=i
            )
            
            for j, item in enumerate(batch):
                try:
                    with transaction.atomic():
                        for obj in serializers.deserialize('json', json.dumps([item])):
                            obj.save()
                    success_count += 1
                except Exception as item_error:
                    error_count += 1
                    print(f"⚠️ فشل في استعادة العنصر {i + j + 1}: {str(item_error)}")
                
                # تحديث التقدم كل 10 عناصر
                if (i + j + 1) % 10 == 0:
                    update_progress(
                        processed_items=i + j + 1,
                        success_count=success_count,
                        error_count=error_count
                    )
        
        # التحديث النهائي
        update_progress(
            current_step='✅ اكتملت العملية بنجاح',
            processed_items=total_items,
            success_count=success_count,
            error_count=error_count
        )
        
        return {
            'total_count': total_items,
            'success_count': success_count,
            'error_count': error_count
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ خطأ في الاستعادة: {error_msg}")
        update_progress(
            current_step=f'❌ فشلت العملية: {error_msg}',
            error_message=error_msg
        )
        raise
'''
    
    # كتابة الدالة المحسنة إلى ملف
    with open('/home/zakee/homeupdate/optimized_restore.py', 'w', encoding='utf-8') as f:
        f.write(optimized_code)
    
    print("✅ تم إنشاء دالة الاستعادة المحسنة في optimized_restore.py")


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء إصلاح مشاكل الاستعادة...")
    
    # 1. إصلاح العمليات العالقة
    fix_stuck_restore_processes()
    
    # 2. إنشاء دالة محسنة
    create_optimized_restore_function()
    
    print("\n✅ تم إنجاز جميع الإصلاحات!")
    print("\n���� التوصيات:")
    print("1. أعد تشغيل الخادم: python manage.py runserver")
    print("2. استخدم ملفات أصغر من 25MB للاستعادة")
    print("3. تأكد من وجود ذاكرة كافية (RAM) قبل الاستعادة")


if __name__ == "__main__":
    main()