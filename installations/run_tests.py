#!/usr/bin/env python
"""
سكريبت تشغيل اختبارات النظام الجديد للتركيبات
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line


def setup_test_environment():
    """إعداد بيئة الاختبار"""

    # إعداد متغير البيئة
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

    # تهيئة Django
    django.setup()


def run_all_tests():
    """تشغيل جميع اختبارات التركيبات"""
    
    print("🚀 بدء تشغيل اختبارات النظام الجديد للتركيبات...")
    print("=" * 60)
    
    # إعداد البيئة
    setup_test_environment()
    
    # الحصول على runner الاختبارات
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True)
    
    # تشغيل الاختبارات
    test_modules = [
        'installations.tests_new.InstallationModelTests',
        'installations.tests_new.CalendarServiceTests',
        'installations.tests_new.AlertSystemTests',
        'installations.tests_new.TechnicianAnalyticsTests',
        'installations.tests_new.OrderCompletionTests',
        'installations.tests_new.ViewsTests',
        'installations.tests_new.ManagementCommandTests',
        'installations.tests_new.IntegrationTests',
    ]
    
    failures = test_runner.run_tests(test_modules)
    
    if failures:
        print(f"\n❌ فشل في {failures} اختبار")
        return False
    else:
        print("\n✅ نجحت جميع الاختبارات!")
        return True


def run_specific_test(test_name):
    """تشغيل اختبار محدد"""
    
    print(f"🧪 تشغيل اختبار: {test_name}")
    print("=" * 60)
    
    setup_test_environment()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True)
    
    failures = test_runner.run_tests([f'installations.tests_new.{test_name}'])
    
    return failures == 0


def run_coverage_test():
    """تشغيل اختبارات مع تقرير التغطية"""
    
    try:
        import coverage
    except ImportError:
        print("❌ مكتبة coverage غير مثبتة. قم بتثبيتها أولاً:")
        print("pip install coverage")
        return False
    
    print("📊 تشغيل اختبارات مع تقرير التغطية...")
    print("=" * 60)
    
    # بدء قياس التغطية
    cov = coverage.Coverage()
    cov.start()
    
    # تشغيل الاختبارات
    success = run_all_tests()
    
    # إيقاف قياس التغطية
    cov.stop()
    cov.save()
    
    # إنشاء تقرير التغطية
    print("\n📈 تقرير التغطية:")
    print("-" * 40)
    cov.report(show_missing=True)
    
    # إنشاء تقرير HTML
    cov.html_report(directory='htmlcov')
    print(f"\n📄 تقرير HTML محفوظ في: htmlcov/index.html")
    
    return success


def run_performance_tests():
    """تشغيل اختبارات الأداء"""
    
    print("⚡ تشغيل اختبارات الأداء...")
    print("=" * 60)
    
    setup_test_environment()
    
    from django.test import TestCase
    from django.utils import timezone
    from datetime import timedelta
    import time
    
    from installations.models_new import InstallationNew
    from installations.services.calendar_service import CalendarService
    from installations.services.alert_system import AlertSystem
    from installations.services.analytics_engine import AnalyticsEngine
    
    # اختبار أداء إنشاء التركيبات
    print("🔧 اختبار أداء إنشاء التركيبات...")
    start_time = time.time()
    
    installations = []
    for i in range(100):
        installation = InstallationNew(
            customer_name=f'عميل {i}',
            customer_phone=f'01234567{i:02d}',
            windows_count=5,
            scheduled_date=timezone.now().date() + timedelta(days=i % 30),
        )
        installations.append(installation)
    
    InstallationNew.objects.bulk_create(installations)
    
    creation_time = time.time() - start_time
    print(f"   ⏱️  إنشاء 100 تركيب: {creation_time:.2f} ثانية")
    
    # اختبار أداء خدمة التقويم
    print("📅 اختبار أداء خدمة التقويم...")
    start_time = time.time()
    
    today = timezone.now().date()
    calendar_data = CalendarService.get_month_calendar(today.year, today.month)
    
    calendar_time = time.time() - start_time
    print(f"   ⏱️  تحميل تقويم الشهر: {calendar_time:.2f} ثانية")
    
    # اختبار أداء نظام الإنذارات
    print("🚨 اختبار أداء نظام الإنذارات...")
    start_time = time.time()
    
    alerts = AlertSystem.check_all_alerts(today)
    
    alerts_time = time.time() - start_time
    print(f"   ⏱️  فحص الإنذارات: {alerts_time:.2f} ثانية")
    
    # اختبار أداء محرك التحليلات
    print("📊 اختبار أداء محرك التحليلات...")
    start_time = time.time()
    
    analytics = AnalyticsEngine.get_dashboard_analytics()
    
    analytics_time = time.time() - start_time
    print(f"   ⏱️  تحليلات لوحة التحكم: {analytics_time:.2f} ثانية")
    
    # تنظيف البيانات
    InstallationNew.objects.filter(customer_name__startswith='عميل ').delete()
    
    print("\n✅ انتهت اختبارات الأداء")
    
    # تقييم النتائج
    total_time = creation_time + calendar_time + alerts_time + analytics_time
    print(f"\n📈 ملخص الأداء:")
    print(f"   إجمالي الوقت: {total_time:.2f} ثانية")
    
    if total_time < 5:
        print("   🟢 أداء ممتاز")
    elif total_time < 10:
        print("   🟡 أداء جيد")
    else:
        print("   🔴 أداء يحتاج تحسين")
    
    return total_time < 10


def run_load_tests():
    """تشغيل اختبارات الحمولة"""
    
    print("🏋️ تشغيل اختبارات الحمولة...")
    print("=" * 60)
    
    setup_test_environment()
    
    from django.test import Client
    from django.contrib.auth import get_user_model
    import threading
    import time
    
    User = get_user_model()
    
    # إنشاء مستخدم للاختبار
    user = User.objects.create_user(
        username='loadtest',
        password='testpass123'
    )
    
    def simulate_user_requests():
        """محاكاة طلبات المستخدم"""
        client = Client()
        client.login(username='loadtest', password='testpass123')
        
        # طلبات مختلفة
        urls = [
            '/installations/',
            '/installations/list/',
            '/installations/calendar/',
            '/installations/technician-analytics/',
        ]
        
        for url in urls:
            try:
                response = client.get(url)
                if response.status_code != 200:
                    print(f"❌ خطأ في {url}: {response.status_code}")
            except Exception as e:
                print(f"❌ استثناء في {url}: {e}")
    
    # تشغيل عدة خيوط متزامنة
    print("🔄 تشغيل 10 مستخدمين متزامنين...")
    
    start_time = time.time()
    threads = []
    
    for i in range(10):
        thread = threading.Thread(target=simulate_user_requests)
        threads.append(thread)
        thread.start()
    
    # انتظار انتهاء جميع الخيوط
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    print(f"⏱️  إجمالي وقت الاختبار: {total_time:.2f} ثانية")
    
    # تنظيف
    user.delete()
    
    if total_time < 30:
        print("✅ نجح اختبار الحمولة")
        return True
    else:
        print("❌ فشل اختبار الحمولة")
        return False


def main():
    """الدالة الرئيسية"""
    
    if len(sys.argv) < 2:
        print("استخدام:")
        print("python run_tests.py [all|coverage|performance|load|specific_test_name]")
        print("\nالخيارات:")
        print("  all         - تشغيل جميع الاختبارات")
        print("  coverage    - تشغيل الاختبارات مع تقرير التغطية")
        print("  performance - تشغيل اختبارات الأداء")
        print("  load        - تشغيل اختبارات الحمولة")
        print("  test_name   - تشغيل اختبار محدد")
        return
    
    command = sys.argv[1]
    
    if command == 'all':
        success = run_all_tests()
    elif command == 'coverage':
        success = run_coverage_test()
    elif command == 'performance':
        success = run_performance_tests()
    elif command == 'load':
        success = run_load_tests()
    else:
        # تشغيل اختبار محدد
        success = run_specific_test(command)
    
    if success:
        print("\n🎉 نجحت جميع الاختبارات!")
        sys.exit(0)
    else:
        print("\n💥 فشلت بعض الاختبارات!")
        sys.exit(1)


if __name__ == '__main__':
    main()
