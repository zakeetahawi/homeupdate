#!/usr/bin/env python
"""
سكريپت بسيط لاختبار الواجهة الأمامية
"""
import requests

def test_frontend():
    """اختبار الواجهة الأمامية"""
    
    print("🔍 اختبار الواجهة الأمامية...")
    
    base_url = "http://127.0.0.1:8000"
    upload_url = f"{base_url}/odoo-db-manager/backups/upload/"
    
    try:
        # اختبار GET request
        print("📋 اختبار GET request...")
        response = requests.get(upload_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ الصفحة تحمل بنجاح")
            
            # البحث عن النموذج
            if 'id="restoreForm"' in response.text:
                print("✅ النموذج موجود")
            else:
                print("❌ النموذج غير موجود")
                
            # البحث عن الزر
            if 'id="restoreBtn"' in response.text:
                print("✅ الزر موجود")
            else:
                print("❌ الزر غير موجود")
                
            # البحث عن JavaScript
            if 'function initializeRestoreSystem' in response.text:
                print("✅ JavaScript موجود")
            else:
                print("❌ JavaScript غير موجود")
                
        else:
            print(f"❌ فشل في تحميل الصفحة: {response.status_code}")
            
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    test_frontend() 