# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0068_add_all_wizard_field_options"),
    ]

    operations = [
        # إصلاح حقل notes و reference_number في Payment
        migrations.AlterField(
            model_name="payment",
            name="reference_number",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="رقم المرجع"
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="notes",
            field=models.TextField(blank=True, null=True, verbose_name="ملاحظات"),
        ),
    ]
