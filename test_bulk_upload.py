#!/usr/bin/env python
"""
اختبار سريع لنظام الرفع بالجملة
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import BulkUploadLog

# فحص آخر 5 سجلات
logs = BulkUploadLog.objects.all().order_by('-id')[:5]

print("📋 آخر 5 عمليات رفع:")
print("-" * 80)
for log in logs:
    status_emoji = {
        'processing': '🔄',
        'completed': '✅',
        'completed_with_errors': '⚠️',
        'failed': '❌'
    }.get(log.status, '❓')
    
    print(f"{status_emoji} ID: {log.id} | {log.file_name} | {log.status}")
    print(f"   الحالة: {log.processed_count}/{log.total_rows} صف")
    print(f"   إنشاء: {log.created_count} | تحديث: {log.updated_count} | أخطاء: {log.error_count}")
    print()

print("\n💡 لاختبار الرفع، ارفع ملف Excel من:")
print("   http://127.0.0.1:8000/inventory/products/bulk-upload/")
