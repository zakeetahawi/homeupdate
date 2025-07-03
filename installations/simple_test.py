#!/usr/bin/env python
"""
اختبار مبسط جداً للنظام الجديد للتركيبات
"""
import os
import sys

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# إضافة المسار الحالي
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import django
django.setup()


def test_imports():
    """اختبار استيراد الوحدات"""
    print("🧪 اختبار استيراد الوحدات...")
    
    success_count = 0
    total_count = 0
    
    # اختبار استيراد النماذج الأساسية
    modules_to_test = [
        ('installations.models_new', 'InstallationNew'),
        ('installations.models_new', 'InstallationTeamNew'),
        ('installations.models_new', 'InstallationTechnician'),
        ('installations.models_new', 'InstallationAlert'),
        ('django.contrib.auth', 'get_user_model'),
        ('django.utils', 'timezone'),
    ]
    
    for module_name, class_name in modules_to_test:
        total_count += 1
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"   ✅ {module_name}.{class_name}")
            success_count += 1
        except ImportError as e:
            print(f"   ❌ {module_name}.{class_name}: {e}")
        except AttributeError as e:
            print(f"   ❌ {module_name}.{class_name}: {e}")
    
    print(f"\n📊 نتائج الاستيراد: {success_count}/{total_count} نجح")
    return success_count == total_count


def test_database_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    print("\n💾 اختبار الاتصال بقاعدة البيانات...")
    
    try:
        from django.db import connection
        
        # اختبار الاتصال
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        if result and result[0] == 1:
            print("   ✅ الاتصال بقاعدة البيانات يعمل")
            return True
        else:
            print("   ❌ فشل في الاتصال بقاعدة البيانات")
            return False
            
    except Exception as e:
        print(f"   ❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        return False


def test_django_setup():
    """اختبار إعداد Django"""
    print("\n⚙️ اختبار إعداد Django...")
    
    try:
        from django.conf import settings
        from django.apps import apps
        
        # فحص الإعدادات
        if hasattr(settings, 'DATABASES'):
            print("   ✅ إعدادات قاعدة البيانات موجودة")
        else:
            print("   ❌ إعدادات قاعدة البيانات مفقودة")
            return False
        
        # فحص التطبيقات
        if 'installations' in settings.INSTALLED_APPS:
            print("   ✅ تطبيق installations مثبت")
        else:
            print("   ❌ تطبيق installations غير مثبت")
            return False
        
        # فحص تحميل التطبيقات
        try:
            installations_app = apps.get_app_config('installations')
            print(f"   ✅ تطبيق installations محمل: {installations_app.name}")
        except Exception as e:
            print(f"   ❌ خطأ في تحميل تطبيق installations: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ خطأ في إعداد Django: {e}")
        return False


def test_models_basic():
    """اختبار أساسي للنماذج"""
    print("\n🏗️ اختبار أساسي للنماذج...")
    
    try:
        # محاولة استيراد النماذج
        from installations.models_new import InstallationNew
        print("   ✅ تم استيراد InstallationNew")
        
        # فحص الحقول الأساسية
        fields = [field.name for field in InstallationNew._meta.fields]
        required_fields = ['customer_name', 'customer_phone', 'windows_count']
        
        missing_fields = []
        for field in required_fields:
            if field in fields:
                print(f"   ✅ حقل {field} موجود")
            else:
                print(f"   ❌ حقل {field} مفقود")
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   ⚠️ حقول مفقودة: {missing_fields}")
            return False
        
        print("   ✅ جميع الحقول الأساسية موجودة")
        return True
        
    except Exception as e:
        print(f"   ❌ خطأ في اختبار النماذج: {e}")
        return False


def test_urls():
    """اختبار URLs"""
    print("\n🔗 اختبار URLs...")
    
    try:
        # محاولة استيراد URLs
        from installations import urls_new
        print("   ✅ تم استيراد urls_new")
        
        # فحص وجود urlpatterns
        if hasattr(urls_new, 'urlpatterns'):
            print(f"   ✅ urlpatterns موجود ({len(urls_new.urlpatterns)} مسار)")
        else:
            print("   ❌ urlpatterns مفقود")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ خطأ في اختبار URLs: {e}")
        return False


def test_services():
    """اختبار الخدمات"""
    print("\n🔧 اختبار الخدمات...")
    
    services_to_test = [
        'installations.services.calendar_service',
        'installations.services.alert_system',
        'installations.services.analytics_engine',
    ]
    
    success_count = 0
    
    for service in services_to_test:
        try:
            __import__(service)
            print(f"   ✅ {service}")
            success_count += 1
        except ImportError as e:
            print(f"   ❌ {service}: {e}")
    
    print(f"\n📊 نتائج الخدمات: {success_count}/{len(services_to_test)} نجح")
    return success_count == len(services_to_test)


def test_management_commands():
    """اختبار أوامر الإدارة"""
    print("\n⚙️ اختبار أوامر الإدارة...")
    
    import os
    commands_dir = os.path.join(
        os.path.dirname(__file__), 
        'management', 
        'commands'
    )
    
    if not os.path.exists(commands_dir):
        print("   ❌ مجلد أوامر الإدارة غير موجود")
        return False
    
    expected_commands = [
        'check_alerts.py',
        'generate_daily_report.py',
        'cleanup_old_data.py'
    ]
    
    success_count = 0
    
    for command in expected_commands:
        command_path = os.path.join(commands_dir, command)
        if os.path.exists(command_path):
            print(f"   ✅ {command}")
            success_count += 1
        else:
            print(f"   ❌ {command} مفقود")
    
    print(f"\n📊 نتائج الأوامر: {success_count}/{len(expected_commands)} موجود")
    return success_count == len(expected_commands)


def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار مبسط للنظام الجديد للتركيبات")
    print("=" * 60)
    
    tests = [
        ("استيراد الوحدات", test_imports),
        ("الاتصال بقاعدة البيانات", test_database_connection),
        ("إعداد Django", test_django_setup),
        ("النماذج الأساسية", test_models_basic),
        ("URLs", test_urls),
        ("الخدمات", test_services),
        ("أوامر الإدارة", test_management_commands),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 تشغيل اختبار: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ نجح اختبار: {test_name}")
            else:
                failed += 1
                print(f"❌ فشل اختبار: {test_name}")
        except Exception as e:
            failed += 1
            print(f"💥 خطأ في اختبار {test_name}: {e}")
    
    # النتائج النهائية
    print("\n" + "=" * 60)
    print("📊 نتائج الاختبارات:")
    print(f"   ✅ نجح: {passed}")
    print(f"   ❌ فشل: {failed}")
    print(f"   📈 معدل النجاح: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 نجحت جميع الاختبارات! النظام جاهز للاستخدام.")
        print("\n🚀 الخطوات التالية:")
        print("   1. تشغيل الهجرات: python manage.py makemigrations && python manage.py migrate")
        print("   2. إنشاء مستخدم إداري: python manage.py createsuperuser")
        print("   3. تشغيل الخادم: python manage.py runserver")
        print("   4. زيارة: http://localhost:8000/installations/")
        return True
    else:
        print(f"\n⚠️ فشل {failed} اختبار. يرجى مراجعة الأخطاء أعلاه.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
