from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ("cutting", "0016_cuttingorder_deleted_by_cuttingorderitem_deleted_by"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="cuttingorder",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="cuttingorder",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="cuttingorder",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cutting_cuttingorder_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="cuttingorderitem",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="cuttingorderitem",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="cuttingorderitem",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cutting_cuttingorderitem_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
    ]
