#!/usr/bin/env python
"""
سكريبت تصحيح للطلبات
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order


def debug_orders():
    """تصحيح الطلبات"""
    print("🔍 تصحيح الطلبات...")
    
    # الحصول على جميع الطلبات
    all_orders = Order.objects.all()
    print(f"📋 عدد الطلبات الإجمالي: {all_orders.count()}")
    
    inspection_count = 0
    for order in all_orders:
        if 'inspection' in order.get_selected_types_list():
            inspection_count += 1
            print(f"\n   📋 طلب معاينة: {order.order_number}")
            print(f"      العميل: {order.customer.name if order.customer else 'غير محدد'}")
            print(f"      تاريخ التسليم الحالي: {order.expected_delivery_date}")
            
            # إعادة حساب تاريخ التسليم المتوقع
            old_delivery_date = order.expected_delivery_date
            order.expected_delivery_date = order.calculate_expected_delivery_date()
            
            if old_delivery_date != order.expected_delivery_date:
                print(f"      ✅ تم تحديث تاريخ التسليم من {old_delivery_date} إلى {order.expected_delivery_date}")
                # حفظ التحديثات
                order.save(update_fields=['expected_delivery_date'])
            else:
                print(f"      ℹ️ تاريخ التسليم لم يتغير: {order.expected_delivery_date}")
    
    print(f"\n✅ تم إصلاح {inspection_count} طلب معاينة بنجاح!")


if __name__ == '__main__':
    debug_orders() 