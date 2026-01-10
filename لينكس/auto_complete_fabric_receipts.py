#!/usr/bin/env python
"""
سكريبت لمرة واحدة: تحديد الأقمشة كمستلمة تلقائياً للطلبات التي رقم الإذن بها AUTO-COMPLETED

الاستخدام:
    python manage.py shell < لينكس/auto_complete_fabric_receipts.py

أو:
    python manage.py shell
    >>> exec(open('لينكس/auto_complete_fabric_receipts.py').read())
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')

try:
    django.setup()
except:
    pass  # Django may already be set up if running from shell

from django.utils import timezone
from django.db import transaction
from manufacturing.models import ManufacturingOrderItem, FabricReceipt, FabricReceiptItem

print("=" * 60)
print("🔄 بدء تحديث استلام الأقمشة للطلبات ذات رقم إذن AUTO-COMPLETED")
print("=" * 60)

# البحث عن جميع العناصر التي رقم الإذن بها يحتوي على AUTO-COMPLETED ولم يتم استلامها بعد
items_to_update = ManufacturingOrderItem.objects.filter(
    permit_number__icontains='AUTO-COMPLETED',
    fabric_received=False
)

total_count = items_to_update.count()
print(f"\n📊 عدد العناصر المطلوب تحديثها: {total_count}")

if total_count == 0:
    print("✅ لا توجد عناصر تحتاج إلى تحديث.")
    sys.exit(0)

updated_count = 0
error_count = 0

for item in items_to_update:
    try:
        with transaction.atomic():
            # تحديث حالة العنصر
            item.fabric_received = True
            item.fabric_received_date = timezone.now()
            item.fabric_notes = 'تم الاستلام تلقائياً - سكريبت AUTO-COMPLETED'
            item.save(update_fields=['fabric_received', 'fabric_received_date', 'fabric_notes'])
            
            # إنشاء سجل FabricReceipt إذا لم يكن موجوداً
            fabric_receipt, created = FabricReceipt.objects.get_or_create(
                manufacturing_order=item.manufacturing_order,
                bag_number=item.bag_number or 'AUTO',
                defaults={
                    'receipt_type': 'manufacturing_order',
                    'order': item.manufacturing_order.order if item.manufacturing_order else None,
                    'permit_number': item.permit_number,
                    'received_by_name': 'نظام آلي',
                    'receipt_date': timezone.now(),
                    'notes': 'تم الاستلام تلقائياً - سكريبت AUTO-COMPLETED'
                }
            )
            
            # إنشاء عنصر الاستلام إذا لم يكن موجوداً
            if not FabricReceiptItem.objects.filter(
                fabric_receipt=fabric_receipt,
                order_item=item.order_item
            ).exists():
                FabricReceiptItem.objects.create(
                    fabric_receipt=fabric_receipt,
                    order_item=item.order_item,
                    cutting_item=item.cutting_item,
                    product_name=item.product_name,
                    quantity_received=item.quantity,
                    item_notes='تم الاستلام تلقائياً - سكريبت'
                )
            
            updated_count += 1
            print(f"  ✅ تم تحديث: {item.product_name} (أمر تصنيع: {item.manufacturing_order.manufacturing_code if item.manufacturing_order else 'N/A'})")
            
    except Exception as e:
        error_count += 1
        print(f"  ❌ خطأ في العنصر {item.pk}: {str(e)}")

print("\n" + "=" * 60)
print(f"📊 ملخص التحديث:")
print(f"   - إجمالي العناصر: {total_count}")
print(f"   - تم التحديث بنجاح: {updated_count}")
print(f"   - أخطاء: {error_count}")
print("=" * 60)
print("✅ اكتمل السكريبت!")
