# Generated by Django 4.2.21 on 2025-07-17 11:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0001_initial'),
        ('orders', '0002_order_inspection_status_order_installation_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='related_inspection',
            field=models.ForeignKey(blank=True, help_text='المعاينة المرتبطة بهذا الطلب', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='related_orders', to='inspections.inspection', verbose_name='معاينة مرتبطة'),
        ),
    ]
