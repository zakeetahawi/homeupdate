# Generated migration to update tailoring_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0063_update_wizard_settings_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="curtainfabric",
            name="tailoring_type",
            field=models.CharField(
                blank=True,
                help_text="طريقة التفصيل - يتم جلب الخيارات من نظام التخصيص",
                max_length=50,
                verbose_name="نوع التفصيل",
            ),
        ),
    ]
