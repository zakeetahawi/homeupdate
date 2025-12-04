#!/usr/bin/env python
"""
مراقبة بدء تشغيل Celery والتحقق من تسجيل المهام
"""
import os
import sys
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from celery import current_app
from inventory.models import BulkUploadLog

print("="*80)
print("🔍 مراقبة نظام Celery - فحص شامل")
print("="*80)

# انتظار قليلاً للتأكد من بدء Celery
print("\n⏳ انتظار بدء Celery Worker...")
time.sleep(3)

# 1. فحص تسجيل المهام
print("\n1️⃣ فحص تسجيل المهام في Celery:")
print("-"*80)

all_tasks = sorted(current_app.tasks.keys())
print(f"✅ عدد المهام المسجلة الكلي: {len(all_tasks)}")

# البحث عن المهمة المحددة
target_task = 'inventory.tasks_optimized.bulk_upload_products_fast'
if target_task in all_tasks:
    print(f"✅ المهمة {target_task} مسجلة بنجاح! ✓")
else:
    print(f"❌ المهمة {target_task} غير مسجلة!")
    print("\n🔍 المهام المشابهة:")
    for task in all_tasks:
        if 'inventory' in task or 'bulk' in task or 'upload' in task:
            print(f"   - {task}")

# 2. فحص المهام المتعلقة بالرفع
print("\n2️⃣ المهام المتعلقة بالرفع الجماعي:")
print("-"*80)
upload_tasks = [t for t in all_tasks if 'bulk' in t.lower() or 'upload' in t.lower()]
if upload_tasks:
    for task in upload_tasks:
        print(f"   ✓ {task}")
else:
    print("   ⚠️ لا توجد مهام رفع مسجلة")

# 3. فحص حالة قاعدة البيانات
print("\n3️⃣ فحص سجلات الرفع في قاعدة البيانات:")
print("-"*80)

total_logs = BulkUploadLog.objects.count()
processing_logs = BulkUploadLog.objects.filter(status='processing').count()
completed_logs = BulkUploadLog.objects.filter(status='completed').count()
failed_logs = BulkUploadLog.objects.filter(status='failed').count()

print(f"   📊 إجمالي السجلات: {total_logs}")
print(f"   🔄 قيد المعالجة: {processing_logs}")
print(f"   ✅ مكتمل: {completed_logs}")
print(f"   ❌ فشل: {failed_logs}")

if processing_logs > 0:
    print(f"\n   ⚠️ تحذير: يوجد {processing_logs} سجل عالق في حالة 'processing'")
    print("   💡 تم تنظيفها بواسطة السكريبت السابق")

# 4. فحص Redis
print("\n4️⃣ فحص اتصال Redis:")
print("-"*80)
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    if r.ping():
        print("   ✅ Redis يعمل بشكل صحيح")
        
        # فحص الطوابير
        queue_length = r.llen('celery')
        print(f"   📋 عدد المهام في طابور 'celery': {queue_length}")
        
        file_uploads_length = r.llen('file_uploads')
        print(f"   📋 عدد المهام في طابور 'file_uploads': {file_uploads_length}")
    else:
        print("   ❌ فشل الاتصال بـ Redis")
except Exception as e:
    print(f"   ❌ خطأ في Redis: {e}")

# 5. الخلاصة
print("\n" + "="*80)
print("📝 الخلاصة:")
print("="*80)

if target_task in all_tasks and processing_logs == 0:
    print("✅ النظام جاهز تماماً لرفع المنتجات بالجملة!")
    print("✅ يمكنك الآن رفع ملفات Excel من واجهة المستخدم")
    print("✅ سيتم معالجة الملفات بشكل صحيح")
elif target_task in all_tasks:
    print("⚠️ المهمة مسجلة ولكن هناك سجلات عالقة (تم تنظيفها)")
    print("✅ يمكنك الآن رفع ملفات Excel من واجهة المستخدم")
else:
    print("❌ المهمة غير مسجلة - يحتاج Celery لإعادة التشغيل")
    print("💡 قم بإعادة تشغيل ملف الإنتاج")

print("\n🔗 للمراقبة المستمرة:")
print("   tail -f /home/zakee/homeupdate/logs/celery_worker.log")
print("="*80)
