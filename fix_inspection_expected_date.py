#!/usr/bin/env python
"""
تحديث جميع طلبات المعاينة ليكون موعد المعاينة المتوقع بعد 48 ساعة من تاريخ الطلب (معاينة فقط)
"""
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order

def fix_inspection_expected_date():
    print("🔧 تحديث موعد المعاينة المتوقع لجميع طلبات المعاينة فقط...")
    count = 0
    for order in Order.objects.all():
        types = order.get_selected_types_list()
        if len(types) == 1 and 'inspection' in types:
            correct_date = (order.order_date.date() + timedelta(days=2))
            if order.expected_delivery_date != correct_date:
                print(f"- الطلب {order.order_number}: {order.expected_delivery_date} ← {correct_date}")
                order.expected_delivery_date = correct_date
                order.save(update_fields=['expected_delivery_date'])
                count += 1
    print(f"\n✅ تم تحديث {count} طلب معاينة فقط!")

if __name__ == '__main__':
    fix_inspection_expected_date() 