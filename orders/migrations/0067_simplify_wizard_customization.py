# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0066_update_installation_types_data"),
    ]

    operations = [
        # 1. إعادة تسمية display_name_ar إلى display_name
        migrations.RenameField(
            model_name="wizardfieldoption",
            old_name="display_name_ar",
            new_name="display_name",
        ),
        # 2. حذف الحقول غير الضرورية
        migrations.RemoveField(
            model_name="wizardfieldoption",
            name="display_name_en",
        ),
        migrations.RemoveField(
            model_name="wizardfieldoption",
            name="description",
        ),
        migrations.RemoveField(
            model_name="wizardfieldoption",
            name="icon",
        ),
        migrations.RemoveField(
            model_name="wizardfieldoption",
            name="color",
        ),
        # 3. تحديث field_type choices
        migrations.AlterField(
            model_name="wizardfieldoption",
            name="field_type",
            field=models.CharField(
                choices=[
                    ("tailoring_type", "طريقة التفصيل"),
                    ("installation_type", "نوع التركيب"),
                    ("payment_method", "طريقة الدفع"),
                    ("order_status", "حالة الطلب"),
                    ("service_type", "نوع الخدمة"),
                ],
                help_text="نوع الحقل الذي ينتمي إليه هذا الخيار",
                max_length=50,
                verbose_name="نوع الحقل",
            ),
        ),
        # 4. تحديث display_name help_text
        migrations.AlterField(
            model_name="wizardfieldoption",
            name="display_name",
            field=models.CharField(
                help_text="النص الذي سيظهر للمستخدم",
                max_length=200,
                verbose_name="ما يظهر بالحقل",
            ),
        ),
        # 5. تحديث value help_text
        migrations.AlterField(
            model_name="wizardfieldoption",
            name="value",
            field=models.CharField(
                help_text="القيمة المخزنة في قاعدة البيانات",
                max_length=100,
                verbose_name="القيمة (بالإنجليزية)",
            ),
        ),
        # 6. تحديث sequence help_text
        migrations.AlterField(
            model_name="wizardfieldoption",
            name="sequence",
            field=models.IntegerField(
                default=0, help_text="ترتيب العرض", verbose_name="الترتيب"
            ),
        ),
        # 7. تحديث is_active help_text
        migrations.AlterField(
            model_name="wizardfieldoption",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="نشط"),
        ),
        # 8. تحديث is_default help_text
        migrations.AlterField(
            model_name="wizardfieldoption",
            name="is_default",
            field=models.BooleanField(default=False, verbose_name="افتراضي"),
        ),
        # 9. تحديث extra_data verbose_name
        migrations.AlterField(
            model_name="wizardfieldoption",
            name="extra_data",
            field=models.JSONField(
                blank=True, default=dict, verbose_name="بيانات إضافية"
            ),
        ),
        # 10. تحديث Meta
        migrations.AlterModelOptions(
            name="wizardfieldoption",
            options={
                "ordering": ["field_type", "sequence", "display_name"],
                "verbose_name": "خيار حقل",
                "verbose_name_plural": "خيارات الحقول",
            },
        ),
        # 11. حذف الـ indexes القديمة إذا كانت موجودة
        migrations.AlterUniqueTogether(
            name="wizardfieldoption",
            unique_together={("field_type", "value")},
        ),
    ]
