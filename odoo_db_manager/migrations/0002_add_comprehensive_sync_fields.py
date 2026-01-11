# Generated migration for comprehensive sync fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("odoo_db_manager", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_manufacturing_orders",
            field=models.BooleanField(
                default=True, verbose_name="مزامنة أوامر التصنيع"
            ),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_technicians",
            field=models.BooleanField(default=True, verbose_name="مزامنة الفنيين"),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_installation_teams",
            field=models.BooleanField(default=True, verbose_name="مزامنة فرق التركيب"),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_suppliers",
            field=models.BooleanField(default=True, verbose_name="مزامنة الموردين"),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_salespersons",
            field=models.BooleanField(default=True, verbose_name="مزامنة البائعين"),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_comprehensive_customers",
            field=models.BooleanField(
                default=False, verbose_name="مزامنة العملاء الشاملة"
            ),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_comprehensive_users",
            field=models.BooleanField(
                default=False, verbose_name="مزامنة المستخدمين الشاملة"
            ),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_comprehensive_inventory",
            field=models.BooleanField(
                default=False, verbose_name="مزامنة المنتجات والمخزون الشاملة"
            ),
        ),
        migrations.AddField(
            model_name="googlesyncconfig",
            name="sync_comprehensive_system",
            field=models.BooleanField(
                default=False, verbose_name="مزامنة إعدادات النظام الشاملة"
            ),
        ),
    ]
