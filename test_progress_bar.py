#!/usr/bin/env python3
"""
سكريبت اختبار لمعرفة سبب عدم ظهور شريط التقدم
"""

import requests
import json
import time

# إعدادات الاختبار
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/accounts/login/"
UPLOAD_URL = f"{BASE_URL}/odoo-db-manager/backups/upload/"

def test_progress_bar():
    """اختبار شريط التقدم"""
    
    print("🔍 اختبار شريط التقدم...")
    
    # إنشاء جلسة
    session = requests.Session()
    
    # الحصول على صفحة تسجيل الدخول للحصول على CSRF token
    print("📝 الحصول على CSRF token...")
    login_page = session.get(LOGIN_URL)
    if login_page.status_code != 200:
        print(f"❌ فشل في الوصول لصفحة تسجيل الدخول: {login_page.status_code}")
        return False
    
    # استخراج CSRF token
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(login_page.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    print(f"✅ تم الحصول على CSRF token")
    
    # تسجيل الدخول
    print("🔐 تسجيل الدخول...")
    login_data = {
        'username': 'zakee.tahawi',
        'password': 'zak123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    login_response = session.post(LOGIN_URL, data=login_data)
    if login_response.status_code != 200 and login_response.status_code != 302:
        print(f"❌ فشل في تسجيل الدخول: {login_response.status_code}")
        return False
    
    print("✅ تم تسجيل الدخول بنجاح")
    
    # الحصول على صفحة الرفع
    print("📄 الحصول على صفحة الرفع...")
    upload_page = session.get(UPLOAD_URL)
    if upload_page.status_code != 200:
        print(f"❌ فشل في الوصول لصفحة الرفع: {upload_page.status_code}")
        return False
    
    # استخراج CSRF token من صفحة الرفع
    soup = BeautifulSoup(upload_page.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
    print(f"✅ تم الحصول على CSRF token من صفحة الرفع")
    
    # إنشاء session_id
    import random
    import string
    session_id = 'test_' + ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    print(f"🆔 Session ID: {session_id}")
    
    # إنشاء ملف اختبار صغير
    test_data = {
        "test": "data",
        "items": [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
    }
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        test_file_path = f.name
    
    print(f"📁 تم إنشاء ملف اختبار: {test_file_path}")
    
    try:
        # رفع الملف
        print("📤 رفع الملف...")
        
        with open(test_file_path, 'rb') as f:
            files = {'backup_file': ('test_backup.json', f, 'application/json')}
            data = {
                'csrfmiddlewaretoken': csrf_token,
                'database_id': '3',
                'backup_type': 'full',
                'clear_data': 'off',
                'session_id': session_id,
                'confirm': 'on'
            }
            
            print(f"📋 البيانات المرسلة: {data}")
            
            # إرسال الطلب
            response = session.post(UPLOAD_URL, data=data, files=files)
            print(f"📊 استجابة الخادم: {response.status_code}")
            
            if response.status_code == 302:
                print("✅ تم رفع الملف بنجاح (إعادة توجيه)")
                
                # اختبار تتبع التقدم
                print("🔍 اختبار تتبع التقدم...")
                progress_url = f"{BASE_URL}/odoo-db-manager/restore-progress/{session_id}/status/"
                
                for i in range(10):  # اختبار لمدة 10 ثوان
                    try:
                        progress_response = session.get(progress_url)
                        print(f"📈 التقدم ({i+1}/10): {progress_response.status_code}")
                        
                        if progress_response.status_code == 200:
                            progress_data = progress_response.json()
                            print(f"   📊 البيانات: {progress_data}")
                            
                            if progress_data.get('status') in ['completed', 'failed']:
                                print("✅ انتهت العملية")
                                break
                        elif progress_response.status_code == 404:
                            print("❌ الجلسة غير موجودة")
                            break
                        else:
                            print(f"⚠️ خطأ في التتبع: {progress_response.status_code}")
                            
                    except Exception as e:
                        print(f"❌ خطأ في التتبع: {e}")
                    
                    time.sleep(1)
                
                return True
            else:
                print(f"❌ فشل في رفع الملف: {response.status_code}")
                print(f"📝 محتوى الاستجابة: {response.text[:500]}")
                return False
                
    finally:
        # حذف الملف المؤقت
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)
            print("🗑️ تم حذف الملف المؤقت")

if __name__ == "__main__":
    try:
        print("🚀 بدء اختبار شريط التقدم...")
        success = test_progress_bar()
        
        if success:
            print("\n✅ الاختبار مكتمل بنجاح!")
        else:
            print("\n❌ فشل في الاختبار")
            
    except Exception as e:
        print(f"\n💥 خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc() 