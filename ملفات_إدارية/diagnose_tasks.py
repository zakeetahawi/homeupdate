#!/usr/bin/env python
"""تشخيص المهام"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import BulkUploadLog
from django.db import connection

# فحص السجلات العالقة
stuck_logs = BulkUploadLog.objects.filter(status='processing')

print(f"📊 عدد السجلات العالقة: {stuck_logs.count()}")
print("-" * 80)

for log in stuck_logs:
    print(f"\n🔍 سجل #{log.id}:")
    print(f"   الملف: {log.file_name}")
    print(f"   task_id: {log.task_id}")
    print(f"   الحالة: {log.status}")
    print(f"   التقدم: {log.processed_count}/{log.total_rows}")
    print(f"   الوقت: {log.created_at}")
    
    # محاولة قراءة الملف المرفوع
    if log.uploaded_file:
        print(f"   المسار: {log.uploaded_file.path}")
        print(f"   الحجم: {log.uploaded_file.size} بايت")

print("\n" + "="*80)
print("💡 الإجراءات المقترحة:")
print("   1. حذف السجلات العالقة: BulkUploadLog.objects.filter(status='processing').delete()")
print("   2. اختبار بملف جديد")
