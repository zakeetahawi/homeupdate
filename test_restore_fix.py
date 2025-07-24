#!/usr/bin/env python3
"""
اختبار إصلاح عملية الاستعادة
============================

هذا السكريبت يختبر:
1. تكوين التطبيقات الصحيح
2. عملية الاستعادة من ملفات JSON
3. التأكد من عدم وجود تعارضات في النماذج
"""

import os
import sys
import django
import json
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.contrib.contenttypes.models import ContentType

def test_app_configuration():
    """اختبار تكوين التطبيقات"""
    print("🔍 اختبار تكوين التطبيقات...")

    # قائمة التطبيقات المتوقعة
    expected_apps = [
        'accounts',
        'customers',
        'orders',
        'inspections',
        'manufacturing',  # التطبيق الرسمي للمصنع
        'installations',
        'odoo_db_manager',
        'inventory',
        'reports'
    ]

    installed_apps = [app.label for app in apps.get_app_configs()]

    print("📱 التطبيقات المثبتة:")
    for app in installed_apps:
        if app in expected_apps:
            print(f"  ✅ {app}")
        elif not app.startswith('django') and not app.startswith('rest_framework') and app not in ['corsheaders', 'django_apscheduler']:
            print(f"  ⚠️  {app} (غير متوقع)")

    # التحقق من عدم وجود تطبيق factory
    if 'factory' in installed_apps:
        print("  ❌ تطبيق factory موجود - يجب إزالته لتجنب التعارض مع manufacturing")
        return False
    else:
        print("  ✅ تطبيق factory غير موجود - ممتاز!")

    return True

def test_manufacturing_models():
    """اختبار نماذج التصنيع"""
    print("\n🏭 اختبار نماذج التصنيع...")

    try:
        # اختبار استيراد النماذج
        from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
        print("  ✅ تم استيراد نماذج التصنيع بنجاح")

        # اختبار عدد النماذج
        manufacturing_models = list(apps.get_app_config('manufacturing').get_models())
        print(f"  📊 عدد النماذج في تطبيق manufacturing: {len(manufacturing_models)}")

        for model in manufacturing_models:
            print(f"    - {model.__name__}")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في نماذج التصنيع: {str(e)}")
        return False

def test_content_types():
    """اختبار أنواع المحتوى"""
    print("\n📋 اختبار أنواع المحتوى...")

    try:
        # التحقق من أنواع المحتوى المهمة
        important_content_types = [
            ('manufacturing', 'manufacturingorder'),
            ('orders', 'order'),
            ('customers', 'customer'),
            ('inspections', 'inspection'),
            ('installations', 'installationschedule'),
        ]

        for app_label, model in important_content_types:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
                print(f"  ✅ {app_label}.{model}")
            except ContentType.DoesNotExist:
                print(f"  ⚠️  {app_label}.{model} غير موجود")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في اختبار أنواع المحتوى: {str(e)}")
        return False

def test_database_connection():
    """اختبار اتصال قاعدة البيانات"""
    print("\n🗄️ اختبار اتصال قاعدة البيانات...")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        print("  ✅ اتصال قاعدة البيانات يعمل بشكل صحيح")

        # عرض معلومات قاعدة البيانات
        db_settings = connection.settings_dict
        print(f"  📊 نوع قاعدة البيانات: {db_settings['ENGINE']}")
        print(f"  📊 اسم قاعدة البيانات: {db_settings['NAME']}")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في اتصال قاعدة البيانات: {str(e)}")
        return False

def test_restore_function():
    """اختبار وظيفة الاستعادة"""
    print("\n🔄 اختبار وظيفة الاستعادة...")

    try:
        from odoo_db_manager.views import _restore_json_simple
        print("  ✅ تم استيراد وظيفة الاستعادة بنجاح")

        # إنشاء ملف اختبار صغير
        test_data = [
            {
                "model": "customers.customer",
                "pk": 999999,
                "fields": {
                    "name": "عميل اختبار الاستعادة",
                    "phone": "0500000000",
                    "location_type": "riyadh",
                    "created_at": "2025-01-24T12:00:00Z",
                    "updated_at": "2025-01-24T12:00:00Z"
                }
            }
        ]

        test_file_path = "test_restore_data.json"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        print("  📄 تم إنشاء ملف اختبار")

        # محاولة الاستعادة
        try:
            result = _restore_json_simple(test_file_path, clear_existing=False)
            print(f"  ✅ نتيجة الاستعادة: {result}")

            # تنظيف البيانات الاختبارية
            from customers.models import Customer
            Customer.objects.filter(pk=999999).delete()
            print("  🧹 تم حذف بيانات الاختبار")

        finally:
            # حذف ملف الاختبار
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
                print("  🗑️ تم حذف ملف الاختبار")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في اختبار الاستعادة: {str(e)}")
        return False

def test_backup_restore_models():
    """اختبار نماذج النسخ الاحتياطي والاستعادة"""
    print("\n💾 اختبار نماذج النسخ الاحتياطي...")

    try:
        from odoo_db_manager.models import Backup, Database, RestoreProgress
        print("  ✅ تم استيراد نماذج النسخ الاحتياطي بنجاح")

        # اختبار إنشاء سجل progress
        from django.utils import timezone
        import uuid

        session_id = f"test_{int(timezone.now().timestamp())}"

        # التحقق من أن النموذج يعمل
        progress = RestoreProgress.objects.create(
            session_id=session_id,
            status='testing',
            progress_percentage=50,
            current_step='اختبار الوظائف'
        )

        print(f"  ✅ تم إنشاء سجل تقدم اختباري: {progress.session_id}")

        # حذف السجل الاختباري
        progress.delete()
        print("  🧹 تم حذف سجل الاختبار")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في نماذج النسخ الاحتياطي: {str(e)}")
        return False

def generate_report():
    """إنشاء تقرير شامل"""
    print("\n" + "="*50)
    print("📊 تقرير الاختبار الشامل")
    print("="*50)

    tests = [
        ("تكوين التطبيقات", test_app_configuration),
        ("نماذج التصنيع", test_manufacturing_models),
        ("أنواع المحتوى", test_content_types),
        ("اتصال قاعدة البيانات", test_database_connection),
        ("وظيفة الاستعادة", test_restore_function),
        ("نماذج النسخ الاحتياطي", test_backup_restore_models),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n🧪 تشغيل اختبار: {test_name}")
        print("-" * 30)
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ فشل الاختبار: {str(e)}")
            results[test_name] = False

    print("\n" + "="*50)
    print("📋 ملخص النتائج")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n📊 النتيجة النهائية: {passed}/{total} اختبار نجح")

    if passed == total:
        print("🎉 جميع الاختبارات نجحت! النظام جاهز للاستخدام.")
        return True
    else:
        print("⚠️ هناك مشاكل تحتاج إلى حل.")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار إصلاح عملية الاستعادة")
    print(f"📅 التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = generate_report()

    if success:
        print("\n✅ تم حل مشكلة عدم التعرف على تطبيق المصنع!")
        print("💡 نصائح:")
        print("   - تطبيق 'manufacturing' هو التطبيق الرسمي للمصنع")
        print("   - تم إزالة تطبيق 'factory' لتجنب التعارض")
        print("   - عملية الاستعادة تعمل بشكل صحيح الآن")
    else:
        print("\n❌ هناك مشاكل تحتاج إلى حل إضافي")

    return success

if __name__ == '__main__':
    main()
