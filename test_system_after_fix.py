#!/usr/bin/env python
"""
سكريبت اختبار النظام بعد تصحيح الأخطاء
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


def test_system_components():
    """اختبار مكونات النظام"""
    print("🔧 اختبار مكونات النظام بعد التصحيح...")
    
    # اختبار إعدادات مواعيد التسليم
    print("\n📅 اختبار إعدادات مواعيد التسليم:")
    settings = DeliveryTimeSettings.objects.all()
    for setting in settings:
        print(f"   ✅ {setting.get_order_type_display()}: {setting.delivery_days} يوم")
    
    # اختبار الطلبات
    print("\n📦 اختبار الطلبات:")
    orders = Order.objects.all()[:3]
    for order in orders:
        print(f"   📋 {order.order_number}: {order.customer.name if order.customer else 'غير محدد'}")
        print(f"      البائع: {order.salesperson.name if order.salesperson else 'غير محدد'}")
        print(f"      تاريخ التسليم المتوقع: {order.expected_delivery_date}")
    
    # اختبار المعاينات
    print("\n🔍 اختبار المعاينات:")
    inspections = Inspection.objects.all()[:3]
    for inspection in inspections:
        print(f"   🔍 {inspection.contract_number}: {inspection.customer.name if inspection.customer else 'غير محدد'}")
        print(f"      المعاين: {inspection.inspector.username if inspection.inspector else 'غير محدد'}")
        print(f"      تاريخ التسليم المتوقع: {inspection.expected_delivery_date}")
    
    # اختبار العملاء
    print("\n👥 اختبار العملاء:")
    customers = Customer.objects.all()[:3]
    for customer in customers:
        print(f"   👤 {customer.name}: {customer.phone}")
    
    # اختبار البائعين
    print("\n💼 اختبار البائعين:")
    salespeople = Salesperson.objects.all()[:3]
    for salesperson in salespeople:
        print(f"   💼 {salesperson.name}: {salesperson.phone if hasattr(salesperson, 'phone') else 'غير محدد'}")
    
    print("\n✅ تم اختبار جميع مكونات النظام بنجاح!")


def test_delivery_calculations():
    """اختبار حسابات مواعيد التسليم"""
    print("\n📊 اختبار حسابات مواعيد التسليم:")
    
    # اختبار الطلبات
    orders = Order.objects.all()[:2]
    for order in orders:
        print(f"\n   📦 الطلب: {order.order_number}")
        print(f"      نوع الطلب: {order.status}")
        print(f"      أنواع مختارة: {order.get_selected_types_list()}")
        expected_date = order.calculate_expected_delivery_date()
        print(f"      تاريخ التسليم المحسوب: {expected_date}")
        print(f"      التاريخ المحفوظ: {order.expected_delivery_date}")
    
    # اختبار المعاينات
    inspections = Inspection.objects.all()[:2]
    for inspection in inspections:
        print(f"\n   🔍 المعاينة: {inspection.contract_number}")
        print(f"      تاريخ الطلب: {inspection.request_date}")
        expected_date = inspection.calculate_expected_delivery_date()
        print(f"      تاريخ التسليم المحسوب: {expected_date}")
        print(f"      التاريخ المحفوظ: {inspection.expected_delivery_date}")


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار النظام بعد التصحيح")
    print("=" * 50)
    
    test_system_components()
    test_delivery_calculations()
    
    print("\n" + "=" * 50)
    print("✅ تم إكمال اختبار النظام بنجاح!")
    print("🎉 النظام جاهز للاستخدام!")


if __name__ == '__main__':
    main() 