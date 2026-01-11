# Generated manually on 2025-11-24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0058_create_default_system_settings"),
    ]

    operations = [
        # حذف جدول SystemSettings بشكل كامل
        migrations.DeleteModel(
            name="SystemSettings",
        ),
    ]
