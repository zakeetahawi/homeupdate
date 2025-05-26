#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # إعداد متغيرات البيئة لقاعدة البيانات
    if 'DATABASE_URL' in os.environ:
        print("تم اكتشاف DATABASE_URL في manage.py")
        print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # تنفيذ الترحيلات تلقائيًا عند تشغيل السيرفر
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        # تعيين متغير بيئي لتجنب تنفيذ الترحيلات مرتين
        if not os.environ.get('AUTO_MIGRATE_EXECUTED'):
            try:
                # تأكد من أن Django تم تهيئته بالكامل
                import django
                django.setup()

                # تنفيذ أمر migrate مع استثناء ترحيل
                # accounts.fix_user_model_swap
                from django.core.management import call_command
                from django.db.migrations.recorder import MigrationRecorder
                from django.db import connection

                print("جاري تنفيذ الترحيلات تلقائيًا...")

                # الحصول على قائمة الترحيلات المطبقة
                recorder = MigrationRecorder(connection)
                applied_migrations = recorder.applied_migrations()

                # التحقق مما إذا كان ترحيل accounts.fix_user_model_swap موجودًا
                problematic_migration = ('accounts', 'fix_user_model_swap')

                # تنفيذ الترحيلات باستثناء الترحيل المشكل
                if problematic_migration not in applied_migrations:
                    # إضافة الترحيل المشكل إلى قائمة الترحيلات
                    # المطبقة لتجنب تنفيذه
                    recorder.record_applied(*problematic_migration)
                    app_name = problematic_migration[0]
                    migration_file = problematic_migration[1]
                    migration_name = f"{app_name}.{migration_file}"
                    print(f"تم تجاوز ترحيل {migration_name}")

                # تنفيذ باقي الترحيلات
                call_command('migrate')
                print("تم تنفيذ الترحيلات بنجاح.")

                # تعيين متغير بيئي لتجنب تنفيذ الترحيلات مرتين
                os.environ['AUTO_MIGRATE_EXECUTED'] = '1'
            except Exception as e:
                print(f"حدث خطأ أثناء تنفيذ الترحيلات التلقائية: {str(e)}")

    # تنفيذ الأمر
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
