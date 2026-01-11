# Generated manually on 2025-11-23 19:13

from django.db import migrations


def create_default_settings(apps, schema_editor):
    """إنشاء إعدادات النظام الافتراضية"""
    SystemSettings = apps.get_model("orders", "SystemSettings")

    # حذف أي إعدادات قديمة
    SystemSettings.objects.all().delete()

    # الإعدادات الافتراضية
    default_settings = {
        "name": "default",
        "order_system": "both",
        "edit_priority": "source",
        "hide_legacy_system": False,
        "hide_wizard_system": False,
        "allow_legacy_to_wizard_conversion": True,
        "tailoring_types": [
            {"value": "regular", "label": "عادي"},
            {"value": "pleated", "label": "كسرات"},
            {"value": "eyelet", "label": "حلقات"},
            {"value": "rod_pocket", "label": "جيب"},
            {"value": "tab_top", "label": "ألسنة"},
        ],
        "fabric_types": [
            {"value": "light", "label": "خفيف"},
            {"value": "heavy", "label": "ثقيل"},
            {"value": "blackout", "label": "بلاك أوت"},
            {"value": "extra", "label": "إضافي"},
        ],
        "installation_types": [
            {"value": "wall", "label": "حائط"},
            {"value": "ceiling", "label": "سقف"},
            {"value": "box", "label": "بيت ستارة"},
        ],
        "payment_methods": [
            {"value": "cash", "label": "نقدي"},
            {"value": "card", "label": "بطاقة"},
            {"value": "bank_transfer", "label": "تحويل بنكي"},
            {"value": "installment", "label": "تقسيط"},
        ],
        "require_contract_number": True,
        "require_contract_file": False,
        "enable_wizard_notifications": True,
    }

    SystemSettings.objects.create(**default_settings)


def reverse_settings(apps, schema_editor):
    """حذف الإعدادات عند التراجع"""
    SystemSettings = apps.get_model("orders", "SystemSettings")
    SystemSettings.objects.filter(name="default").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0057_add_wizard_integration_fields"),
    ]

    operations = [
        migrations.RunPython(create_default_settings, reverse_settings),
    ]
