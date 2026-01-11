# Generated migration to update installation_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0064_update_tailoring_type_field"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contractcurtain",
            name="installation_type",
            field=models.CharField(
                blank=True,
                help_text="نوع التركيب - يتم جلب الخيارات من نظام التخصيص",
                max_length=50,
                verbose_name="نوع التركيب",
            ),
        ),
    ]
