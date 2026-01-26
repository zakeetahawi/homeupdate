from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0030_product_deleted_by_productbatch_deleted_by_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="product",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="product",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_product_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="supplier",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="supplier",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="supplier",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_supplier_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_warehouse_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="warehouselocation",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="warehouselocation",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="warehouselocation",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_warehouselocation_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="productbatch",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="productbatch",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="productbatch",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_productbatch_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_purchaseorder_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="purchaseorderitem",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="purchaseorderitem",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="purchaseorderitem",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_purchaseorderitem_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
    ]
