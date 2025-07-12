#!/usr/bin/env python
"""
سكريبت تحديث الطلبات الموجودة لتطبيق النظام الجديد للمعاينات
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order, DeliveryTimeSettings
from datetime import datetime, timedelta


def update_existing_inspection_orders():
    """تحديث الطلبات الموجودة لتطبيق النظام الجديد للمعاينات"""
    print("🔄 تحديث الطلبات الموجودة...")
    
    # الحصول على جميع طلبات المعاينة
    inspection_orders = Order.objects.filter(
        selected_types__contains='inspection'
    )
    
    print(f"📋 عدد طلبات المعاينة الموجودة: {inspection_orders.count()}")
    
    updated_count = 0
    for order in inspection_orders:
        print(f"\n   📋 تحديث الطلب: {order.order_number}")
        print(f"      العميل: {order.customer.name if order.customer else 'غير محدد'}")
        print(f"      وضع الطلب الحالي: {order.status}")
        print(f"      تاريخ التسليم الحالي: {order.expected_delivery_date}")
        
        # تحديث وضع الطلب إلى عادي للمعاينات
        if order.status != 'normal':
            order.status = 'normal'
            print(f"      ✅ تم تحديث وضع الطلب إلى: عادي")
        
        # إعادة حساب تاريخ التسليم المتوقع
        old_delivery_date = order.expected_delivery_date
        order.expected_delivery_date = order.calculate_expected_delivery_date()
        
        if old_delivery_date != order.expected_delivery_date:
            print(f"      ✅ تم تحديث تاريخ التسليم من {old_delivery_date} إلى {order.expected_delivery_date}")
        else:
            print(f"      ℹ️ تاريخ التسليم لم يتغير: {order.expected_delivery_date}")
        
        # حفظ التحديثات
        order.save(update_fields=['status', 'expected_delivery_date'])
        updated_count += 1
    
    print(f"\n✅ تم تحديث {updated_count} طلب بنجاح!")


def verify_delivery_settings():
    """التحقق من إعدادات مواعيد التسليم"""
    print("\n⚙️ التحقق من إعدادات مواعيد التسليم...")
    
    settings = DeliveryTimeSettings.objects.all()
    for setting in settings:
        print(f"   📅 {setting.get_order_type_display()}: {setting.delivery_days} يوم")
        
        # اختبار الحصول على الأيام
        days = DeliveryTimeSettings.get_delivery_days(setting.order_type)
        if days == setting.delivery_days:
            print(f"      ✅ الحصول على الأيام صحيح: {days} يوم")
        else:
            print(f"      ❌ الحصول على الأيام غير صحيح: {days} يوم")


def test_updated_orders():
    """اختبار الطلبات المحدثة"""
    print("\n🧪 اختبار الطلبات المحدثة...")
    
    inspection_orders = Order.objects.filter(
        selected_types__contains='inspection'
    )[:3]
    
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


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء تحديث الطلبات الموجودة")
    print("=" * 60)
    
    verify_delivery_settings()
    update_existing_inspection_orders()
    test_updated_orders()
    
    print("\n" + "=" * 60)
    print("✅ تم إكمال التحديث بنجاح!")
    print("🎉 جميع الطلبات محدثة ومتسقة مع النظام الجديد!")


if __name__ == '__main__':
    main() 