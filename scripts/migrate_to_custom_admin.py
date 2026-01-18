"""
سكريبت لنقل جميع التسجيلات من admin.site إلى custom_admin_site
يقوم بنسخ جميع النماذج المسجلة تلقائياً
"""
import os
import sys

import django

# إعداد Django
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib import admin

from crm.custom_admin import custom_admin_site


def migrate_admin_registrations():
    """نقل جميع التسجيلات من admin.site إلى custom_admin_site"""
    migrated = 0
    skipped = 0
    errors = []
    
    print("="*70)
    print("🔄 بدء نقل التسجيلات من admin.site إلى custom_admin_site...")
    print("="*70)
    print(f"\n📊 عدد النماذج المسجلة في admin.site: {len(admin.site._registry)}\n")
    
    for model, model_admin in admin.site._registry.items():
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        full_name = f"{app_label}.{model_name}"
        
        try:
            # التحقق من عدم التسجيل المسبق
            if model not in custom_admin_site._registry:
                # تسجيل النموذج مع نفس الـ ModelAdmin class
                custom_admin_site.register(model, model_admin.__class__)
                migrated += 1
                print(f"✅ تم تسجيل: {full_name:50} | {model_admin.__class__.__name__}")
            else:
                skipped += 1
                print(f"⏭️  مسجل مسبقاً: {full_name:50}")
        except admin.sites.AlreadyRegistered:
            skipped += 1
            print(f"⏭️  مسجل مسبقاً: {full_name:50}")
        except Exception as e:
            error_msg = f"❌ خطأ في {full_name}: {str(e)}"
            errors.append(error_msg)
            print(error_msg)
    
    # ملخص النتائج
    print("\n" + "="*70)
    print("📊 ملخص النتائج:")
    print("="*70)
    print(f"✅ تم تسجيل {migrated} نموذج بنجاح")
    print(f"⏭️  تم تخطي {skipped} نموذج (مسجل مسبقاً)")
    print(f"📊 إجمالي النماذج في custom_admin_site: {len(custom_admin_site._registry)}")
    
    if errors:
        print(f"\n⚠️  حدثت {len(errors)} أخطاء:")
        print("-"*70)
        for error in errors:
            print(f"  {error}")
    else:
        print("\n🎉 تمت العملية بنجاح بدون أخطاء!")
    
    print("="*70)
    
    return migrated, skipped, errors


def verify_migration():
    """التحقق من نجاح عملية النقل"""
    print("\n" + "="*70)
    print("🔍 التحقق من التسجيلات...")
    print("="*70)
    
    # تجميع النماذج حسب التطبيق
    apps_dict = {}
    for model in custom_admin_site._registry:
        app_label = model._meta.app_label
        if app_label not in apps_dict:
            apps_dict[app_label] = []
        apps_dict[app_label].append(model._meta.model_name)
    
    # عرض النماذج المسجلة لكل تطبيق
    for app_label in sorted(apps_dict.keys()):
        models = sorted(apps_dict[app_label])
        print(f"\n📦 {app_label} ({len(models)} نموذج):")
        for model_name in models:
            print(f"   - {model_name}")
    
    print("\n" + "="*70)
    print(f"✅ إجمالي التطبيقات: {len(apps_dict)}")
    print(f"✅ إجمالي النماذج: {len(custom_admin_site._registry)}")
    print("="*70)


if __name__ == '__main__':
    print("\n🚀 بدء عملية النقل التلقائي...\n")
    
    # تنفيذ عملية النقل
    migrated, skipped, errors = migrate_admin_registrations()
    
    # التحقق من النتائج
    if errors:
        print("\n⚠️  تحذير: حدثت بعض الأخطاء أثناء النقل")
        print("يرجى مراجعة الأخطاء أعلاه وإصلاحها يدوياً")
    else:
        # عرض التحقق التفصيلي
        verify_migration()
        
        print("\n" + "="*70)
        print("✅ العملية مكتملة!")
        print("="*70)
        print("\nالخطوات التالية:")
        print("1. أعد تشغيل السيرفر: python manage.py runserver")
        print("2. افتح المتصفح: http://localhost:8000/admin/")
        print("3. تحقق من ظهور المجموعات والإحصائيات")
        print("="*70 + "\n")
