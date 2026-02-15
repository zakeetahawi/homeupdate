"""
إعادة تسمية ManufacturingOrder → ModificationManufacturingOrder
مع الحفاظ على جدول installations_manufacturingorder بدون تغيير
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("installations", "0024_customerdebt_inst_debt_cust_paid_idx_and_more"),
    ]

    operations = [
        # 1. إعادة تسمية النموذج — الجدول لا يتغير لأن db_table مُحدد
        migrations.RenameModel(
            old_name="ManufacturingOrder",
            new_name="ModificationManufacturingOrder",
        ),
        # 2. تحديث related_name على modification_request FK
        migrations.AlterField(
            model_name="modificationmanufacturingorder",
            name="modification_request",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="modification_manufacturing_orders",
                to="installations.modificationrequest",
                verbose_name="طلب التعديل",
            ),
        ),
        # 3. تحديث FK في ModificationReport
        migrations.AlterField(
            model_name="modificationreport",
            name="manufacturing_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="installations.modificationmanufacturingorder",
                verbose_name="أمر التصنيع",
            ),
        ),
    ]
