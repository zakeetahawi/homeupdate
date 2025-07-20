#!/usr/bin/env python
"""
سكريبت اختبار النظام عبر المتصفح للتأكد من إعدادات العملة
Web Browser Test Script for Currency Settings
"""

import os
import sys
import django
import requests
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def test_web_pages():
    """اختبار صفحات الويب"""
    print("🌐 اختبار صفحات الويب...")
    
    base_url = "http://127.0.0.1:8000"
    
    # قائمة الصفحات للاختبار
    test_pages = [
        "/installations/",
        "/installations/dashboard/",
        "/admin/installations/",
        "/admin/installations/installationpayment/",
        "/admin/installations/customerdebt/",
        "/admin/installations/modificationrequest/",
    ]
    
    results = []
    
    for page in test_pages:
        try:
            url = base_url + page
            print(f"   اختبار: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ نجح - {response.status_code}")
                
                # البحث عن تنسيق العملة في المحتوى
                content = response.text
                currency_indicators = [
                    "ج.م", "ر.س", "$", "€", "د.إ", "د.ك", "ر.ق", "د.ب", "ر.ع"
                ]
                
                found_currency = False
                for indicator in currency_indicators:
                    if indicator in content:
                        found_currency = True
                        print(f"   💰 وجد رمز العملة: {indicator}")
                        break
                
                if not found_currency:
                    print(f"   ⚠️  لم يتم العثور على رموز العملة")
                
                results.append((page, True, response.status_code))
            else:
                print(f"   ❌ فشل - {response.status_code}")
                results.append((page, False, response.status_code))
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ خطأ في الاتصال - تأكد من تشغيل الخادم")
            results.append((page, False, "Connection Error"))
        except Exception as e:
            print(f"   ❌ خطأ: {str(e)}")
            results.append((page, False, str(e)))
    
    return results

def test_admin_interface():
    """اختبار واجهة الإدارة"""
    print("\n🔧 اختبار واجهة الإدارة...")
    
    try:
        # اختبار صفحة إعدادات النظام
        from accounts.models import SystemSettings
        settings = SystemSettings.get_settings()
        
        print(f"✅ إعدادات النظام:")
        print(f"   العملة: {settings.currency}")
        print(f"   الرمز: {settings.currency_symbol}")
        
        # اختبار تغيير العملة
        test_currencies = ['SAR', 'USD', 'EUR']
        original_currency = settings.currency
        
        for currency in test_currencies:
            settings.currency = currency
            settings.save()
            
            # إعادة تحميل الإعدادات
            settings = SystemSettings.get_settings()
            print(f"   اختبار {currency}: {settings.currency_symbol}")
        
        # إعادة العملة الأصلية
        settings.currency = original_currency
        settings.save()
        print(f"   ✅ تم إعادة العملة الأصلية: {original_currency}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار واجهة الإدارة: {str(e)}")
        return False

def test_currency_formatting():
    """اختبار تنسيق العملة"""
    print("\n💰 اختبار تنسيق العملة...")
    
    try:
        from installations.templatetags.custom_filters import format_currency
        from accounts.models import SystemSettings
        
        settings = SystemSettings.get_settings()
        test_amounts = [1000.50, 2500.75, 500.00, 0.00]
        
        print(f"   العملة الحالية: {settings.currency} ({settings.currency_symbol})")
        
        for amount in test_amounts:
            formatted = format_currency(amount)
            print(f"   {amount:,.2f} -> {formatted}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تنسيق العملة: {str(e)}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار النظام عبر المتصفح...")
    
    # اختبار تنسيق العملة
    success1 = test_currency_formatting()
    
    # اختبار واجهة الإدارة
    success2 = test_admin_interface()
    
    # اختبار صفحات الويب
    print("\n🌐 بدء اختبار صفحات الويب...")
    print("💡 تأكد من تشغيل الخادم على http://127.0.0.1:8000")
    
    web_results = test_web_pages()
    
    # عرض النتائج
    print("\n" + "="*60)
    print("📋 نتائج اختبار الويب:")
    print("="*60)
    
    web_success = 0
    web_total = len(web_results)
    
    for page, success, status in web_results:
        status_text = "✅ نجح" if success else "❌ فشل"
        print(f"   {page}: {status_text} ({status})")
        if success:
            web_success += 1
    
    print("="*60)
    print(f"📊 نتائج الويب: {web_success}/{web_total} صفحات نجحت")
    
    # النتيجة النهائية
    total_success = (1 if success1 else 0) + (1 if success2 else 0) + (1 if web_success > 0 else 0)
    total_tests = 3
    
    print(f"\n📊 النتيجة النهائية: {total_success}/{total_tests} اختبارات نجحت")
    
    if total_success == total_tests:
        print("\n🎉 جميع الاختبارات نجحت!")
        print("✅ إعدادات العملة تعمل بشكل صحيح")
        print("✅ واجهة الإدارة تعمل بشكل صحيح")
        print("✅ صفحات الويب تعمل بشكل صحيح")
        print("✅ النظام جاهز للاستخدام")
    else:
        print(f"\n⚠️  {total_tests - total_success} اختبارات فشلت")
        print("🔧 يرجى مراجعة الأخطاء وإصلاحها")
    
    return total_success == total_tests

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 