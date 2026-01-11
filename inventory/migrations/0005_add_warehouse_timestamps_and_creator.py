# Generated manually to add timestamps and creator to Warehouse model

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def set_default_timestamps(apps, schema_editor):
    """Set default timestamps for existing warehouses"""
    Warehouse = apps.get_model("inventory", "Warehouse")
    for warehouse in Warehouse.objects.all():
        warehouse.created_at = timezone.now()
        warehouse.updated_at = timezone.now()
        warehouse.save()


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_add_warehouse_to_stock_transaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouse",
            name="created_at",
            field=models.DateTimeField(
                verbose_name="تاريخ الإنشاء", auto_now_add=True, default=timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="warehouse",
            name="updated_at",
            field=models.DateTimeField(verbose_name="تاريخ التحديث", auto_now=True),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_warehouses",
                to="accounts.user",
                verbose_name="تم الإنشاء بواسطة",
            ),
        ),
        migrations.RunPython(
            set_default_timestamps, reverse_code=migrations.RunPython.noop
        ),
    ]
