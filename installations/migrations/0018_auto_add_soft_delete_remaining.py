from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ("installations", "0017_driver_deleted_by_installationschedule_deleted_by_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="technician",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="technician",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="technician",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="installations_technician_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="driver",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="driver",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="driver",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="installations_driver_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="installationteam",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="installationteam",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="installationteam",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="installations_installationteam_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="installationschedule",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="installationschedule",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="installationschedule",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="installations_installationschedule_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="modificationrequest",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="modificationrequest",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="modificationrequest",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="installations_modificationrequest_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
        migrations.AddField(
            model_name="manufacturingorder",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False, verbose_name="محذوف"),
        ),
        migrations.AddField(
            model_name="manufacturingorder",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الحذف"),
        ),
        migrations.AddField(
            model_name="manufacturingorder",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="installations_manufacturingorder_deleted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="حذف بواسطة",
            ),
        ),
    ]
