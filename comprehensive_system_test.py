#!/usr/bin/env python3
"""
اختبار شامل لنظام إدارة المنزل
يختبر جميع الروابط والوظائف الأساسية
"""

import os
import sys
import django
import requests
import time
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import UnifiedSystemSettings, Branch, Department, Notification

User = get_user_model()

class SystemTester:
    def __init__(self):
        self.client = Client()
        self.base_url = "http://127.0.0.1:8000"
        self.results = []
        self.errors = []
        
    def log_result(self, test_name, status, message=""):
        """تسجيل نتيجة الاختبار"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': timestamp
        }
        self.results.append(result)
        
        # طباعة النتيجة مع الألوان
        if status == "✅ نجح":
            print(f"\033[92m[{timestamp}] ✅ {test_name}\033[0m")
        elif status == "❌ فشل":
            print(f"\033[91m[{timestamp}] ❌ {test_name}: {message}\033[0m")
        else:
            print(f"\033[93m[{timestamp}] ⚠️ {test_name}: {message}\033[0m")
    
    def test_server_connection(self):
        """اختبار الاتصال بالخادم"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.log_result("اتصال الخادم", "✅ نجح")
                return True
            else:
                self.log_result("اتصال الخادم", "❌ فشل", f"رمز الاستجابة: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("اتصال الخادم", "❌ فشل", str(e))
            return False
    
    def test_admin_login(self):
        """اختبار تسجيل الدخول للإدارة"""
        try:
            # إنشاء مستخدم admin إذا لم يكن موجود
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@example.com',
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
            
            # تسجيل الدخول
            login_success = self.client.login(username='admin', password='admin123')
            if login_success:
                self.log_result("تسجيل دخول الإدارة", "✅ نجح")
                return True
            else:
                self.log_result("تسجيل دخول الإدارة", "❌ فشل", "فشل في تسجيل الدخول")
                return False
        except Exception as e:
            self.log_result("تسجيل دخول الإدارة", "❌ فشل", str(e))
            return False
    
    def test_admin_pages(self):
        """اختبار صفحات الإدارة"""
        admin_pages = [
            ('/', 'الصفحة الرئيسية للإدارة'),
            ('/admin/accounts/', 'إدارة الحسابات'),
            ('/admin/accounts/unifiedsystemsettings/', 'إعدادات النظام الموحدة'),
            ('/admin/accounts/user/', 'إدارة المستخدمين'),
            ('/admin/accounts/branch/', 'إدارة الفروع'),
            ('/admin/accounts/department/', 'إدارة الأقسام'),
            ('/admin/accounts/notification/', 'إدارة الإشعارات'),
            ('/admin/customers/', 'إدارة العملاء'),
            ('/admin/orders/', 'إدارة الطلبات'),
            ('/admin/inventory/', 'إدارة المخزون'),
            ('/admin/manufacturing/', 'إدارة التصنيع'),
            ('/admin/inspections/', 'إدارة الفحص'),
            ('/admin/reports/', 'إدارة التقارير'),
        ]
        
        success_count = 0
        for url, description in admin_pages:
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    self.log_result(f"صفحة الإدارة: {description}", "✅ نجح")
                    success_count += 1
                else:
                    self.log_result(f"صفحة الإدارة: {description}", "❌ فشل", f"رمز الاستجابة: {response.status_code}")
            except Exception as e:
                self.log_result(f"صفحة الإدارة: {description}", "❌ فشل", str(e))
        
        return success_count == len(admin_pages)
    
    def test_frontend_pages(self):
        """اختبار صفحات الواجهة الأمامية"""
        frontend_pages = [
            ('/', 'الصفحة الرئيسية'),
            ('/accounts/login/', 'صفحة تسجيل الدخول'),
            ('/customers/', 'صفحة العملاء'),
            ('/orders/', 'صفحة الطلبات'),
            ('/inventory/', 'صفحة المخزون'),
            ('/manufacturing/', 'صفحة التصنيع'),
            ('/inspections/', 'صفحة الفحص'),
            ('/reports/', 'صفحة التقارير'),
        ]
        
        success_count = 0
        for url, description in frontend_pages:
            try:
                response = self.client.get(url)
                if response.status_code in [200, 302]:  # 302 للتحويل إلى تسجيل الدخول
                    self.log_result(f"صفحة الواجهة: {description}", "✅ نجح")
                    success_count += 1
                else:
                    self.log_result(f"صفحة الواجهة: {description}", "❌ فشل", f"رمز الاستجابة: {response.status_code}")
            except Exception as e:
                self.log_result(f"صفحة الواجهة: {description}", "❌ فشل", str(e))
        
        return success_count == len(frontend_pages)
    
    def test_unified_settings(self):
        """اختبار إعدادات النظام الموحدة"""
        try:
            settings = UnifiedSystemSettings.objects.first()
            if settings:
                self.log_result("إعدادات النظام الموحدة", "✅ نجح", f"تم العثور على إعدادات: {settings.company_name}")
                return True
            else:
                self.log_result("إعدادات النظام الموحدة", "❌ فشل", "لم يتم العثور على إعدادات موحدة")
                return False
        except Exception as e:
            self.log_result("إعدادات النظام الموحدة", "❌ فشل", str(e))
            return False
    
    def test_database_models(self):
        """اختبار نماذج قاعدة البيانات"""
        models_to_test = [
            (User, 'المستخدمين'),
            (Branch, 'الفروع'),
            (Department, 'الأقسام'),
            (Notification, 'الإشعارات'),
            (UnifiedSystemSettings, 'إعدادات النظام الموحدة'),
        ]
        
        success_count = 0
        for model, description in models_to_test:
            try:
                count = model.objects.count()
                self.log_result(f"نموذج {description}", "✅ نجح", f"عدد السجلات: {count}")
                success_count += 1
            except Exception as e:
                self.log_result(f"نموذج {description}", "❌ فشل", str(e))
        
        return success_count == len(models_to_test)
    
    def test_api_endpoints(self):
        """اختبار نقاط النهاية API"""
        api_endpoints = [
            ('/api/notifications/', 'API الإشعارات'),
            ('/api/notifications/unread/', 'API الإشعارات غير المقروءة'),
        ]
        
        success_count = 0
        for url, description in api_endpoints:
            try:
                response = self.client.get(url)
                if response.status_code in [200, 401, 403]:  # 401/403 مقبول للاختبار
                    self.log_result(f"API: {description}", "✅ نجح")
                    success_count += 1
                else:
                    self.log_result(f"API: {description}", "❌ فشل", f"رمز الاستجابة: {response.status_code}")
            except Exception as e:
                self.log_result(f"API: {description}", "❌ فشل", str(e))
        
        return success_count == len(api_endpoints)
    
    def run_comprehensive_test(self):
        """تشغيل الاختبار الشامل"""
        print("\n" + "="*60)
        print("🚀 بدء الاختبار الشامل لنظام إدارة المنزل")
        print("="*60)
        
        # اختبار الاتصال
        if not self.test_server_connection():
            print("\n❌ فشل في الاتصال بالخادم. تأكد من تشغيل الخادم.")
            return False
        
        # اختبار تسجيل الدخول
        if not self.test_admin_login():
            print("\n❌ فشل في تسجيل دخول الإدارة.")
            return False
        
        # اختبار نماذج قاعدة البيانات
        self.test_database_models()
        
        # اختبار إعدادات النظام الموحدة
        self.test_unified_settings()
        
        # اختبار صفحات الإدارة
        self.test_admin_pages()
        
        # اختبار صفحات الواجهة الأمامية
        self.test_frontend_pages()
        
        # اختبار API
        self.test_api_endpoints()
        
        # إحصائيات النتائج
        successful_tests = len([r for r in self.results if r['status'] == "✅ نجح"])
        failed_tests = len([r for r in self.results if r['status'] == "❌ فشل"])
        total_tests = len(self.results)
        
        print("\n" + "="*60)
        print("📊 نتائج الاختبار الشامل")
        print("="*60)
        print(f"✅ الاختبارات الناجحة: {successful_tests}")
        print(f"❌ الاختبارات الفاشلة: {failed_tests}")
        print(f"📈 إجمالي الاختبارات: {total_tests}")
        print(f"📊 نسبة النجاح: {(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "📊 نسبة النجاح: 0%")
        
        if failed_tests == 0:
            print("\n🎉 جميع الاختبارات نجحت! النظام جاهز للاستخدام.")
        else:
            print(f"\n⚠️ هناك {failed_tests} اختبار فشل. راجع الأخطاء أعلاه.")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = SystemTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1) 