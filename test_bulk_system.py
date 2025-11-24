#!/usr/bin/env python
"""
اختبار نظام الرفع بالجملة
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.tasks_optimized import bulk_upload_products_fast
from inventory.models import BulkUploadLog, Warehouse
from django.contrib.auth import get_user_model
import pandas as pd
from io import BytesIO
import time

User = get_user_model()

print("🧪 اختبار نظام الرفع بالجملة")
print("=" * 80)

# 1. إنشاء ملف اختبار
print("\n1️⃣ إنشاء ملف Excel اختبار...")
data = {
    'اسم المنتج': ['منتج اختبار 1'],
    'الكود': ['TEST001'],
    'الفئة': ['اقمشة'],
    'السعر': [100],
    'الكمية': [10],
    'المستودع': ['المستودع الرئيسي'],
    'الوصف': ['اختبار النظام'],
    'الحد الأدنى': [5],
    'العملة': ['IQD'],
    'الوحدة': ['متر']
}

df = pd.DataFrame(data)
buffer = BytesIO()
df.to_excel(buffer, index=False, engine='openpyxl')
file_content = buffer.getvalue()
print(f"   ✅ ملف جاهز ({len(file_content)} بايت)")

# 2. إنشاء سجل
print("\n2️⃣ إنشاء سجل رفع...")
user = User.objects.first()
warehouse = Warehouse.objects.first()

upload_log = BulkUploadLog.objects.create(
    upload_type='products',
    file_name='test.xlsx',
    warehouse=warehouse,
    created_by=user,
    status='processing'
)
print(f"   ✅ سجل #{upload_log.id}")

# 3. إرسال المهمة
print("\n3️⃣ إرسال المهمة...")
task = bulk_upload_products_fast.delay(
    upload_log.id,
    file_content,
    warehouse.id,
    'add_to_existing',
    user.id
)

upload_log.task_id = task.id
upload_log.save(update_fields=['task_id'])
print(f"   ✅ المهمة: {task.id}")

# 4. انتظار النتيجة
print("\n4️⃣ انتظار التنفيذ (10 ثواني)...")
for i in range(10):
    time.sleep(1)
    upload_log.refresh_from_db()
    print(f"   [{i+1}/10] الحالة: {upload_log.status} | التقدم: {upload_log.processed_count}/{upload_log.total_rows}")
    
    if upload_log.status in ['completed', 'failed', 'completed_with_errors']:
        break

# 5. النتيجة النهائية
print("\n" + "=" * 80)
upload_log.refresh_from_db()
print(f"📊 النتيجة النهائية:")
print(f"   الحالة: {upload_log.status}")
print(f"   التقدم: {upload_log.processed_count}/{upload_log.total_rows}")
print(f"   إنشاء: {upload_log.created_count}")
print(f"   تحديث: {upload_log.updated_count}")
print(f"   أخطاء: {upload_log.error_count}")

if upload_log.status == 'completed':
    print("\n✅ النظام يعمل بنجاح!")
elif upload_log.status == 'processing':
    print("\n⚠️ المهمة ما زالت قيد المعالجة - المشكلة في Celery worker!")
else:
    print(f"\n❌ فشل: {upload_log.summary}")
