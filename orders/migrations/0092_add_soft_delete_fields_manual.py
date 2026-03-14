from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0091_draftorderitem_is_manual_price_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Order fields
        migrations.AddField(
            model_name="order",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="order",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="order",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders_order_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        # OrderItem fields
        migrations.AddField(
            model_name="orderitem",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders_orderitem_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
    ]
