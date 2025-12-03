#!/usr/bin/env python
"""
اختبار شامل لتسجيل الدخول - فحص جميع المراحل
"""
import os
import django
import requests
from bs4 import BeautifulSoup

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import User

print("="*60)
print("🔍 اختبار شامل لتسجيل الدخول")
print("="*60)

# 1. فحص المستخدم في قاعدة البيانات
print("\n1️⃣ فحص المستخدم في قاعدة البيانات...")
user = User.objects.filter(username='zakee.tahawi').first()
if user:
    print(f"   ✅ المستخدم موجود: {user.username}")
    print(f"   📧 البريد: {user.email}")
    print(f"   🟢 نشط: {user.is_active}")
    print(f"   👤 موظف: {user.is_staff}")
    print(f"   👑 مدير: {user.is_superuser}")
    print(f"   🔑 كلمة مرور صالحة: {user.has_usable_password()}")
else:
    print("   ❌ المستخدم غير موجود!")
    exit(1)

# 2. اختبار المصادقة من Django
print("\n2️⃣ اختبار المصادقة من Django...")
auth_user = authenticate(username='zakee.tahawi', password='2beornot2beE@#$')
if auth_user:
    print(f"   ✅ المصادقة نجحت: {auth_user.username}")
else:
    print("   ❌ المصادقة فشلت!")
    exit(1)

# 3. اختبار HTTP - الحصول على CSRF Token
print("\n3️⃣ اختبار HTTP - الحصول على صفحة تسجيل الدخول...")
session = requests.Session()
base_url = "http://192.168.1.30:8000"
login_url = f"{base_url}/accounts/login/"

try:
    response = session.get(login_url)
    print(f"   📊 كود الاستجابة: {response.status_code}")
    print(f"   🍪 Cookies: {list(session.cookies.keys())}")
    
    # استخراج CSRF token
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    
    if csrf_input:
        csrf_token = csrf_input.get('value')
        print(f"   🔑 CSRF Token: {csrf_token[:20]}...")
    else:
        print("   ❌ لم يتم العثور على CSRF Token!")
        exit(1)
        
except Exception as e:
    print(f"   ❌ خطأ في الاتصال: {e}")
    exit(1)

# 4. اختبار إرسال بيانات تسجيل الدخول
print("\n4️⃣ إرسال بيانات تسجيل الدخول...")
login_data = {
    'username': 'zakee.tahawi',
    'password': '2beornot2beE@#$',
    'csrfmiddlewaretoken': csrf_token,
}

headers = {
    'Referer': login_url,
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0',
}

try:
    response = session.post(login_url, data=login_data, headers=headers, allow_redirects=False)
    print(f"   📊 كود الاستجابة: {response.status_code}")
    print(f"   📍 Location Header: {response.headers.get('Location', 'N/A')}")
    print(f"   🍪 Cookies بعد الإرسال: {list(session.cookies.keys())}")
    
    if response.status_code == 302:
        redirect_to = response.headers.get('Location', '')
        if '/accounts/login/' in redirect_to:
            print("   ❌ تم التحويل إلى صفحة تسجيل الدخول (فشل)")
            print("\n🔍 فحص رسالة الخطأ...")
            error_response = session.get(login_url)
            soup = BeautifulSoup(error_response.text, 'html.parser')
            errors = soup.find_all('div', class_='alert-danger')
            if errors:
                for error in errors:
                    print(f"   ⚠️  {error.get_text(strip=True)}")
        else:
            print(f"   ✅ تم التحويل إلى: {redirect_to}")
            print("   🎉 تسجيل الدخول نجح!")
    elif response.status_code == 200:
        print("   ⚠️  لم يتم التحويل (200) - فحص الأخطاء...")
        soup = BeautifulSoup(response.text, 'html.parser')
        errors = soup.find_all('div', class_='alert-danger')
        for error in errors:
            print(f"   ❌ {error.get_text(strip=True)}")
    elif response.status_code == 403:
        print("   ❌ ممنوع (403) - مشكلة CSRF أو صلاحيات")
    else:
        print(f"   ⚠️  كود غير متوقع: {response.status_code}")
        
except Exception as e:
    print(f"   ❌ خطأ في إرسال البيانات: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ انتهى الاختبار")
print("="*60)
