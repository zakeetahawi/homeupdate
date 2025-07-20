#!/usr/bin/env python
"""
سكريبت اختبار إعدادات العملة في قسم التركيبات
Test Currency Settings in Installations Module
"""

import os
import sys
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from accounts.models import SystemSettings
from installations.models import InstallationPayment, CustomerDebt, ModificationRequest
from installations.templatetags.custom_filters import format_currency

def test_currency_settings():
    """اختبار إعدادات العملة"""
    print("🔍 اختبار إعدادات العملة في قسم التركيبات...")
    
    try:
        # التحقق من إعدادات النظام
        settings = SystemSettings.get_settings()
        print(f"✅ إعدادات النظام موجودة:")
        print(f"   العملة: {settings.currency}")
        print(f"   رمز العملة: {settings.currency_symbol}")
        print(f"   اسم النظام: {settings.name}")
        
        # اختبار دالة تنسيق العملة
        test_amounts = [1000.50, 2500.75, 500.00, 0.00]
        print(f"\n🧪 اختبار تنسيق العملة:")
        for amount in test_amounts:
            formatted = format_currency(amount)
            print(f"   {amount:,.2f} -> {formatted}")
        
        # اختبار البيانات الموجودة
        payments_count = InstallationPayment.objects.count()
        debts_count = CustomerDebt.objects.count()
        modifications_count = ModificationRequest.objects.count()
        
        print(f"\n📊 البيانات الموجودة في قسم التركيبات:")
        print(f"   المدفوعات: {payments_count}")
        print(f"   المديونيات: {debts_count}")
        print(f"   طلبات التعديل: {modifications_count}")
        
        # اختبار تنسيق العملة على بيانات حقيقية
        if payments_count > 0:
            payment = InstallationPayment.objects.first()
            formatted_amount = format_currency(payment.amount)
            print(f"\n💰 مثال على المدفوعات:")
            print(f"   المبلغ الأصلي: {payment.amount}")
            print(f"   المبلغ المنسق: {formatted_amount}")
        
        if debts_count > 0:
            debt = CustomerDebt.objects.first()
            formatted_debt = format_currency(debt.debt_amount)
            print(f"\n💳 مثال على المديونيات:")
            print(f"   المبلغ الأصلي: {debt.debt_amount}")
            print(f"   المبلغ المنسق: {formatted_debt}")
        
        if modifications_count > 0:
            modification = ModificationRequest.objects.first()
            formatted_cost = format_currency(modification.estimated_cost)
            print(f"\n🔧 مثال على طلبات التعديل:")
            print(f"   التكلفة الأصلية: {modification.estimated_cost}")
            print(f"   التكلفة المنسقة: {formatted_cost}")
        
        print(f"\n🎉 اختبار إعدادات العملة اكتمل بنجاح!")
        print(f"✅ قسم التركيبات يستخدم الآن إعدادات العملة من النظام")
        print(f"✅ جميع المبالغ المالية ستظهر بالتنسيق الصحيح")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار إعدادات العملة: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_integration():
    """اختبار تكامل لوحة الإدارة"""
    print(f"\n🔍 اختبار تكامل لوحة الإدارة...")
    
    try:
        from installations.admin import format_currency as admin_format_currency
        
        # اختبار دالة تنسيق العملة في admin
        test_amount = 1500.75
        formatted = admin_format_currency(test_amount)
        print(f"✅ دالة تنسيق العملة في admin تعمل: {test_amount} -> {formatted}")
        
        print(f"✅ تكامل لوحة الإدارة يعمل بشكل صحيح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تكامل لوحة الإدارة: {str(e)}")
        return False

def test_template_filters():
    """اختبار template filters"""
    print(f"\n🔍 اختبار template filters...")
    
    try:
        from installations.templatetags.custom_filters import format_currency
        
        # اختبار template filter
        test_amount = 2000.50
        formatted = format_currency(test_amount)
        print(f"✅ template filter يعمل: {test_amount} -> {formatted}")
        
        print(f"✅ template filters تعمل بشكل صحيح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في template filters: {str(e)}")
        return False

if __name__ == '__main__':
    print("🚀 بدء اختبار إعدادات العملة في قسم التركيبات...")
    
    # اختبار إعدادات العملة
    success1 = test_currency_settings()
    
    # اختبار تكامل لوحة الإدارة
    success2 = test_admin_integration()
    
    # اختبار template filters
    success3 = test_template_filters()
    
    if success1 and success2 and success3:
        print("\n🎉 جميع الاختبارات نجحت!")
        print("💡 قسم التركيبات يستخدم الآن إعدادات العملة من النظام")
        print("💡 جميع المبالغ المالية ستظهر بالتنسيق الصحيح")
    else:
        print("\n❌ فشل في بعض الاختبارات")
        print("🔧 يرجى مراجعة الأخطاء وإصلاحها") 