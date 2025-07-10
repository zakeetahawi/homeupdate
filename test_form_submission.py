#!/usr/bin/env python
"""
سكريبت لاختبار إرسال النموذج مباشرة
"""
import requests
import json
from pathlib import Path

def test_form_submission():
    """اختبار إرسال النموذج"""
    
    print("🔍 اختبار إرسال النموذج...")
    
    # إعدادات الاختبار
    base_url = "http://127.0.0.1:8000"
    upload_url = f"{base_url}/odoo-db-manager/backups/upload/"
    
    # إنشاء session
    session = requests.Session()
    
    try:
        # 1. الحصول على صفحة النموذج أولاً لاستخراج CSRF token
        print("📋 الحصول على صفحة النموذج...")
        response = session.get(upload_url)
        print(f"✅ GET request status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ فشل في الحصول على الصفحة: {response.status_code}")
            return False
        
        # استخراج CSRF token
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            print("❌ لم يتم العثور على CSRF token")
            return False
        
        csrf_value = csrf_token.get('value')
        print(f"✅ CSRF token found: {csrf_value[:20]}...")
        
        # 2. إنشاء ملف اختبار صغير
        test_file_path = Path("test_backup_small.json")
        if not test_file_path.exists():
            print("❌ ملف الاختبار غير موجود")
            return False
        
        # 3. إرسال النموذج
        print("📤 إرسال النموذج...")
        
        # إعداد البيانات
        data = {
            'csrfmiddlewaretoken': csrf_value,
            'database_id': '1',  # افتراض وجود قاعدة بيانات برقم 1
            'backup_type': 'full',
            'clear_data': 'off',
            'session_id': 'test_session_' + str(int(time.time()))
        }
        
        # إعداد الملف
        with open(test_file_path, 'rb') as f:
            files = {
                'backup_file': ('test_backup_small.json', f, 'application/json')
            }
            
            # إرسال POST request
            response = session.post(
                upload_url,
                data=data,
                files=files,
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': upload_url
                }
            )
        
        print(f"📨 POST request status: {response.status_code}")
        print(f"📨 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"✅ JSON response: {response_data}")
                return response_data.get('success', False)
            except:
                print(f"⚠️ Response is not JSON: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"❌ Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        return False

if __name__ == "__main__":
    import time
    
    print("🚀 بدء اختبار إرسال النموذج...")
    print("📋 ملاحظة: تأكد من تشغيل الخادم على http://127.0.0.1:8000")
    print("📋 ملاحظة: تأكد من تسجيل الدخول في المتصفح")
    
    success = test_form_submission()
    
    if success:
        print("✅ الاختبار نجح!")
    else:
        print("❌ الاختبار فشل!")
        print("💡 تحقق من:")
        print("   - تشغيل الخادم")
        print("   - تسجيل الدخول")
        print("   - وجود قاعدة بيانات برقم 1")
        print("   - وجود ملف test_backup_small.json") 