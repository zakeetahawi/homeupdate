#!/usr/bin/env python
"""
سكريبت إصلاح الطلبات الموجودة
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order


def fix_existing_orders():
    """إصلاح الطلبات الموجودة"""
    print("🔧 إصلاح الطلبات الموجودة...")
    
    # الحصول على طلبات المعاينة
    inspection_orders = Order.objects.filter(
        selected_types__contains='inspection'
    )
    
    print(f"📋 عدد طلبات المعاينة: {inspection_orders.count()}")
    
    for order in inspection_orders:
        print(f"\n   📋 إصلاح الطلب: {order.order_number}")
        print(f"      العميل: {order.customer.name if order.customer else 'غير محدد'}")
        print(f"      تاريخ التسليم الحالي: {order.expected_delivery_date}")
        
        # إعادة حساب تاريخ التسليم المتوقع
        old_delivery_date = order.expected_delivery_date
        order.expected_delivery_date = order.calculate_expected_delivery_date()
        
        if old_delivery_date != order.expected_delivery_date:
            print(f"      ✅ تم تحديث تاريخ التسليم من {old_delivery_date} إلى {order.expected_delivery_date}")
        else:
            print(f"      ℹ️ تاريخ التسليم لم يتغير: {order.expected_delivery_date}")
        
        # حفظ التحديثات
        order.save(update_fields=['expected_delivery_date'])
    
    print(f"\n✅ تم إصلاح {inspection_orders.count()} طلب بنجاح!")


if __name__ == '__main__':
    fix_existing_orders() 