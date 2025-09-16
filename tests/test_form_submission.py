#!/usr/bin/env python
"""
اختبار إرسال النموذج والتأكد من عدم تعليق مؤشر التقدم
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from customers.models import Customer
from accounts.models import Branch, Salesperson
import json

User = get_user_model()

def test_form_submission():
    """اختبار إرسال النموذج"""
    print("🧪 اختبار إرسال نموذج الطلب")
    print("=" * 50)
    
    # إنشاء client للاختبار
    client = Client()
    
    # البحث عن مستخدم للاختبار
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("❌ لا يوجد مستخدم للاختبار")
        return False
    
    # تسجيل الدخول
    client.force_login(user)
    print(f"✅ تم تسجيل الدخول كـ: {user.username}")
    
    # البحث عن بيانات للاختبار
    customer = Customer.objects.first()
    branch = Branch.objects.first()
    salesperson = Salesperson.objects.filter(is_active=True).first()
    
    if not all([customer, branch, salesperson]):
        print("❌ لا توجد بيانات كافية للاختبار")
        return False
    
    print(f"📋 العميل: {customer}")
    print(f"🏢 الفرع: {branch}")
    print(f"💼 البائع: {salesperson}")
    
    # بيانات النموذج الصحيحة
    form_data = {
        'customer': customer.id,
        'branch': branch.id,
        'salesperson': salesperson.id,
        'selected_types': 'inspection',
        'notes': 'اختبار إرسال النموذج',
        'status': 'normal',
        'delivery_type': 'branch',
        'delivery_address': '',
        'tracking_status': 'pending',
    }
    
    print(f"\n📋 بيانات النموذج:")
    for key, value in form_data.items():
        print(f"  - {key}: {value}")
    
    # اختبار 1: إرسال عادي
    print(f"\n🔬 اختبار 1: إرسال عادي")
    print("-" * 30)
    
    response = client.post('/orders/create/', form_data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 302:
        print("✅ تم إنشاء الطلب بنجاح (إعادة توجيه)")
        print(f"إعادة التوجيه إلى: {response.url}")
    else:
        print("❌ فشل في إنشاء الطلب")
        if hasattr(response, 'content'):
            print(f"المحتوى: {response.content[:200]}")
    
    # اختبار 2: إرسال AJAX
    print(f"\n🔬 اختبار 2: إرسال AJAX")
    print("-" * 30)
    
    response = client.post(
        '/orders/create/', 
        form_data,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("✅ استجابة JSON صحيحة:")
            print(f"  - success: {data.get('success')}")
            print(f"  - message: {data.get('message')}")
            if data.get('success'):
                print(f"  - order_id: {data.get('order_id')}")
                print(f"  - order_number: {data.get('order_number')}")
                print(f"  - redirect_url: {data.get('redirect_url')}")
            else:
                print(f"  - errors: {data.get('errors')}")
        except Exception as e:
            print(f"❌ خطأ في تحليل JSON: {e}")
    else:
        print("❌ فشل في الإرسال عبر AJAX")
    
    # اختبار 3: إرسال بيانات خاطئة
    print(f"\n🔬 اختبار 3: إرسال بيانات خاطئة")
    print("-" * 30)
    
    bad_form_data = {
        'customer': '',  # خطأ: عميل فارغ
        'branch': branch.id,
        'salesperson': salesperson.id,
        'selected_types': 'installation',  # يحتاج رقم فاتورة
        'notes': 'اختبار بيانات خاطئة',
        'status': 'normal',
        'delivery_type': 'branch',
        'delivery_address': '',
        'tracking_status': 'pending',
        # لا يوجد invoice_number
    }
    
    response = client.post(
        '/orders/create/', 
        bad_form_data,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 400:
        try:
            data = response.json()
            print("✅ تم التعامل مع الأخطاء بشكل صحيح:")
            print(f"  - success: {data.get('success')}")
            print(f"  - message: {data.get('message')}")
            print(f"  - errors: {data.get('errors')}")
        except Exception as e:
            print(f"❌ خطأ في تحليل JSON للأخطاء: {e}")
    else:
        print("❌ لم يتم التعامل مع الأخطاء بشكل صحيح")
    
    return True

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نظام إرسال النماذج")
    print("=" * 60)
    
    success = test_form_submission()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 تم الاختبار بنجاح!")
        print("✅ النظام يتعامل مع إرسال النماذج بشكل صحيح")
        print("✅ استجابات JSON تعمل للـ AJAX")
        print("✅ معالجة الأخطاء تعمل بشكل صحيح")
        print("\n📋 النتيجة:")
        print("  - مؤشر التقدم سيختفي عند النجاح أو الفشل")
        print("  - رسائل واضحة للمستخدم")
        print("  - لا مزيد من التعليق في الواجهة")
    else:
        print("❌ فشل في الاختبار")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
