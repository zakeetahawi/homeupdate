#!/usr/bin/env python
"""
سكريبت اختبار نظام مواعيد التسليم الجديد
"""
import os
import sys
import django
from datetime import datetime, timedelta

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order, DeliveryTimeSettings
from inspections.models import Inspection
from customers.models import Customer
from accounts.models import Branch, Salesperson, User


def test_delivery_time_settings():
    """اختبار إعدادات مواعيد التسليم"""
    print("🔧 اختبار إعدادات مواعيد التسليم...")
    
    # التحقق من وجود الإعدادات
    settings = DeliveryTimeSettings.objects.all()
    print(f"   📊 عدد الإعدادات الموجودة: {settings.count()}")
    
    for setting in settings:
        print(f"   ✅ {setting.get_order_type_display()}: {setting.delivery_days} يوم")
    
    # اختبار الحصول على الأيام
    print("\n📅 اختبار الحصول على أيام التسليم:")
    for order_type in ['normal', 'vip', 'inspection']:
        days = DeliveryTimeSettings.get_delivery_days(order_type)
        print(f"   📋 {order_type}: {days} يوم")


def test_order_delivery_calculation():
    """اختبار حساب مواعيد التسليم للطلبات"""
    print("\n📦 اختبار حساب مواعيد التسليم للطلبات...")
    
    # الحصول على طلب للاختبار
    orders = Order.objects.all()[:3]
    
    for order in orders:
        print(f"\n   📋 الطلب: {order.order_number}")
        print(f"      نوع الطلب: {order.status}")
        print(f"      أنواع مختارة: {order.get_selected_types_list()}")
        
        # حساب التاريخ المتوقع
        expected_date = order.calculate_expected_delivery_date()
        print(f"      تاريخ التسليم المتوقع: {expected_date}")
        
        if order.expected_delivery_date:
            print(f"      التاريخ المحفوظ: {order.expected_delivery_date}")


def test_inspection_delivery_calculation():
    """اختبار حساب مواعيد التسليم للمعاينات"""
    print("\n🔍 اختبار حساب مواعيد التسليم للمعاينات...")
    
    # الحصول على معاينة للاختبار
    inspections = Inspection.objects.all()[:3]
    
    for inspection in inspections:
        print(f"\n   🔍 المعاينة: {inspection.contract_number}")
        print(f"      تاريخ الطلب: {inspection.request_date}")
        
        # حساب التاريخ المتوقع
        expected_date = inspection.calculate_expected_delivery_date()
        print(f"      تاريخ التسليم المتوقع: {expected_date}")
        
        if inspection.expected_delivery_date:
            print(f"      التاريخ المحفوظ: {inspection.expected_delivery_date}")


def create_test_data():
    """إنشاء بيانات اختبار"""
    print("\n🧪 إنشاء بيانات اختبار...")
    
    try:
        # الحصول على فرع وبائع وعميل
        branch = Branch.objects.first()
        salesperson = Salesperson.objects.first()
        customer = Customer.objects.first()
        
        if not all([branch, salesperson, customer]):
            print("   ❌ لا توجد بيانات كافية للاختبار")
            return
        
        # إنشاء طلب عادي
        normal_order = Order.objects.create(
            customer=customer,
            salesperson=salesperson,
            branch=branch,
            status='normal',
            selected_types=['accessory'],
            order_number=f"TEST-NORMAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            invoice_number="TEST-INV-001"
        )
        print(f"   ✅ تم إنشاء طلب عادي: {normal_order.order_number}")
        
        # إنشاء طلب VIP
        vip_order = Order.objects.create(
            customer=customer,
            salesperson=salesperson,
            branch=branch,
            status='vip',
            selected_types=['tailoring'],
            order_number=f"TEST-VIP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            invoice_number="TEST-INV-002"
        )
        print(f"   ✅ تم إنشاء طلب VIP: {vip_order.order_number}")
        
        # إنشاء طلب معاينة
        inspection_order = Order.objects.create(
            customer=customer,
            salesperson=salesperson,
            branch=branch,
            status='normal',
            selected_types=['inspection'],
            order_number=f"TEST-INSP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            invoice_number="TEST-INV-003"
        )
        print(f"   ✅ تم إنشاء طلب معاينة: {inspection_order.order_number}")
        
        # إنشاء معاينة
        inspection = Inspection.objects.create(
            customer=customer,
            branch=branch,
            responsible_employee=salesperson,
            contract_number=f"TEST-CONTRACT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            request_date=datetime.now().date(),
            scheduled_date=(datetime.now() + timedelta(days=1)).date(),
            status='pending',
            order=inspection_order
        )
        print(f"   ✅ تم إنشاء معاينة: {inspection.contract_number}")
        
        print("\n   🎉 تم إنشاء بيانات الاختبار بنجاح!")
        
    except Exception as e:
        print(f"   ❌ خطأ في إنشاء بيانات الاختبار: {e}")


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار نظام مواعيد التسليم الجديد")
    print("=" * 50)
    
    # اختبار الإعدادات
    test_delivery_time_settings()
    
    # إنشاء بيانات اختبار
    create_test_data()
    
    # اختبار حساب مواعيد التسليم للطلبات
    test_order_delivery_calculation()
    
    # اختبار حساب مواعيد التسليم للمعاينات
    test_inspection_delivery_calculation()
    
    print("\n" + "=" * 50)
    print("✅ تم إكمال اختبار نظام مواعيد التسليم بنجاح!")


if __name__ == '__main__':
    main() 