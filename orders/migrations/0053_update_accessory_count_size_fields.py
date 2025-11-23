# Generated manually on 2025-11-23
from django.db import migrations, models
from decimal import Decimal


def set_default_values(apps, schema_editor):
    """Set default values for empty size fields before converting to decimal"""
    CurtainAccessory = apps.get_model('orders', 'CurtainAccessory')
    # Update empty sizes to '1'
    CurtainAccessory.objects.filter(size='').update(size='1')
    CurtainAccessory.objects.filter(size__isnull=True).update(size='1')


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0052_add_invoice_item_link_to_accessories"),
    ]

    operations = [
        # Step 1: Add count field
        migrations.AddField(
            model_name="curtainaccessory",
            name="count",
            field=models.IntegerField(
                default=1,
                help_text="عدد القطع",
                verbose_name="العدد",
            ),
        ),
        
        # Step 2: Set default values for size
        migrations.RunPython(set_default_values, migrations.RunPython.noop),
        
        # Step 3: Change size from CharField to DecimalField
        migrations.AlterField(
            model_name="curtainaccessory",
            name="size",
            field=models.DecimalField(
                decimal_places=3,
                default=1,
                help_text="المقاس لكل قطعة",
                max_digits=10,
                verbose_name="المقاس",
            ),
        ),
        
        # Step 4: Update quantity field description
        migrations.AlterField(
            model_name="curtainaccessory",
            name="quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=1,
                help_text="الكمية الإجمالية = العدد × المقاس",
                max_digits=10,
                verbose_name="الكمية الإجمالية",
            ),
        ),
    ]
