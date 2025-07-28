#!/usr/bin/env python
"""
سكريبت اختبار نظام الاستعادة
"""
import os
import sys
import django
import time
from pathlib import Path

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from backup_system.services import backup_manager
from backup_system.models import RestoreJob
from django.contrib.auth import get_user_model

User = get_user_model()

def test_restore():
    """اختبار عملية الاستعادة"""
    
    # الحصول على مستخدم للاختبار
    user = User.objects.first()
    if not user:
        print("❌ لا يوجد مستخدمين في النظام")
        return
    
    # مسار الملف
    file_path = "/home/zakee/homeupdate/media/uploads/2024فثسف_20250728_182153.json.gz"
    
    if not os.path.exists(file_path):
        print(f"❌ الملف غير موجود: {file_path}")
        return
    
    print("🚀 بدء اختبار نظام الاستعادة")
    print(f"📁 الملف: {file_path}")
    print(f"📊 حجم الملف: {os.path.getsize(file_path):,} بايت")
    print(f"👤 المستخدم: {user.username}")
    print("-" * 50)
    
    try:
        # بدء عملية الاستعادة
        job = backup_manager.restore_backup(
            file_path=file_path,
            user=user,
            name="اختبار استعادة النظام الجديد",
            clear_existing=False,  # لا نحذف البيانات الموجودة في الاختبار
            description="اختبار عملية الاستعادة من النظام الجديد"
        )
        
        print(f"✅ تم إنشاء مهمة الاستعادة: {job.id}")
        print(f"📝 الاسم: {job.name}")
        print(f"🔄 الحالة الأولية: {job.get_status_display()}")
        print("-" * 50)
        
        # مراقبة التقدم
        print("📊 مراقبة تقدم العملية:")
        last_progress = -1
        last_step = ""
        
        while True:
            # تحديث بيانات المهمة
            job.refresh_from_db()
            
            # عرض التقدم إذا تغير
            if job.progress_percentage != last_progress or job.current_step != last_step:
                progress_bar = "█" * int(job.progress_percentage / 5) + "░" * (20 - int(job.progress_percentage / 5))
                print(f"\r🔄 [{progress_bar}] {job.progress_percentage:.1f}% - {job.current_step}", end="", flush=True)
                last_progress = job.progress_percentage
                last_step = job.current_step
            
            # التحقق من انتهاء العملية
            if job.status in ['completed', 'failed', 'cancelled']:
                print()  # سطر جديد
                break
            
            time.sleep(2)  # انتظار ثانيتين قبل التحقق مرة أخرى
        
        print("-" * 50)
        
        # عرض النتائج النهائية
        if job.status == 'completed':
            print("🎉 تمت عملية الاستعادة بنجاح!")
            print(f"📊 إجمالي السجلات: {job.total_records:,}")
            print(f"✅ السجلات الناجحة: {job.success_records:,}")
            print(f"❌ السجلات الفاشلة: {job.failed_records:,}")
            print(f"📈 نسبة النجاح: {job.success_rate:.1f}%")
            if job.duration:
                print(f"⏱️ المدة: {job.duration}")
        
        elif job.status == 'failed':
            print("❌ فشلت عملية الاستعادة!")
            print(f"🚨 رسالة الخطأ: {job.error_message}")
        
        else:
            print(f"⚠️ حالة غير متوقعة: {job.get_status_display()}")
        
        print("-" * 50)
        print(f"🔗 يمكنك مراجعة التفاصيل في: http://localhost:8000/backup-system/restore/{job.id}/")
        
        return job
        
    except Exception as e:
        print(f"❌ خطأ في بدء عملية الاستعادة: {str(e)}")
        return None

if __name__ == "__main__":
    test_restore()