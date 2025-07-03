#!/usr/bin/env python
"""
سكريبت إعداد وتشغيل النظام الجديد للتركيبات
"""
import os
import sys
import django
from django.core.management import execute_from_command_line, call_command
from django.conf import settings


def setup_django():
    """إعداد Django"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
    django.setup()


def check_requirements():
    """فحص المتطلبات"""
    print("🔍 فحص المتطلبات...")
    
    required_packages = [
        'django',
        'reportlab',
        'openpyxl',
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - غير مثبت")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  المكتبات المفقودة: {', '.join(missing_packages)}")
        print("قم بتثبيتها باستخدام:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ جميع المتطلبات متوفرة")
    return True


def create_migrations():
    """إنشاء ملفات الهجرة"""
    print("\n📦 إنشاء ملفات الهجرة...")
    
    try:
        call_command('makemigrations', 'installations', verbosity=1)
        print("✅ تم إنشاء ملفات الهجرة بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في إنشاء ملفات الهجرة: {e}")
        return False


def apply_migrations():
    """تطبيق الهجرات"""
    print("\n🔄 تطبيق الهجرات...")
    
    try:
        call_command('migrate', verbosity=1)
        print("✅ تم تطبيق الهجرات بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في تطبيق الهجرات: {e}")
        return False


def create_superuser():
    """إنشاء مستخدم إداري"""
    print("\n👤 إنشاء مستخدم إداري...")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # التحقق من وجود مستخدم إداري
    if User.objects.filter(is_superuser=True).exists():
        print("✅ يوجد مستخدم إداري مسبقاً")
        return True
    
    try:
        # إنشاء مستخدم إداري افتراضي
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        print("✅ تم إنشاء مستخدم إداري:")
        print("   اسم المستخدم: admin")
        print("   كلمة المرور: admin123")
        print("   ⚠️  يرجى تغيير كلمة المرور بعد تسجيل الدخول")
        return True
    except Exception as e:
        print(f"❌ خطأ في إنشاء المستخدم الإداري: {e}")
        return False


def create_sample_data():
    """إنشاء بيانات تجريبية"""
    print("\n📊 إنشاء بيانات تجريبية...")
    
    try:
        from django.contrib.auth import get_user_model
        from installations.models_new import (
            InstallationNew, 
            InstallationTeamNew, 
            InstallationTechnician
        )
        from django.utils import timezone
        from datetime import timedelta
        
        User = get_user_model()
        
        # إنشاء فنيين
        technician_users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'technician{i+1}',
                first_name=f'فني {i+1}',
                last_name='التركيب',
                email=f'technician{i+1}@example.com',
                password='tech123'
            )
            technician_users.append(user)
        
        # إنشاء فرق
        teams = []
        for i, user in enumerate(technician_users):
            team = InstallationTeamNew.objects.create(
                name=f'فريق {i+1}',
                branch_name=f'الفرع {i+1}',
                max_daily_installations=5
            )
            teams.append(team)
            
            # إنشاء فني
            technician = InstallationTechnician.objects.create(
                user=user,
                employee_id=f'EMP{i+1:03d}',
                experience_years=2 + i,
                max_daily_windows=15 + i * 5
            )
            
            # ربط الفني بالفريق
            team.technicians.add(technician)
        
        # إنشاء تركيبات تجريبية
        admin_user = User.objects.filter(is_superuser=True).first()
        today = timezone.now().date()
        
        statuses = ['pending', 'scheduled', 'in_progress', 'completed']
        priorities = ['normal', 'high', 'urgent']
        
        for i in range(20):
            installation = InstallationNew.objects.create(
                customer_name=f'عميل تجريبي {i+1}',
                customer_phone=f'0123456{i:03d}',
                customer_address=f'عنوان تجريبي {i+1}',
                salesperson_name=f'بائع {(i % 3) + 1}',
                branch_name=f'الفرع {(i % 3) + 1}',
                windows_count=(i % 10) + 1,
                order_date=today - timedelta(days=i % 30),
                scheduled_date=today + timedelta(days=i % 14),
                status=statuses[i % len(statuses)],
                priority=priorities[i % len(priorities)],
                team=teams[i % len(teams)],
                created_by=admin_user
            )
            
            # إضافة تواريخ فعلية للتركيبات المكتملة
            if installation.status == 'completed':
                installation.actual_start_date = timezone.now() - timedelta(hours=4)
                installation.actual_end_date = timezone.now() - timedelta(hours=1)
                installation.quality_rating = 4 + (i % 2)
                installation.customer_satisfaction = 4 + (i % 2)
                installation.save()
        
        print("✅ تم إنشاء البيانات التجريبية:")
        print(f"   - 3 فرق تركيب")
        print(f"   - 3 فنيين")
        print(f"   - 20 تركيب تجريبي")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء البيانات التجريبية: {e}")
        return False


def run_initial_checks():
    """تشغيل فحوصات أولية"""
    print("\n🔧 تشغيل فحوصات أولية...")
    
    try:
        # فحص الإنذارات
        call_command('check_alerts', verbosity=0)
        print("   ✅ نظام الإنذارات يعمل")
        
        # إنشاء تقرير يومي
        from datetime import date
        yesterday = date.today() - timedelta(days=1)
        call_command('generate_daily_report', '--date', yesterday.strftime('%Y-%m-%d'), verbosity=0)
        print("   ✅ نظام التقارير يعمل")
        
        return True
    except Exception as e:
        print(f"   ⚠️  تحذير في الفحوصات الأولية: {e}")
        return True  # لا نوقف الإعداد بسبب هذا


def display_system_info():
    """عرض معلومات النظام"""
    print("\n" + "="*60)
    print("🎉 تم إعداد النظام الجديد للتركيبات بنجاح!")
    print("="*60)
    
    print("\n📋 معلومات النظام:")
    print("   - النظام: نظام إدارة التركيبات المتقدم")
    print("   - الإصدار: 1.0.0")
    print("   - التاريخ: 2024")
    
    print("\n🔗 الروابط المهمة:")
    print("   - لوحة التحكم: /installations/")
    print("   - قائمة التركيبات: /installations/list/")
    print("   - التقويم الذكي: /installations/calendar/")
    print("   - تحليل الفنيين: /installations/technician-analytics/")
    print("   - واجهة المصنع: /installations/factory/")
    
    print("\n👥 حسابات المستخدمين:")
    print("   - المدير: admin / admin123")
    print("   - فني 1: technician1 / tech123")
    print("   - فني 2: technician2 / tech123")
    print("   - فني 3: technician3 / tech123")
    
    print("\n🛠️  أوامر مفيدة:")
    print("   - فحص الإنذارات: python manage.py check_alerts")
    print("   - إنشاء تقرير يومي: python manage.py generate_daily_report")
    print("   - تنظيف البيانات: python manage.py cleanup_old_data")
    print("   - تشغيل الاختبارات: python installations/run_tests.py all")
    
    print("\n📚 الميزات الرئيسية:")
    print("   ✅ إدارة التركيبات الشاملة")
    print("   ✅ الجدولة الذكية")
    print("   ✅ نظام الإنذارات المتقدم")
    print("   ✅ تحليل أداء الفنيين")
    print("   ✅ واجهة المصنع")
    print("   ✅ التصدير والطباعة")
    print("   ✅ التحليلات والتقارير")
    
    print("\n⚠️  ملاحظات مهمة:")
    print("   - يرجى تغيير كلمات المرور الافتراضية")
    print("   - راجع ملف README_NEW_SYSTEM.md للتفاصيل")
    print("   - تأكد من إعداد البريد الإلكتروني للإنذارات")
    
    print("\n🚀 النظام جاهز للاستخدام!")


def main():
    """الدالة الرئيسية"""
    print("🏗️  إعداد النظام الجديد للتركيبات")
    print("="*50)
    
    # إعداد Django
    setup_django()
    
    # فحص المتطلبات
    if not check_requirements():
        sys.exit(1)
    
    # إنشاء الهجرات
    if not create_migrations():
        sys.exit(1)
    
    # تطبيق الهجرات
    if not apply_migrations():
        sys.exit(1)
    
    # إنشاء مستخدم إداري
    if not create_superuser():
        sys.exit(1)
    
    # إنشاء بيانات تجريبية
    create_sample_data()
    
    # تشغيل فحوصات أولية
    run_initial_checks()
    
    # عرض معلومات النظام
    display_system_info()


if __name__ == '__main__':
    main()
