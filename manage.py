#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # إعداد متغيرات البيئة لقاعدة البيانات
    if 'DATABASE_URL' in os.environ:
        print(f"استخدام DATABASE_URL: {os.environ.get('DATABASE_URL')}")
        print("تم تكوين قاعدة البيانات من DATABASE_URL")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # تنفيذ الترحيلات تلقائ<|im_start|> عند تشغيل الخادم (محسن ومبسط)
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver' and not os.environ.get('AUTO_MIGRATE_EXECUTED'):
        try:
            import django
            django.setup()

            from django.core.management import call_command
            print("جاري تنفيذ الترحيلات تلقائ<|im_start|>...")

            call_command('migrate', verbosity=0)  # تقليل الإخراج
            print("تم تنفيذ الترحيلات بنجاح.")

            os.environ['AUTO_MIGRATE_EXECUTED'] = '1'
        except Exception as e:
            print(f"حدث خطأ أثناء تنفيذ الترحيلات التلقائية: {str(e)}")

    # تنفيذ الأمر
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
