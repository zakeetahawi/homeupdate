#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection

def test_inspection_status():
    """اختبار دالة get_display_inspection_status"""
    print("🔍 اختبار حالة المعاينة في الطلبات...")
    
    # البحث عن طلبات المعاينة بطريقة أخرى
    all_orders = Order.objects.all()
    inspection_orders = []
    
    for order in all_orders:
        if 'inspection' in order.get_selected_types_list():
            inspection_orders.append(order)
    
    print(f"📊 عدد طلبات المعاينة: {len(inspection_orders)}")
    
    for order in inspection_orders[:5]:  # اختبار أول 5 طلبات فقط
        print(f"\n📋 الطلب: {order.order_number}")
        print(f"   العميل: {order.customer.name}")
        
        # الحصول على المعاينة الفعلية
        actual_inspection = order.inspections.first()
        
        if actual_inspection:
            print(f"   ✅ معاينة فعلية موجودة: {actual_inspection.contract_number}")
            print(f"   📊 حالة المعاينة: {actual_inspection.get_status_display()}")
        else:
            print(f"   ❌ لا توجد معاينة فعلية")
        
        # اختبار دالة get_display_inspection_status
        status_info = order.get_display_inspection_status()
        print(f"   🎯 نتيجة الدالة: {status_info['text']}")
        print(f"   🏷️  فئة الـ badge: {status_info['badge_class']}")
        print(f"   🎨 الأيقونة: {status_info['icon']}")

if __name__ == '__main__':
    test_inspection_status() 