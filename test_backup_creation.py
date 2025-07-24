#!/usr/bin/env python3
"""
اختبار إنشاء النسخة الاحتياطية بعد إزالة تطبيق factory
==============================================================

هذا السكريبت يختبر:
1. إنشاء نسخة احتياطية كاملة
2. التأكد من عدم وجود أخطاء في التطبيقات
3. اختبار أن تطبيق manufacturing يعمل بشكل صحيح
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
from io import StringIO
import tempfile

def test_apps_availability():
    """اختبار توفر التطبيقات المطلوبة"""
    print("🔍 اختبار توفر التطبيقات...")

    required_apps = [
        'customers',
        'orders',
        'inspections',
        'inventory',
        'installations',
        'manufacturing',  # التطبيق الصحيح للمصنع
        'accounts',
        'odoo_db_manager'
    ]

    all_available = True

    for app_name in required_apps:
        try:
            app_config = apps.get_app_config(app_name)
            print(f"  ✅ {app_name}: {app_config.verbose_name}")
        except LookupError:
            print(f"  ❌ {app_name}: غير موجود")
            all_available = False

    # التحقق من عدم وجود factory
    try:
        apps.get_app_config('factory')
        print(f"  ⚠️ factory: لا يجب أن يكون موجوداً!")
        all_available = False
    except LookupError:
        print(f"  ✅ factory: غير موجود (صحيح)")

    return all_available

def test_manufacturing_models():
    """اختبار نماذج التصنيع"""
    print("\n🏭 اختبار نماذج التصنيع...")

    try:
        from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem

        # عد النماذج
        manufacturing_count = ManufacturingOrder.objects.count()
        print(f"  📊 عدد أوامر التصنيع: {manufacturing_count}")

        # اختبار إنشاء ContentType
        ct = ContentType.objects.get_for_model(ManufacturingOrder)
        print(f"  ✅ ContentType: {ct.app_label}.{ct.model}")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في نماذج التصنيع: {str(e)}")
        return False

def test_dumpdata_command():
    """اختبار أمر dumpdata للتطبيقات المطلوبة"""
    print("\n📦 اختبار أمر dumpdata...")

    apps_to_test = [
        'customers',
        'orders',
        'inspections',
        'inventory',
        'installations',
        'manufacturing',  # استخدام manufacturing بدلاً من factory
        'accounts',
        'odoo_db_manager'
    ]

    try:
        # اختبار كل تطبيق على حدة
        for app in apps_to_test:
            try:
                output = StringIO()
                call_command('dumpdata', app, stdout=output, format='json', verbosity=0)
                data = output.getvalue()

                # التحقق من أن البيانات صالحة JSON
                json.loads(data)
                print(f"  ✅ {app}: {len(data)} حرف")

            except Exception as app_error:
                print(f"  ❌ {app}: {str(app_error)}")
                return False

        # اختبار جميع التطبيقات معاً
        print(f"\n  🔄 اختبار جميع التطبيقات معاً...")
        output = StringIO()
        call_command('dumpdata', *apps_to_test, stdout=output, format='json', indent=2, verbosity=0)
        full_data = output.getvalue()

        # التحقق من صحة JSON
        parsed_data = json.loads(full_data)
        print(f"  ✅ النسخة الكاملة: {len(parsed_data)} عنصر، {len(full_data)} حرف")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في اختبار dumpdata: {str(e)}")
        return False

def test_backup_creation_simulation():
    """محاكاة إنشاء نسخة احتياطية"""
    print("\n💾 محاكاة إنشاء نسخة احتياطية...")

    try:
        # إنشاء ملف مؤقت
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name

        try:
            # تطبيقات النسخة الكاملة
            apps_to_backup = [
                'customers',
                'orders',
                'inspections',
                'inventory',
                'installations',
                'manufacturing',  # استخدام manufacturing
                'accounts',
                'odoo_db_manager'
            ]

            print(f"  📋 التطبيقات المحددة: {', '.join(apps_to_backup)}")

            # تنفيذ dumpdata
            with open(temp_path, 'w', encoding='utf-8') as output_file:
                call_command('dumpdata', *apps_to_backup, stdout=output_file,
                           format='json', indent=2, verbosity=0)

            # قراءة والتحقق من النتيجة
            with open(temp_path, 'r', encoding='utf-8') as input_file:
                backup_data = input_file.read()

            # التحقق من صحة JSON
            parsed_data = json.loads(backup_data)

            # إحصائيات
            models_count = {}
            for item in parsed_data:
                model = item.get('model', 'unknown')
                models_count[model] = models_count.get(model, 0) + 1

            print(f"  ✅ تم إنشاء النسخة الاحتياطية بنجاح!")
            print(f"  📊 إجمالي العناصر: {len(parsed_data)}")
            print(f"  📊 عدد النماذج: {len(models_count)}")

            # عرض أهم النماذج
            print(f"  📋 أهم النماذج:")
            for model, count in sorted(models_count.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"    - {model}: {count} عنصر")

            # التحقق من وجود بيانات manufacturing
            manufacturing_models = [model for model in models_count.keys() if model.startswith('manufacturing')]
            if manufacturing_models:
                print(f"  ✅ تم العثور على نماذج التصنيع: {manufacturing_models}")
            else:
                print(f"  ⚠️ لم يتم العثور على نماذج التصنيع (قد يكون فارغاً)")

            return True

        finally:
            # حذف الملف المؤقت
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                print(f"  🗑️ تم حذف الملف المؤقت")

    except Exception as e:
        print(f"  ❌ خطأ في محاكاة النسخة الاحتياطية: {str(e)}")
        return False

def test_manufacturing_content_type():
    """اختبار ContentType للتصنيع"""
    print("\n🏷️ اختبار ContentType للتصنيع...")

    try:
        # التحقق من وجود ContentType للتصنيع
        manufacturing_ct = ContentType.objects.filter(app_label='manufacturing')

        if manufacturing_ct.exists():
            print(f"  ✅ تم العثور على {manufacturing_ct.count()} ContentType للتصنيع:")
            for ct in manufacturing_ct:
                print(f"    - {ct.app_label}.{ct.model}")
        else:
            print(f"  ⚠️ لم يتم العثور على ContentType للتصنيع")

        # التحقق من عدم وجود ContentType لـ factory
        factory_ct = ContentType.objects.filter(app_label='factory')

        if factory_ct.exists():
            print(f"  ❌ تم العثور على ContentType قديم لـ factory:")
            for ct in factory_ct:
                print(f"    - {ct.app_label}.{ct.model} (يجب إزالته)")
            return False
        else:
            print(f"  ✅ لا يوجد ContentType قديم لـ factory")

        return True

    except Exception as e:
        print(f"  ❌ خطأ في اختبار ContentType: {str(e)}")
        return False

def generate_report():
    """إنشاء تقرير شامل للاختبار"""
    print("\n" + "="*60)
    print("📊 تقرير اختبار إنشاء النسخة الاحتياطية")
    print("="*60)

    tests = [
        ("توفر التطبيقات", test_apps_availability),
        ("نماذج التصنيع", test_manufacturing_models),
        ("أمر dumpdata", test_dumpdata_command),
        ("محاكاة النسخة الاحتياطية", test_backup_creation_simulation),
        ("ContentType للتصنيع", test_manufacturing_content_type),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n🧪 تشغيل اختبار: {test_name}")
        print("-" * 40)
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ فشل الاختبار بشكل غير متوقع: {str(e)}")
            results[test_name] = False

    print("\n" + "="*60)
    print("📋 ملخص النتائج")
    print("="*60)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n📊 النتيجة النهائية: {passed}/{total} اختبار نجح")

    if passed == total:
        print("\n🎉 جميع الاختبارات نجحت!")
        print("✅ يمكن الآن إنشاء النسخ الاحتياطية بدون أخطاء")
        print("💡 تطبيق 'manufacturing' يعمل بشكل صحيح")
        return True
    else:
        print("\n⚠️ هناك مشاكل تحتاج إلى حل إضافي")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار إنشاء النسخة الاحتياطية")
    print(f"📅 التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = generate_report()

    if success:
        print("\n✅ تم حل مشكلة إنشاء النسخة الاحتياطية!")
        print("\n💡 نصائح للاستخدام:")
        print("   - استخدم تطبيق 'manufacturing' بدلاً من 'factory'")
        print("   - النسخ الاحتياطية الكاملة تعمل بشكل صحيح")
        print("   - جميع التطبيقات متوفرة ومتوافقة")
    else:
        print("\n❌ هناك مشاكل تحتاج إلى حل إضافي")
        print("💡 يرجى مراجعة الأخطاء أعلاه وإصلاحها")

    return success

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الاختبار بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ عام في الاختبار: {str(e)}")
        sys.exit(1)
