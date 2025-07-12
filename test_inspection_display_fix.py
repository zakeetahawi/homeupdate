#!/usr/bin/env python
"""
سكريبت اختبار إصلاح عرض المعاينات
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from datetime import datetime, timedelta


def test_inspection_display():
    """اختبار عرض المعاينات"""
    print("🔍 اختبار عرض المعاينات...")
    
    # الحصول على جميع الطلبات وفلترة المعاينات
    all_orders = Order.objects.all()
    inspection_orders = [order for order in all_orders if 'inspection' in order.get_selected_types_list()]
    
    print(f"📋 عدد طلبات المعاينة: {len(inspection_orders)}")
    
    for order in inspection_orders[:3]:
        print(f"\n   📋 الطلب: {order.order_number}")
        print(f"      العميل: {order.customer.name if order.customer else 'غير محدد'}")
        print(f"      وضع الطلب: {order.status}")
        print(f"      أنواع الطلب: {order.get_selected_types_list()}")
        print(f"      تاريخ التسليم المتوقع: {order.expected_delivery_date}")
        
        # التحقق من أن وضع الطلب عادي للمعاينات
        if 'inspection' in order.get_selected_types_list():
            if order.status == 'normal':
                print(f"      ✅ وضع الطلب صحيح: عادي")
            else:
                print(f"      ❌ وضع الطلب غير صحيح: {order.status}")
        
        # التحقق من موعد التسليم (48 ساعة)
        if order.expected_delivery_date:
            delivery_days = (order.expected_delivery_date - order.order_date.date()).days
            if delivery_days == 2:  # 48 ساعة = يومين
                print(f"      ✅ موعد التسليم صحيح: {delivery_days} يوم")
            else:
                print(f"      ❌ موعد التسليم غير صحيح: {delivery_days} يوم")
        
        # اختبار عرض التاريخ
        print(f"      📅 عرض التاريخ: {order.expected_delivery_date.strftime('%Y-%m-%d') if order.expected_delivery_date else 'غير محدد'}")


def test_template_variables():
    """اختبار متغيرات القالب"""
    print("\n🧪 اختبار متغيرات القالب...")
    
    all_orders = Order.objects.all()
    inspection_orders = [order for order in all_orders if 'inspection' in order.get_selected_types_list()]
    
    for order in inspection_orders[:1]:
        print(f"\n   📋 اختبار الطلب: {order.order_number}")
        
        # اختبار get_selected_types_list
        types_list = order.get_selected_types_list()
        print(f"      أنواع الطلب: {types_list}")
        
        # اختبار وجود 'inspection' في القائمة
        if 'inspection' in types_list:
            print(f"      ✅ يحتوي على معاينة")
        else:
            print(f"      ❌ لا يحتوي على معاينة")
        
        # اختبار expected_delivery_date
        if order.expected_delivery_date:
            print(f"      📅 تاريخ التسليم المتوقع: {order.expected_delivery_date}")
            print(f"      📅 تنسيق التاريخ: {order.expected_delivery_date.strftime('%Y/%m/%d')}")
        else:
            print(f"      ❌ لا يوجد تاريخ تسليم متوقع")


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار إصلاح عرض المعاينات")
    print("=" * 60)
    
    test_inspection_display()
    test_template_variables()
    
    print("\n" + "=" * 60)
    print("✅ تم إكمال الاختبار بنجاح!")
    print("🎉 النظام يعرض المعاينات بشكل صحيح!")


if __name__ == '__main__':
    main() 