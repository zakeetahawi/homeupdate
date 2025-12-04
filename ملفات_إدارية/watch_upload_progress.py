#!/usr/bin/env python
"""
مراقبة عملية الرفع في الوقت الفعلي
"""
import os
import sys
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import BulkUploadLog

print("="*80)
print("📊 مراقبة عمليات الرفع في الوقت الفعلي")
print("="*80)
print("⏳ في انتظار عملية رفع جديدة...")
print("   (قم برفع ملف Excel من المتصفح الآن)")
print("="*80)

# تتبع آخر ID
last_id = BulkUploadLog.objects.all().order_by('-id').first()
last_id_num = last_id.id if last_id else 0

while True:
    time.sleep(2)  # فحص كل ثانيتين
    
    # البحث عن سجلات جديدة
    new_logs = BulkUploadLog.objects.filter(id__gt=last_id_num).order_by('id')
    
    if new_logs.exists():
        for log in new_logs:
            print(f"\n🆕 عملية رفع جديدة!")
            print(f"   ID: {log.id}")
            print(f"   الملف: {log.file_name}")
            print(f"   الحالة: {log.status}")
            print(f"   Task ID: {log.task_id}")
            
            # مراقبة التقدم
            while log.status == 'processing':
                time.sleep(1)
                log.refresh_from_db()
                
                if log.total_rows > 0:
                    progress = (log.processed_count / log.total_rows) * 100
                    print(f"\r   التقدم: {log.processed_count}/{log.total_rows} ({progress:.1f}%) | جديد:{log.created_count} محدث:{log.updated_count} أخطاء:{log.error_count}", end='', flush=True)
                else:
                    print(f"\r   التقدم: {log.processed_count} صف معالج...", end='', flush=True)
            
            # النتيجة النهائية
            print(f"\n\n✅ اكتملت العملية!")
            print(f"   الحالة النهائية: {log.status}")
            print(f"   الملخص: {log.summary}")
            print(f"   إجمالي: {log.total_rows} صف")
            print(f"   معالج: {log.processed_count}")
            print(f"   جديد: {log.created_count}")
            print(f"   محدث: {log.updated_count}")
            print(f"   أخطاء: {log.error_count}")
            print("="*80)
            
            last_id_num = log.id
            print("\n⏳ في انتظار عملية رفع أخرى...")
