#!/usr/bin/env python3
"""
اختبار وظيفة التحميل
==================

هذا السكريپت يختبر:
1. وظيفة التحميل في النظام
2. تحديد نوع المحتوى الصحيح
3. إعدادات headers للتحميل
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from odoo_db_manager.models import Backup, Database
from django.urls import reverse
import tempfile
import json

def create_test_backup():
    """إنشاء نسخة احتياطية اختبارية"""
    print("🔧 إنشاء نسخة احتياطية اختبارية...")

    # إنشاء ملف اختبار
    test_data = [
        {
            "model": "customers.customer",
            "pk": 1,
            "fields": {
                "name": "عميل اختبار",
                "phone": "0500000000"
            }
        }
    ]

    # إنشاء ملف مؤقت
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
        temp_file_path = f.name

    # الحصول على قاعدة بيانات أو إنشاء واحدة
    database = Database.objects.first()
    if not database:
        database = Database.objects.create(
            name="Test Database",
            db_type="postgresql",
            connection_info={}
        )

    # إنشاء سجل النسخة الاحتياطية
    backup = Backup.objects.create(
        name="Test Backup for Download",
        database=database,
        backup_type="test",
        file_path=temp_file_path
    )

    print(f"✅ تم إنشاء نسخة احتياطية اختبارية: {backup.id}")
    return backup, temp_file_path

def test_download_response(backup):
    """اختبار استجابة التحميل"""
    print(f"🔍 اختبار استجابة التحميل للنسخة الاحتياطية {backup.id}...")

    # إنشاء مستخدم للاختبار
    User = get_user_model()
    user = User.objects.filter(is_staff=True).first()
    if not user:
        user = User.objects.create_superuser(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    # إنشاء client للاختبار
    client = Client()
    client.force_login(user)

    # طلب التحميل
    download_url = reverse('odoo_db_manager:backup_download', args=[backup.id])
    print(f"🔗 رابط التحميل: {download_url}")

    response = client.get(download_url)

    # فحص الاستجابة
    print(f"📊 حالة الاستجابة: {response.status_code}")
    print(f"📊 نوع المحتوى: {response.get('Content-Type', 'غير محدد')}")
    print(f"📊 Content-Disposition: {response.get('Content-Disposition', 'غير محدد')}")
    print(f"📊 حجم المحتوى: {response.get('Content-Length', 'غير محدد')} bytes")

    # فحص headers أخرى
    important_headers = [
        'Cache-Control',
        'Pragma',
        'Expires',
        'X-Content-Type-Options',
        'Content-Transfer-Encoding'
    ]

    print("\n📋 Headers إضافية:")
    for header in important_headers:
        value = response.get(header, 'غير موجود')
        print(f"  {header}: {value}")

    # التحقق من المحتوى
    if response.status_code == 200:
        content_length = len(response.content)
        print(f"✅ تم تحميل المحتوى بنجاح ({content_length} bytes)")

        # التحقق من أن المحتوى هو JSON صالح
        try:
            if response.get('Content-Type') == 'application/octet-stream':
                content_str = response.content.decode('utf-8')
                json.loads(content_str)
                print("✅ المحتوى هو JSON صالح")
            else:
                print("ℹ️ نوع المحتوى غير JSON")
        except:
            print("⚠️ المحتوى ليس JSON صالح")

    return response

def test_download_headers():
    """اختبار headers المطلوبة للتحميل"""
    print("\n🔍 اختبار headers المطلوبة للتحميل...")

    required_headers = {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': 'attachment',
        'Cache-Control': 'no-cache',
        'X-Content-Type-Options': 'nosniff'
    }

    print("📋 Headers المطلوبة للتحميل الصحيح:")
    for header, expected_value in required_headers.items():
        print(f"  ✅ {header}: {expected_value}")

def cleanup_test_data(backup, temp_file_path):
    """تنظيف بيانات الاختبار"""
    print("\n🧹 تنظيف بيانات الاختبار...")

    try:
        # حذف الملف المؤقت
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"✅ تم حذف الملف المؤقت: {temp_file_path}")

        # حذف سجل النسخة الاحتياطية
        backup.delete()
        print(f"✅ تم حذف سجل النسخة الاحتياطية: {backup.id}")

    except Exception as e:
        print(f"⚠️ خطأ في التنظيف: {str(e)}")

def generate_download_test_report():
    """إنشاء تقرير اختبار التحميل"""
    print("\n" + "="*60)
    print("📊 تقرير اختبار وظيفة التحميل")
    print("="*60)

    try:
        # إنشاء بيانات اختبار
        backup, temp_file_path = create_test_backup()

        # اختبار headers المطلوبة
        test_download_headers()

        # اختبار الاستجابة
        response = test_download_response(backup)

        # تحليل النتائج
        print(f"\n📋 ملخص النتائج:")

        if response.status_code == 200:
            print("✅ حالة الاستجابة: نجح (200)")
        else:
            print(f"❌ حالة الاستجابة: فشل ({response.status_code})")

        # فحص headers التحميل
        content_disposition = response.get('Content-Disposition', '')
        if 'attachment' in content_disposition:
            print("✅ Content-Disposition: يحتوي على attachment")
        else:
            print("❌ Content-Disposition: لا يحتوي على attachment")

        content_type = response.get('Content-Type', '')
        if content_type == 'application/octet-stream':
            print("✅ Content-Type: صحيح (application/octet-stream)")
        else:
            print(f"⚠️ Content-Type: {content_type} (قد يفتح في المتصفح)")

        # نصائح لحل المشاكل
        print(f"\n💡 نصائح لحل مشاكل التحميل:")
        print("1. تأكد من أن Content-Type هو application/octet-stream")
        print("2. تأكد من وجود attachment في Content-Disposition")
        print("3. جرب متصفحات مختلفة")
        print("4. تحقق من إعدادات التحميل في المتصفح")

        # تنظيف البيانات
        cleanup_test_data(backup, temp_file_path)

        return response.status_code == 200 and 'attachment' in content_disposition

    except Exception as e:
        print(f"❌ خطأ في الاختبار: {str(e)}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار وظيفة التحميل")
    print(f"📅 التاريخ والوقت: {os.popen('date').read().strip()}")

    success = generate_download_test_report()

    if success:
        print("\n🎉 اختبار التحميل نجح!")
        print("💡 إذا كان التحميل لا يزال لا يعمل، جرب:")
        print("   - مسح cache المتصفح")
        print("   - استخدام متصفح آخر")
        print("   - التحقق من إعدادات التحميل")
    else:
        print("\n❌ اختبار التحميل فشل")
        print("💡 تحقق من:")
        print("   - صلاحيات الملفات")
        print("   - إعدادات الخادم")
        print("   - logs النظام")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الاختبار بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ عام: {str(e)}")
        sys.exit(1)
