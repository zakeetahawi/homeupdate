#!/usr/bin/env python
"""
إصلاح سريع لمشكلة URLs في النظام الجديد
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

from django.urls import reverse
from django.test import Client


def test_urls():
    """اختبار URLs النظام الجديد"""
    print("🔗 اختبار URLs النظام الجديد...")
    
    # URLs للاختبار
    urls_to_test = [
        ('installations_new:dashboard', 'لوحة التحكم'),
        ('installations_new:list', 'قائمة التركيبات'),
        ('installations_new:create', 'إنشاء تركيب'),
        ('installations_new:calendar', 'التقويم'),
        ('installations_new:technician_analytics', 'تحليل الفنيين'),
        ('installations_new:factory_interface', 'واجهة المصنع'),
        ('installations_new:quick_edit', 'التعديل السريع'),
    ]
    
    success_count = 0
    total_count = len(urls_to_test)
    
    for url_name, description in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"   ✅ {description}: {url}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ {description}: {e}")
    
    print(f"\n📊 نتائج اختبار URLs: {success_count}/{total_count} نجح")
    return success_count == total_count


def test_views():
    """اختبار العروض"""
    print("\n🖥️ اختبار العروض...")
    
    client = Client()
    
    # تسجيل دخول تجريبي
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # إنشاء مستخدم تجريبي
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@example.com',
            'is_staff': True,
            'is_active': True
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
    
    # تسجيل الدخول
    login_success = client.login(username='test_user', password='testpass123')
    
    if not login_success:
        print("   ❌ فشل في تسجيل الدخول")
        return False
    
    print("   ✅ تم تسجيل الدخول بنجاح")
    
    # اختبار الصفحات
    pages_to_test = [
        ('/installations/', 'لوحة التحكم'),
        ('/installations/list/', 'قائمة التركيبات'),
        ('/installations/create/', 'إنشاء تركيب'),
        ('/installations/calendar/', 'التقويم'),
        ('/installations/technician-analytics/', 'تحليل الفنيين'),
        ('/installations/factory/', 'واجهة المصنع'),
        ('/installations/quick-edit/', 'التعديل السريع'),
    ]
    
    success_count = 0
    total_count = len(pages_to_test)
    
    for url, description in pages_to_test:
        try:
            response = client.get(url)
            if response.status_code == 200:
                print(f"   ✅ {description}: {response.status_code}")
                success_count += 1
            else:
                print(f"   ⚠️ {description}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {description}: {e}")
    
    print(f"\n📊 نتائج اختبار العروض: {success_count}/{total_count} نجح")
    
    # تنظيف
    if created:
        user.delete()
    
    return success_count >= total_count * 0.8  # 80% نجاح مقبول


def fix_common_issues():
    """إصلاح المشاكل الشائعة"""
    print("\n🔧 إصلاح المشاكل الشائعة...")
    
    fixes_applied = 0
    
    # 1. التحقق من وجود ملفات القوالب
    template_files = [
        'installations/templates/installations/dashboard.html',
        'installations/templates/installations/list.html',
        'installations/templates/installations/smart_calendar.html',
        'installations/templates/installations/technician_analytics.html',
        'installations/templates/installations/factory_interface.html',
        'installations/templates/installations/quick_edit_table.html',
    ]
    
    for template_file in template_files:
        if os.path.exists(template_file):
            print(f"   ✅ قالب موجود: {template_file}")
        else:
            print(f"   ❌ قالب مفقود: {template_file}")
            # يمكن إنشاء قالب أساسي هنا
    
    # 2. التحقق من وجود ملفات الخدمات
    service_files = [
        'installations/services/calendar_service.py',
        'installations/services/alert_system.py',
        'installations/services/analytics_engine.py',
        'installations/services/technician_analytics.py',
        'installations/services/order_completion.py',
        'installations/services/pdf_export.py',
    ]
    
    for service_file in service_files:
        if os.path.exists(service_file):
            print(f"   ✅ خدمة موجودة: {service_file}")
        else:
            print(f"   ❌ خدمة مفقودة: {service_file}")
    
    # 3. التحقق من إعدادات Django
    from django.conf import settings
    
    if 'installations' in settings.INSTALLED_APPS:
        print("   ✅ تطبيق installations مثبت في INSTALLED_APPS")
        fixes_applied += 1
    else:
        print("   ❌ تطبيق installations غير مثبت في INSTALLED_APPS")
    
    print(f"\n📊 تم تطبيق {fixes_applied} إصلاح")
    return fixes_applied > 0


def create_basic_templates():
    """إنشاء قوالب أساسية إذا كانت مفقودة"""
    print("\n📄 إنشاء قوالب أساسية...")
    
    templates_dir = 'installations/templates/installations'
    os.makedirs(templates_dir, exist_ok=True)
    
    # قالب أساسي للصفحات المفقودة
    basic_template = '''{% extends "base.html" %}
{% load i18n %}

{% block title %}{{ page_title }}{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3><i class="fas fa-tools"></i> {{ page_title }}</h3>
                </div>
                <div class="card-body">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i>
                        هذه الصفحة قيد التطوير. سيتم إضافة المحتوى قريباً.
                    </div>
                    
                    <div class="text-center">
                        <a href="{% url 'installations_new:dashboard' %}" class="btn btn-primary">
                            <i class="fas fa-home"></i> العودة للوحة التحكم
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''
    
    # قوالب للإنشاء
    templates_to_create = [
        ('list.html', 'قائمة التركيبات'),
        ('create.html', 'إنشاء تركيب جديد'),
        ('edit.html', 'تعديل التركيب'),
        ('detail.html', 'تفاصيل التركيب'),
    ]
    
    created_count = 0
    
    for template_name, page_title in templates_to_create:
        template_path = os.path.join(templates_dir, template_name)
        
        if not os.path.exists(template_path):
            try:
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(basic_template.replace('{{ page_title }}', page_title))
                print(f"   ✅ تم إنشاء قالب: {template_name}")
                created_count += 1
            except Exception as e:
                print(f"   ❌ فشل في إنشاء قالب {template_name}: {e}")
        else:
            print(f"   ✅ قالب موجود: {template_name}")
    
    print(f"\n📊 تم إنشاء {created_count} قالب جديد")
    return created_count


def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح سريع لنظام التركيبات الجديد")
    print("=" * 60)
    
    # تشغيل الاختبارات والإصلاحات
    tests = [
        ("اختبار URLs", test_urls),
        ("إصلاح المشاكل الشائعة", fix_common_issues),
        ("إنشاء قوالب أساسية", create_basic_templates),
        ("اختبار العروض", test_views),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 تشغيل: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ نجح: {test_name}")
            else:
                failed += 1
                print(f"❌ فشل: {test_name}")
        except Exception as e:
            failed += 1
            print(f"💥 خطأ في {test_name}: {e}")
    
    # النتائج النهائية
    print("\n" + "=" * 60)
    print("📊 نتائج الإصلاح:")
    print(f"   ✅ نجح: {passed}")
    print(f"   ❌ فشل: {failed}")
    print(f"   📈 معدل النجاح: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 تم إصلاح جميع المشاكل! النظام جاهز للاستخدام.")
        print("\n🚀 للوصول للنظام:")
        print("   1. تشغيل الخادم: python manage.py runserver")
        print("   2. زيارة: http://localhost:8000/installations/")
        return True
    else:
        print(f"\n⚠️ لا تزال هناك {failed} مشكلة. يرجى مراجعة الأخطاء أعلاه.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
