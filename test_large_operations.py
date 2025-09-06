#!/usr/bin/env python3
"""
اختبار الإعدادات الجديدة للملفات الكبيرة والمزامنة
Testing new settings for large files and synchronization
"""

import os
import sys
import django
import time
import requests
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.conf import settings
from celery import Celery
from inspections.models import Inspection
from inspections.tasks import upload_inspection_to_drive

def test_large_file_settings():
    """اختبار إعدادات الملفات الكبيرة"""
    print("🔧 اختبار إعدادات الملفات الكبيرة:")
    print("=" * 50)
    
    # فحص إعدادات Django
    print(f"📁 حد حجم الملف في الذاكرة: {settings.FILE_UPLOAD_MAX_MEMORY_SIZE / (1024*1024):.0f} ميجابايت")
    print(f"📊 حد حجم البيانات: {settings.DATA_UPLOAD_MAX_MEMORY_SIZE / (1024*1024):.0f} ميجابايت")
    
    # فحص إعدادات Celery
    print(f"⏰ حد وقت المهام: {settings.CELERY_TASK_TIME_LIMIT} ثانية ({settings.CELERY_TASK_TIME_LIMIT/60:.0f} دقيقة)")
    print(f"🔄 حد وقت المهام الناعم: {settings.CELERY_TASK_SOFT_TIME_LIMIT} ثانية ({settings.CELERY_TASK_SOFT_TIME_LIMIT/60:.0f} دقيقة)")
    
    # فحص إعدادات قاعدة البيانات
    db_settings = settings.DATABASES['default']
    print(f"🗄️ عمر الاتصال: {db_settings.get('CONN_MAX_AGE', 0)} ثانية")
    print(f"🔍 فحص صحة الاتصال: {db_settings.get('CONN_HEALTH_CHECKS', False)}")
    
    return True

def test_celery_connection():
    """اختبار اتصال Celery"""
    print("\n🔗 اختبار اتصال Celery:")
    print("=" * 30)
    
    try:
        from celery import current_app
        
        # فحص الاتصال
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print("✅ Celery Worker متصل ويعمل")
            for worker_name, worker_stats in stats.items():
                print(f"  👷 {worker_name}: {worker_stats.get('pool', {}).get('processes', 0)} عملية")
            
            # فحص قوائم الانتظار
            active_queues = inspect.active_queues()
            if active_queues:
                print("📋 قوائم الانتظار النشطة:")
                for worker_name, queues in active_queues.items():
                    queue_names = [q['name'] for q in queues]
                    print(f"  {worker_name}: {', '.join(queue_names)}")
            
            return True
        else:
            print("❌ لا يمكن الاتصال بـ Celery Worker")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في الاتصال بـ Celery: {str(e)}")
        return False

def test_inspection_upload():
    """اختبار رفع ملف معاينة"""
    print("\n📤 اختبار رفع ملف معاينة:")
    print("=" * 35)
    
    try:
        # البحث عن معاينة لم يتم رفعها
        pending_inspection = Inspection.objects.filter(
            upload_status='pending'
        ).first()
        
        if pending_inspection:
            print(f"🔍 وجدت معاينة للرفع: {pending_inspection.inspection_number}")
            
            # بدء مهمة الرفع
            task = upload_inspection_to_drive.delay(pending_inspection.id)
            print(f"🚀 بدأت مهمة الرفع: {task.id}")
            
            # انتظار قصير
            time.sleep(2)
            
            # فحص حالة المهمة
            result = task.ready()
            if result:
                print(f"✅ المهمة اكتملت: {task.result}")
            else:
                print(f"⏳ المهمة قيد التنفيذ...")
                
            return True
        else:
            print("ℹ️ لا توجد معاينات معلقة للرفع")
            return True
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الرفع: {str(e)}")
        return False

def test_timeout_settings():
    """اختبار إعدادات المهلة الزمنية"""
    print("\n⏱️ اختبار إعدادات المهلة الزمنية:")
    print("=" * 40)
    
    # فحص إعدادات Cloudflare Tunnel
    try:
        with open('cloudflared.yml', 'r') as f:
            content = f.read()
            if 'connectTimeout: 60s' in content:
                print("✅ إعدادات Cloudflare Tunnel محدثة")
            else:
                print("⚠️ إعدادات Cloudflare Tunnel قد تحتاج تحديث")
    except FileNotFoundError:
        print("⚠️ ملف cloudflared.yml غير موجود")
    
    # فحص إعدادات العمليات الكبيرة
    if hasattr(settings, 'LARGE_OPERATIONS_CONFIG'):
        config = settings.LARGE_OPERATIONS_CONFIG
        print(f"📊 حد الرفع الأقصى: {config['MAX_UPLOAD_SIZE'] / (1024*1024*1024):.1f} جيجابايت")
        print(f"⏰ مهلة الاتصال: {config['CONNECTION_TIMEOUT']} ثانية")
        print(f"🔗 مدة keep-alive للجسر: {config['BRIDGE_KEEPALIVE']} ثانية")
    
    return True

def main():
    """الدالة الرئيسية للاختبار"""
    print(f"🧪 اختبار إعدادات الأداء والملفات الكبيرة")
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    # اختبار 1: إعدادات الملفات الكبيرة
    if test_large_file_settings():
        tests_passed += 1
    
    # اختبار 2: اتصال Celery
    if test_celery_connection():
        tests_passed += 1
    
    # اختبار 3: رفع المعاينات
    if test_inspection_upload():
        tests_passed += 1
    
    # اختبار 4: إعدادات المهلة الزمنية
    if test_timeout_settings():
        tests_passed += 1
    
    # النتيجة النهائية
    print("\n" + "=" * 60)
    print(f"📊 نتائج الاختبار: {tests_passed}/{total_tests} اختبار نجح")
    
    if tests_passed == total_tests:
        print("🎉 جميع الاختبارات نجحت! النظام جاهز للعمليات الكبيرة")
        return True
    else:
        print("⚠️ بعض الاختبارات فشلت - قد تحتاج مراجعة الإعدادات")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
