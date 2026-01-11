"""
Data Migration: تحميل القوالب والإعدادات الأساسية
يتم تطبيقه تلقائياً عند migrate
بيانات الاعتماد (access_token, etc.) تُضاف يدوياً من لوحة التحكم
"""

from django.db import migrations


def create_initial_data(apps, schema_editor):
    """إنشاء القوالب والإعدادات الأساسية"""

    WhatsAppMessageTemplate = apps.get_model("whatsapp", "WhatsAppMessageTemplate")
    WhatsAppSettings = apps.get_model("whatsapp", "WhatsAppSettings")

    # إنشاء القوالب
    templates_data = [
        {
            "name": "ترحيب بالعميل",
            "message_type": "WELCOME",
            "meta_template_name": "customer_welcome",
            "language": "ar",
            "test_variables": {"customer_name": "عميل تجريبي"},
            "is_active": True,
        },
        {
            "name": "تأكيد الطلب",
            "message_type": "ORDER_CREATED",
            "meta_template_name": "confirm_order",
            "language": "ar",
            "test_variables": {
                "customer_name": "عميل تجريبي",
                "order_number": "TEST-001",
                "order_date": "2026-01-03",
            },
            "is_active": True,
        },
        {
            "name": "موعد المعاينة",
            "message_type": "INSPECTION_SCHEDULED",
            "meta_template_name": "inspection_date",
            "language": "ar",
            "test_variables": {
                "customer_name": "عميل تجريبي",
                "order_number": "TEST-001",
                "inspection_date": "2026-01-15",
            },
            "is_active": True,
        },
        {
            "name": "موعد التركيب",
            "message_type": "INSTALLATION_SCHEDULED",
            "meta_template_name": "installation_date",
            "language": "ar",
            "test_variables": {
                "customer_name": "عميل تجريبي",
                "order_number": "TEST-001",
                "installation_date": "2026-01-20",
            },
            "is_active": True,
        },
        {
            "name": "انتهاء التركيب",
            "message_type": "INSTALLATION_COMPLETED",
            "meta_template_name": "installing_done",
            "language": "ar",
            "test_variables": {
                "customer_name": "عميل تجريبي",
                "order_number": "TEST-001",
            },
            "is_active": True,
        },
    ]

    created_templates = []
    for data in templates_data:
        template, created = WhatsAppMessageTemplate.objects.get_or_create(
            message_type=data["message_type"], defaults=data
        )
        created_templates.append(template)
        if created:
            print(f"  ✅ تم إنشاء قالب: {data['name']}")
        else:
            print(f"  ⚠️ قالب موجود: {data['name']}")

    # إنشاء الإعدادات الأساسية (بدون بيانات الاعتماد)
    settings, created = WhatsAppSettings.objects.get_or_create(
        pk=1,
        defaults={
            "phone_number": "",  # يُضاف يدوياً
            "business_account_id": "",  # يُضاف يدوياً
            "phone_number_id": "",  # يُضاف يدوياً
            "access_token": "",  # يُضاف يدوياً
            "is_active": False,  # معطل حتى إضافة البيانات
            "test_mode": False,
            "retry_failed_messages": True,
            "max_retry_attempts": 3,
            "default_language": "ar",
            "use_template": False,
        },
    )

    if created:
        print("  ✅ تم إنشاء إعدادات WhatsApp الأساسية")
        print("  ⚠️ يجب إضافة بيانات الاعتماد يدوياً من لوحة التحكم:")
        print("     - phone_number")
        print("     - business_account_id")
        print("     - phone_number_id")
        print("     - access_token")
        print("     - header_image (صورة الهيدر)")
    else:
        print("  ⚠️ إعدادات WhatsApp موجودة مسبقاً")

    # تفعيل جميع القوالب في الإعدادات
    if created_templates:
        settings.enabled_templates.set(created_templates)
        print(f"  ✅ تم تفعيل {len(created_templates)} قالب")


def reverse_data(apps, schema_editor):
    """لا نحذف البيانات عند الرجوع"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp", "0023_dynamic_template_activation"),
    ]

    operations = [
        migrations.RunPython(create_initial_data, reverse_data),
    ]
