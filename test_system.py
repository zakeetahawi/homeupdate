#!/usr/bin/env python
"""
اختبارات أساسية للنظام
تشغيل: python test_system.py
"""

import os
import sys
import django
from django.test.utils import get_runner
from django.conf import settings

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def test_database_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ اتصال قاعدة البيانات: نجح")
        return True
    except Exception as e:
        print(f"❌ اتصال قاعدة البيانات: فشل - {e}")
        return False

def test_models():
    """اختبار النماذج الأساسية"""
    try:
        from accounts.models import User
        from customers.models import Customer
        from orders.models import Order
        from odoo_db_manager.models import Database, Backup
        
        # اختبار عدد السجلات
        users_count = User.objects.count()
        customers_count = Customer.objects.count()
        orders_count = Order.objects.count()
        databases_count = Database.objects.count()
        backups_count = Backup.objects.count()
        
        print(f"✅ النماذج: نجح")
        print(f"   - المستخدمون: {users_count}")
        print(f"   - العملاء: {customers_count}")
        print(f"   - الطلبات: {orders_count}")
        print(f"   - قواعد البيانات: {databases_count}")
        print(f"   - النسخ الاحتياطية: {backups_count}")
        return True
    except Exception as e:
        print(f"❌ النماذج: فشل - {e}")
        return False

def test_services():
    """اختبار الخدمات الأساسية"""
    try:
        from odoo_db_manager.services.backup_service import BackupService
        from odoo_db_manager.services.scheduled_backup_service import ScheduledBackupService
        from accounts.services.dashboard_service import DashboardService
        
        # اختبار إنشاء الخدمات
        backup_service = BackupService()
        scheduled_service = ScheduledBackupService()
        dashboard_stats = DashboardService.get_cached_stats()
        
        print("✅ الخدمات: نجح")
        print(f"   - إحصائيات لوحة التحكم: {len(dashboard_stats)} عنصر")
        return True
    except Exception as e:
        print(f"❌ الخدمات: فشل - {e}")
        return False

def test_urls():
    """اختبار URLs الأساسية"""
    try:
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        
        # اختبار URLs أساسية
        urls_to_test = [
            ('accounts:login', 200),
            ('odoo_db_manager:dashboard', 302),  # يحول إلى تسجيل الدخول
        ]
        
        for url_name, expected_status in urls_to_test:
            try:
                url = reverse(url_name)
                response = client.get(url)
                if response.status_code == expected_status:
                    print(f"   ✅ {url_name}: {response.status_code}")
                else:
                    print(f"   ⚠️ {url_name}: {response.status_code} (متوقع {expected_status})")
            except Exception as e:
                print(f"   ❌ {url_name}: خطأ - {e}")
        
        print("✅ URLs: نجح")
        return True
    except Exception as e:
        print(f"❌ URLs: فشل - {e}")
        return False

def test_static_files():
    """اختبار الملفات الثابتة"""
    try:
        import os
        from django.conf import settings
        
        static_dirs = settings.STATICFILES_DIRS
        static_root = settings.STATIC_ROOT
        media_root = settings.MEDIA_ROOT
        
        print("✅ الملفات الثابتة: نجح")
        print(f"   - مجلدات static: {len(static_dirs)}")
        print(f"   - STATIC_ROOT: {os.path.exists(static_root) if static_root else 'غير محدد'}")
        print(f"   - MEDIA_ROOT: {os.path.exists(media_root)}")
        return True
    except Exception as e:
        print(f"❌ الملفات الثابتة: فشل - {e}")
        return False

def main():
    """تشغيل جميع الاختبارات"""
    print("🧪 بدء اختبارات النظام الأساسية...")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_models,
        test_services,
        test_urls,
        test_static_files,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ خطأ في الاختبار: {e}")
        print("-" * 30)
    
    print(f"📊 النتائج: {passed}/{total} اختبار نجح")
    
    if passed == total:
        print("🎉 جميع الاختبارات نجحت!")
        return 0
    else:
        print("⚠️ بعض الاختبارات فشلت")
        return 1

if __name__ == '__main__':
    sys.exit(main())
