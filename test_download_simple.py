#!/usr/bin/env python3
"""
اختبار بسيط لوظيفة التحميل
========================

هذا السكريپت يختبر:
1. وظيفة التحميل من الخادم
2. تحديد نوع المحتوى الصحيح
3. إعدادات headers للتحميل
"""

import os
import sys
import django
import tempfile
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from odoo_db_manager.models import Database, Backup

def test_download_headers():
    """اختبار headers التحميل"""
    print("🔍 اختبار headers التحميل...")

    # إنشاء ملف اختبار
    test_data = {"test": "data", "timestamp": "2025-01-24"}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False)
        temp_path = f.name

    try:
        # إنشاء قاعدة بيانات اختبار
        database = Database.objects.create(
            name="Test DB",
            db_type="postgresql",
            connection_info={}
        )

        # إنشاء نسخة احتياطية اختبار
        backup = Backup.objects.create(
            name="Test Backup",
            database=database,
            backup_type="test",
            file_path=temp_path
        )

        # إنشاء مستخدم مميز
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'email': 'test@test.com'
            }
        )

        # اختبار التحميل
        client = Client()
        client.force_login(user)

        url = reverse('odoo_db_manager:backup_download', args=[backup.id])
        response = client.get(url)

        print(f"📊 حالة الاستجابة: {response.status_code}")
        print(f"📊 Content-Type: {response.get('Content-Type', 'غير محدد')}")
        print(f"📊 Content-Disposition: {response.get('Content-Disposition', 'غير محدد')}")
        print(f"📊 Content-Length: {response.get('Content-Length', 'غير محدد')}")

        # فحص النتائج
        success = True

        if response.status_code != 200:
            print(f"❌ حالة الاستجابة خاطئة: {response.status_code}")
            success = False

        content_type = response.get('Content-Type', '')
        if content_type != 'application/octet-stream':
            print(f"⚠️ Content-Type غير مثالي: {content_type}")

        content_disposition = response.get('Content-Disposition', '')
        if 'attachment' not in content_disposition:
            print(f"❌ Content-Disposition لا يحتوي على attachment")
            success = False

        if success:
            print("✅ جميع headers صحيحة للتحميل")

        # تنظيف
        backup.delete()
        database.delete()

        return success

    except Exception as e:
        print(f"❌ خطأ في الاختبار: {str(e)}")
        return False

    finally:
        # حذف الملف المؤقت
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار بسيط لوظيفة التحميل")
    print("="*40)

    success = test_download_headers()

    if success:
        print("\n🎉 الاختبار نجح!")
        print("💡 وظيفة التحميل تعمل بشكل صحيح")
    else:
        print("\n❌ الاختبار فشل")
        print("💡 راجع إعدادات التحميل")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ خطأ عام: {str(e)}")
        sys.exit(1)
