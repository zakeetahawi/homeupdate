# Generated manually to fix null values in allowed_order_types

from django.db import migrations


def fix_null_allowed_order_types(apps, schema_editor):
    """إصلاح القيم null في حقل allowed_order_types"""
    ManufacturingDisplaySettings = apps.get_model(
        "manufacturing", "ManufacturingDisplaySettings"
    )

    # تحديث جميع السجلات التي تحتوي على null
    for setting in ManufacturingDisplaySettings.objects.all():
        if setting.allowed_order_types is None:
            setting.allowed_order_types = []
            setting.save()
        if setting.allowed_statuses is None:
            setting.allowed_statuses = []
            setting.save()


def reverse_fix_null_allowed_order_types(apps, schema_editor):
    """عكس العملية - لا نحتاج لفعل شيء"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("manufacturing", "0007_manufacturingdisplaysettings"),
    ]

    operations = [
        migrations.RunPython(
            fix_null_allowed_order_types, reverse_fix_null_allowed_order_types
        ),
    ]
