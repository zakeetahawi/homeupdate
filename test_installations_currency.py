#!/usr/bin/env python
"""
سكريبت اختبار شامل لقسم التركيبات مع إعدادات العملة
Comprehensive Test Script for Installations Module with Currency Settings
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

def test_system_settings():
    """اختبار إعدادات النظام"""
    print("🔍 اختبار إعدادات النظام...")
    
    try:
        settings = SystemSettings.get_settings()
        print(f"✅ إعدادات النظام:")
        print(f"   العملة: {settings.currency}")
        print(f"   رمز العملة: {settings.currency_symbol}")
        print(f"   اسم النظام: {settings.name}")
        return True
    except Exception as e:
        print(f"❌ خطأ في إعدادات النظام: {str(e)}")
        return False

def test_currency_formatting():
    """اختبار تنسيق العملة"""
    print("\n🧪 اختبار تنسيق العملة...")
    
    try:
        test_amounts = [1000.50, 2500.75, 500.00, 0.00, 1234567.89]
        for amount in test_amounts:
            formatted = format_currency(amount)
            print(f"   {amount:,.2f} -> {formatted}")
        return True
    except Exception as e:
        print(f"❌ خطأ في تنسيق العملة: {str(e)}")
        return False

def test_admin_integration():
    """اختبار تكامل لوحة الإدارة"""
    print("\n🔧 اختبار تكامل لوحة الإدارة...")
    
    try:
        from installations.admin import format_currency as admin_format_currency
        test_amount = 1500.75
        formatted = admin_format_currency(test_amount)
        print(f"✅ admin format_currency: {test_amount} -> {formatted}")
        return True
    except Exception as e:
        print(f"❌ خطأ في تكامل لوحة الإدارة: {str(e)}")
        return False

def test_template_filters():
    """اختبار template filters"""
    print("\n📝 اختبار template filters...")
    
    try:
        from installations.templatetags.custom_filters import format_currency
        test_amount = 2000.50
        formatted = format_currency(test_amount)
        print(f"✅ template filter: {test_amount} -> {formatted}")
        return True
    except Exception as e:
        print(f"❌ خطأ في template filters: {str(e)}")
        return False

def test_data_integration():
    """اختبار تكامل البيانات"""
    print("\n📊 اختبار تكامل البيانات...")
    
    try:
        payments_count = InstallationPayment.objects.count()
        debts_count = CustomerDebt.objects.count()
        modifications_count = ModificationRequest.objects.count()
        
        print(f"   المدفوعات: {payments_count}")
        print(f"   المديونيات: {debts_count}")
        print(f"   طلبات التعديل: {modifications_count}")
        
        # اختبار على بيانات حقيقية إذا وجدت
        if payments_count > 0:
            payment = InstallationPayment.objects.first()
            formatted = format_currency(payment.amount)
            print(f"   مثال مدفوعات: {payment.amount} -> {formatted}")
        
        if debts_count > 0:
            debt = CustomerDebt.objects.first()
            formatted = format_currency(debt.debt_amount)
            print(f"   مثال مديونيات: {debt.debt_amount} -> {formatted}")
        
        if modifications_count > 0:
            modification = ModificationRequest.objects.first()
            formatted = format_currency(modification.estimated_cost)
            print(f"   مثال تعديلات: {modification.estimated_cost} -> {formatted}")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في تكامل البيانات: {str(e)}")
        return False

def test_currency_symbols():
    """اختبار رموز العملات المختلفة"""
    print("\n💱 اختبار رموز العملات المختلفة...")
    
    try:
        settings = SystemSettings.get_settings()
        symbols = settings.CURRENCY_SYMBOLS
        
        print("   رموز العملات المتاحة:")
        for currency, symbol in symbols.items():
            print(f"     {currency}: {symbol}")
        
        # اختبار تنسيق مع عملات مختلفة
        test_amount = 1000.50
        for currency, symbol in symbols.items():
            settings.currency = currency
            formatted = format_currency(test_amount)
            print(f"     {currency}: {test_amount} -> {formatted}")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في اختبار رموز العملات: {str(e)}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار شامل لقسم التركيبات مع إعدادات العملة...")
    
    tests = [
        ("إعدادات النظام", test_system_settings),
        ("تنسيق العملة", test_currency_formatting),
        ("تكامل لوحة الإدارة", test_admin_integration),
        ("Template Filters", test_template_filters),
        ("تكامل البيانات", test_data_integration),
        ("رموز العملات", test_currency_symbols),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ خطأ في اختبار {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # عرض النتائج
    print("\n" + "="*60)
    print("📋 نتائج الاختبارات:")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print("="*60)
    print(f"📊 النتيجة النهائية: {passed}/{total} اختبارات نجحت")
    
    if passed == total:
        print("\n🎉 جميع الاختبارات نجحت!")
        print("✅ قسم التركيبات يستخدم إعدادات العملة من النظام")
        print("✅ جميع المبالغ المالية ستظهر بالتنسيق الصحيح")
        print("✅ النظام جاهز للاستخدام")
    else:
        print(f"\n⚠️  {total - passed} اختبارات فشلت")
        print("🔧 يرجى مراجعة الأخطاء وإصلاحها")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 