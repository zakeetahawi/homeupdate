#!/usr/bin/env python
"""
سكريبت للتحقق من الطلبات الموجودة
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order


def check_existing_orders():
    """التحقق من الطلبات الموجودة"""
    print("🔍 التحقق من الطلبات الموجودة...")
    
    all_orders = Order.objects.all()[:10]
    print(f"📋 عدد الطلبات الإجمالي: {Order.objects.count()}")
    print(f"📋 عدد الطلبات المعروضة: {all_orders.count()}")
    
    for order in all_orders:
        print(f"\n   📋 الطلب: {order.order_number}")
        print(f"      العميل: {order.customer.name if order.customer else 'غير محدد'}")
        print(f"      وضع الطلب: {order.status}")
        print(f"      أنواع الطلب الخام: {order.selected_types}")
        print(f"      أنواع الطلب المفسرة: {order.get_selected_types_list()}")
        print(f"      تاريخ التسليم المتوقع: {order.expected_delivery_date}")
        
        # التحقق من وجود معاينة
        if 'inspection' in order.get_selected_types_list():
            print(f"      ✅ يحتوي على معاينة")
        else:
            print(f"      ❌ لا يحتوي على معاينة")


if __name__ == '__main__':
    check_existing_orders() 