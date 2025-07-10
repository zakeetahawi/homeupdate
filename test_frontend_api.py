#!/usr/bin/env python3
"""
سكريبت لاختبار API الواجهة الأمامية مباشرة
"""

import requests
import json
import os
from time import sleep

def test_frontend_api():
    """اختبار API الواجهة الأمامية"""
    
    print("🔍 اختبار API الواجهة الأمامية...")
    
    base_url = "http://localhost:8000"
    
    # 1. اختبار إنشاء رمز مؤقت
    print("\n1. اختبار إنشاء رمز مؤقت...")
    try:
        response = requests.post(f"{base_url}/odoo-db-manager/generate-temp-token/", 
                               headers={'Content-Type': 'application/json'})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
            if data.get('success'):
                temp_token = data.get('temp_token')
                print(f"✅ تم إنشاء الرمز المؤقت: {temp_token[:10]}...")
            else:
                print(f"❌ فشل في إنشاء الرمز المؤقت: {data.get('error')}")
        else:
            print(f"❌ خطأ HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
    
    # 2. اختبار تحديث الجلسة
    print("\n2. اختبار تحديث الجلسة...")
    try:
        response = requests.post(f"{base_url}/odoo-db-manager/refresh-session/", 
                               headers={'Content-Type': 'application/json'})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
        else:
            print(f"❌ خطأ HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
    
    # 3. اختبار حالة التقدم (بدون جلسة)
    print("\n3. اختبار حالة التقدم...")
    test_session_id = "test_session_123"
    try:
        response = requests.get(f"{base_url}/odoo-db-manager/restore-progress/{test_session_id}/status/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
        elif response.status_code == 404:
            print("✅ متوقع - الجلسة غير موجودة")
        else:
            print(f"❌ خطأ HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
    
    # 4. اختبار صفحة الاستعادة
    print("\n4. اختبار صفحة الاستعادة...")
    try:
        response = requests.get(f"{base_url}/odoo-db-manager/backups/upload/5/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ صفحة الاستعادة متاحة")
        else:
            print(f"❌ خطأ HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
    
    print("\n🔍 انتهى اختبار API")

if __name__ == '__main__':
    test_frontend_api() 