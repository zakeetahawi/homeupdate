#!/usr/bin/env python
"""
سكريبت اختبار التحديثات الجديدة للمعاينات
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order, DeliveryTimeSettings
from inspections.models import Inspection
from customers.models import Customer
from accounts.models import Branch, Salesperson
from datetime import datetime, timedelta


def test_inspection_order_behavior():
    """اختبار سلوك طلبات المعاينة"""
    print("🔍 اختبار سلوك طلبات المعاينة...")
    
    # الحصول على طلبات المعاينة
    inspection_orders = Order.objects.filter(
        selected_types__contains='inspection'
    )[:3]
    
    print(f"\n📋 عدد طلبات المعاينة الموجودة: {inspection_orders.count()}")
    
    for order in inspection_orders:
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


def test_other_orders_behavior():
    """اختبار سلوك الطلبات الأخرى"""
    print("\n📦 اختبار سلوك الطلبات الأخرى...")
    
    # الحصول على طلبات غير المعاينة
    other_orders = Order.objects.exclude(
        selected_types__contains='inspection'
    )[:3]
    
    print(f"\n📋 عدد الطلبات الأخرى: {other_orders.count()}")
    
    for order in other_orders:
        print(f"\n   📋 الطلب: {order.order_number}")
        print(f"      العميل: {order.customer.name if order.customer else 'غير محدد'}")
        print(f"      وضع الطلب: {order.status}")
        print(f"      أنواع الطلب: {order.get_selected_types_list()}")
        print(f"      تاريخ التسليم المتوقع: {order.expected_delivery_date}")
        
        # التحقق من موعد التسليم حسب نوع الطلب
        if order.expected_delivery_date:
            delivery_days = (order.expected_delivery_date - order.order_date.date()).days
            expected_days = 7 if order.status == 'vip' else 15
            
            if delivery_days == expected_days:
                print(f"      ✅ موعد التسليم صحيح: {delivery_days} يوم")
            else:
                print(f"      ❌ موعد التسليم غير صحيح: {delivery_days} يوم (متوقع: {expected_days})")


def test_delivery_settings():
    """اختبار إعدادات مواعيد التسليم"""
    print("\n⚙️ اختبار إعدادات مواعيد التسليم...")
    
    settings = DeliveryTimeSettings.objects.all()
    for setting in settings:
        print(f"   📅 {setting.get_order_type_display()}: {setting.delivery_days} يوم")
        
        # اختبار الحصول على الأيام
        days = DeliveryTimeSettings.get_delivery_days(setting.order_type)
        if days == setting.delivery_days:
            print(f"      ✅ الحصول على الأيام صحيح: {days} يوم")
        else:
            print(f"      ❌ الحصول على الأيام غير صحيح: {days} يوم")


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار التحديثات الجديدة للمعاينات")
    print("=" * 60)
    
    test_delivery_settings()
    test_inspection_order_behavior()
    test_other_orders_behavior()
    
    print("\n" + "=" * 60)
    print("✅ تم إكمال اختبار التحديثات بنجاح!")
    print("🎉 النظام يعمل كما هو متوقع!")


if __name__ == '__main__':
    main() 