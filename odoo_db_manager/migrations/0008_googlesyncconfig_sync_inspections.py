# Generated by Django 4.2.21 on 2025-06-11 08:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('odoo_db_manager', '0007_googlesyncconfig_googlesynclog'),
    ]

    operations = [
        migrations.AddField(
            model_name='googlesyncconfig',
            name='sync_inspections',
            field=models.BooleanField(default=True, verbose_name='مزامنة المعاينات'),
        ),
    ]
