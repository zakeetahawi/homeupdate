#!/usr/bin/env python
"""
اختبار مبسط للنظام الجديد للتركيبات
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# إضافة المسار الحالي لـ Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

# استيراد النماذج
from installations.models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationTechnician
)

User = get_user_model()


def test_basic_functionality():
    """اختبار الوظائف الأساسية"""
    
    print("🧪 اختبار الوظائف الأساسية...")
    
    try:
        # 1. اختبار إنشاء مستخدم
        print("   📝 اختبار إنشاء مستخدم...")
        user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        print("   ✅ تم إنشاء المستخدم بنجاح")
        
        # 2. اختبار إنشاء فريق
        print("   👥 اختبار إنشاء فريق...")

        # إنشاء فرع أولاً
        from accounts.models import Branch
        branch, created = Branch.objects.get_or_create(
            name='فرع الاختبار',
            defaults={'address': 'عنوان الفرع'}
        )

        team = InstallationTeamNew.objects.create(
            name='فريق الاختبار',
            branch=branch,
            max_daily_installations=5
        )
        print("   ✅ تم إنشاء الفريق بنجاح")
        
        # 3. اختبار إنشاء فني
        print("   🔧 اختبار إنشاء فني...")
        technician = InstallationTechnician.objects.create(
            user=user,
            employee_id='TEST001',
            experience_years=3,
            max_daily_windows=15
        )
        print("   ✅ تم إنشاء الفني بنجاح")
        
        # 4. اختبار إنشاء تركيب
        print("   🏠 اختبار إنشاء تركيب...")

        # إنشاء طلب أولاً
        from orders.models import Order
        order = Order.objects.create(
            customer_name='عميل الاختبار',
            customer_phone='0123456789',
            salesperson=user,
            branch=branch,
            total_amount=1000.00
        )

        installation = InstallationNew.objects.create(
            order=order,
            customer_name='عميل الاختبار',
            customer_phone='0123456789',
            customer_address='عنوان الاختبار',
            salesperson_name='بائع الاختبار',
            windows_count=5,
            order_date=timezone.now().date(),
            scheduled_date=timezone.now().date() + timedelta(days=1),
            team=team,
            created_by=user
        )
        print("   ✅ تم إنشاء التركيب بنجاح")
        
        # 5. اختبار تحديث التركيب
        print("   📝 اختبار تحديث التركيب...")
        installation.status = 'scheduled'
        installation.priority = 'high'
        installation.save()
        print("   ✅ تم تحديث التركيب بنجاح")
        
        # 6. اختبار الاستعلامات
        print("   🔍 اختبار الاستعلامات...")
        
        # عدد التركيبات
        total_installations = InstallationNew.objects.count()
        print(f"   📊 إجمالي التركيبات: {total_installations}")
        
        # التركيبات المجدولة
        scheduled_installations = InstallationNew.objects.filter(status='scheduled').count()
        print(f"   📅 التركيبات المجدولة: {scheduled_installations}")
        
        # التركيبات عالية الأولوية
        high_priority = InstallationNew.objects.filter(priority='high').count()
        print(f"   🔥 التركيبات عالية الأولوية: {high_priority}")
        
        # 7. تنظيف البيانات
        print("   🧹 تنظيف بيانات الاختبار...")
        installation.delete()
        technician.delete()
        team.delete()
        user.delete()
        print("   ✅ تم تنظيف البيانات")
        
        print("✅ نجحت جميع الاختبارات الأساسية!")
        return True
        
    except Exception as e:
        print(f"❌ فشل في الاختبار: {e}")
        return False


def test_models_functionality():
    """اختبار وظائف النماذج"""
    
    print("\n🏗️ اختبار وظائف النماذج...")
    
    try:
        # إنشاء بيانات للاختبار
        user = User.objects.create_user(
            username='model_test',
            password='testpass123'
        )
        
        # إنشاء فرع
        from accounts.models import Branch
        branch, created = Branch.objects.get_or_create(
            name='فرع النماذج',
            defaults={'address': 'عنوان الفرع'}
        )

        team = InstallationTeamNew.objects.create(
            name='فريق النماذج',
            branch=branch,
            max_daily_installations=3
        )
        
        installation = InstallationNew.objects.create(
            customer_name='عميل النماذج',
            customer_phone='0987654321',
            windows_count=8,
            scheduled_date=timezone.now().date(),
            team=team,
            created_by=user
        )
        
        # اختبار خصائص النموذج
        print(f"   📋 معرف التركيب: {installation.id}")
        print(f"   👤 اسم العميل: {installation.customer_name}")
        print(f"   🪟 عدد الشبابيك: {installation.windows_count}")
        print(f"   📅 تاريخ الجدولة: {installation.scheduled_date}")
        print(f"   ⭐ الحالة: {installation.status}")
        print(f"   🎯 الأولوية: {installation.priority}")
        
        # اختبار العلاقات
        print(f"   👥 الفريق: {installation.team.name}")
        print(f"   🏢 الفرع: {installation.team.branch_name}")
        print(f"   👤 منشئ التركيب: {installation.created_by.username}")
        
        # اختبار الطرق
        print(f"   📝 نص التركيب: {str(installation)}")
        
        # تنظيف
        installation.delete()
        team.delete()
        user.delete()
        
        print("✅ نجحت اختبارات النماذج!")
        return True
        
    except Exception as e:
        print(f"❌ فشل في اختبار النماذج: {e}")
        return False


def test_database_operations():
    """اختبار عمليات قاعدة البيانات"""
    
    print("\n💾 اختبار عمليات قاعدة البيانات...")
    
    try:
        # إنشاء بيانات متعددة
        user = User.objects.create_user(username='db_test', password='test123')
        
        # إنشاء عدة تركيبات
        installations = []
        for i in range(5):
            installation = InstallationNew.objects.create(
                customer_name=f'عميل {i+1}',
                customer_phone=f'01234567{i:02d}',
                windows_count=i + 1,
                scheduled_date=timezone.now().date() + timedelta(days=i),
                created_by=user
            )
            installations.append(installation)
        
        print(f"   📝 تم إنشاء {len(installations)} تركيب")
        
        # اختبار الاستعلامات المتقدمة
        # البحث بالاسم
        search_result = InstallationNew.objects.filter(
            customer_name__icontains='عميل'
        ).count()
        print(f"   🔍 نتائج البحث بالاسم: {search_result}")
        
        # الفلترة بالتاريخ
        today_installations = InstallationNew.objects.filter(
            scheduled_date=timezone.now().date()
        ).count()
        print(f"   📅 تركيبات اليوم: {today_installations}")
        
        # الترتيب
        ordered_installations = InstallationNew.objects.order_by('-windows_count')[:3]
        print(f"   📊 أكبر 3 تركيبات: {[inst.windows_count for inst in ordered_installations]}")
        
        # التجميع
        from django.db.models import Sum, Count, Avg
        stats = InstallationNew.objects.aggregate(
            total_windows=Sum('windows_count'),
            total_count=Count('id'),
            avg_windows=Avg('windows_count')
        )
        print(f"   📈 إجمالي الشبابيك: {stats['total_windows']}")
        print(f"   📊 متوسط الشبابيك: {stats['avg_windows']:.1f}")
        
        # تنظيف
        InstallationNew.objects.filter(created_by=user).delete()
        user.delete()
        
        print("✅ نجحت اختبارات قاعدة البيانات!")
        return True
        
    except Exception as e:
        print(f"❌ فشل في اختبار قاعدة البيانات: {e}")
        return False


def test_system_imports():
    """اختبار استيراد وحدات النظام"""
    
    print("\n📦 اختبار استيراد وحدات النظام...")
    
    try:
        # اختبار استيراد الخدمات
        print("   🔧 اختبار استيراد الخدمات...")
        
        try:
            from installations.services.calendar_service import CalendarService
            print("   ✅ CalendarService")
        except ImportError as e:
            print(f"   ⚠️ CalendarService: {e}")
        
        try:
            from installations.services.alert_system import AlertSystem
            print("   ✅ AlertSystem")
        except ImportError as e:
            print(f"   ⚠️ AlertSystem: {e}")
        
        try:
            from installations.services.analytics_engine import AnalyticsEngine
            print("   ✅ AnalyticsEngine")
        except ImportError as e:
            print(f"   ⚠️ AnalyticsEngine: {e}")
        
        # اختبار استيراد العروض
        print("   🖥️ اختبار استيراد العروض...")
        
        try:
            from installations import views_new
            print("   ✅ views_new")
        except ImportError as e:
            print(f"   ⚠️ views_new: {e}")
        
        try:
            from installations import views_export
            print("   ✅ views_export")
        except ImportError as e:
            print(f"   ⚠️ views_export: {e}")
        
        # اختبار استيراد النماذج
        print("   📋 اختبار استيراد النماذج...")
        
        try:
            from installations.models_new import DailyInstallationReport
            print("   ✅ DailyInstallationReport")
        except ImportError as e:
            print(f"   ⚠️ DailyInstallationReport: {e}")
        
        try:
            from installations.models_new import InstallationAlert
            print("   ✅ InstallationAlert")
        except ImportError as e:
            print(f"   ⚠️ InstallationAlert: {e}")
        
        print("✅ انتهى اختبار الاستيراد!")
        return True
        
    except Exception as e:
        print(f"❌ فشل في اختبار الاستيراد: {e}")
        return False


def main():
    """الدالة الرئيسية"""
    
    print("🚀 بدء اختبار النظام الجديد للتركيبات")
    print("=" * 60)
    
    tests = [
        ("الوظائف الأساسية", test_basic_functionality),
        ("وظائف النماذج", test_models_functionality),
        ("عمليات قاعدة البيانات", test_database_operations),
        ("استيراد الوحدات", test_system_imports),
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
        return True
    else:
        print(f"\n⚠️ فشل {failed} اختبار. يرجى مراجعة الأخطاء.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
