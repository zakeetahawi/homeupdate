#!/usr/bin/env python3
"""
تنظيف جميع ملفات اللوغ والسجلات لمراقبة نظيفة
"""

import os
import glob
from datetime import datetime

def clean_logs():
    """تنظيف جميع ملفات اللوغ"""
    print("🧹 بدء تنظيف ملفات اللوغ...")
    
    # قائمة ملفات اللوغ المختلفة
    log_files = [
        # Django logs
        "logs/django.log",
        "logs/errors.log", 
        "logs/debug.log",
        "logs/access.log",
        
        # Celery logs
        "logs/celery.log",
        "logs/celery_optimized.log",
        "logs/celery_fixed.log",
        "/tmp/celery_worker.log",
        
        # System logs
        "/tmp/cloudflared.log",
        "/tmp/gunicorn.log",
        
        # Custom logs
        "logs/*.log",
        "*.log"
    ]
    
    cleaned_count = 0
    
    for log_pattern in log_files:
        # استخدام glob للبحث عن الملفات
        if '*' in log_pattern:
            files = glob.glob(log_pattern)
        else:
            files = [log_pattern] if os.path.exists(log_pattern) else []
        
        for log_file in files:
            try:
                if os.path.exists(log_file):
                    # حفظ نسخة احتياطية صغيرة إذا كان الملف كبير
                    file_size = os.path.getsize(log_file)
                    if file_size > 1024 * 1024:  # أكبر من 1MB
                        backup_name = f"{log_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        # حفظ آخر 100 سطر فقط
                        os.system(f"tail -100 '{log_file}' > '{backup_name}' 2>/dev/null")
                        print(f"💾 تم حفظ نسخة احتياطية: {backup_name}")
                    
                    # مسح الملف
                    with open(log_file, 'w') as f:
                        f.write(f"# تم تنظيف اللوغ في {datetime.now()}\n")
                    
                    print(f"🗑️ تم تنظيف: {log_file} ({file_size:,} bytes)")
                    cleaned_count += 1
                    
            except Exception as e:
                print(f"❌ خطأ في تنظيف {log_file}: {e}")
    
    # تنظيف ملفات PID القديمة
    pid_files = [
        "/tmp/celery_worker.pid",
        "/tmp/celery_worker_optimized.pid", 
        "/tmp/celery_worker_fixed.pid",
        "/tmp/gunicorn.pid"
    ]
    
    for pid_file in pid_files:
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
                print(f"🗑️ تم حذف ملف PID: {pid_file}")
                cleaned_count += 1
        except Exception as e:
            print(f"❌ خطأ في حذف {pid_file}: {e}")
    
    # إنشاء مجلد logs إذا لم يكن موجود
    if not os.path.exists("logs"):
        os.makedirs("logs")
        print("📁 تم إنشاء مجلد logs")
    
    # إنشاء ملفات لوغ فارغة جديدة
    new_logs = [
        "logs/django.log",
        "logs/celery_fixed.log",
        "logs/errors.log"
    ]
    
    for log_file in new_logs:
        try:
            with open(log_file, 'w') as f:
                f.write(f"# بدء مراقبة نظيفة - {datetime.now()}\n")
            print(f"📝 تم إنشاء لوغ جديد: {log_file}")
        except Exception as e:
            print(f"❌ خطأ في إنشاء {log_file}: {e}")
    
    print(f"\n✅ تم تنظيف {cleaned_count} ملف")
    print("🎉 المراقبة جاهزة بشكل نظيف!")

def clean_redis():
    """تنظيف Redis للبدء من جديد"""
    print("\n🧹 تنظيف Redis...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.flushdb()
        print("✅ تم تنظيف Redis")
    except Exception as e:
        print(f"❌ خطأ في تنظيف Redis: {e}")

def show_log_status():
    """عرض حالة ملفات اللوغ"""
    print("\n📊 حالة ملفات اللوغ:")
    print("-" * 40)
    
    log_files = [
        "logs/django.log",
        "logs/celery_fixed.log", 
        "logs/errors.log",
        "/tmp/celery_worker.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"📝 {log_file}: {size:,} bytes")
        else:
            print(f"❌ {log_file}: غير موجود")

def main():
    """الدالة الرئيسية"""
    print("🧹 تنظيف شامل لملفات اللوغ والسجلات")
    print("=" * 50)
    
    # تنظيف اللوغات
    clean_logs()
    
    # تنظيف Redis
    clean_redis()
    
    # عرض الحالة
    show_log_status()
    
    print("\n" + "=" * 50)
    print("🎉 تم التنظيف بنجاح!")
    print("💡 يمكنك الآن تشغيل النظام ومراقبة اللوغات النظيفة")
    print("📝 لمراقبة اللوغ الجديد: tail -f logs/celery_fixed.log")

if __name__ == "__main__":
    main()
