# Generated migration to update wizard settings fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0062_wizard_customization_default_data"),
    ]

    operations = [
        # إزالة الحقول القديمة
        migrations.RemoveField(
            model_name="wizardglobalsettings",
            name="require_contract_for_types",
        ),
        migrations.RemoveField(
            model_name="wizardglobalsettings",
            name="require_inspection_for_types",
        ),
        # إضافة حقول جديدة للعقد
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_contract_for_installation",
            field=models.BooleanField(
                default=True,
                help_text="هل يتطلب طلب التركيب عقداً؟",
                verbose_name="تطلب عقد للتركيب",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_contract_for_tailoring",
            field=models.BooleanField(
                default=True,
                help_text="هل يتطلب طلب التفصيل عقداً؟",
                verbose_name="تطلب عقد للتفصيل",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_contract_for_accessory",
            field=models.BooleanField(
                default=True,
                help_text="هل يتطلب طلب الإكسسوار عقداً؟",
                verbose_name="تطلب عقد للإكسسوار",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_contract_for_inspection",
            field=models.BooleanField(
                default=False,
                help_text="هل يتطلب طلب المعاينة عقداً؟",
                verbose_name="تطلب عقد للمعاينة",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_contract_for_products",
            field=models.BooleanField(
                default=False,
                help_text="هل يتطلب طلب المنتجات عقداً؟",
                verbose_name="تطلب عقد للمنتجات",
            ),
        ),
        # إضافة حقول جديدة للمعاينة
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_inspection_for_installation",
            field=models.BooleanField(
                default=True,
                help_text="هل يتطلب طلب التركيب معاينة؟",
                verbose_name="تطلب معاينة للتركيب",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_inspection_for_tailoring",
            field=models.BooleanField(
                default=True,
                help_text="هل يتطلب طلب التفصيل معاينة؟",
                verbose_name="تطلب معاينة للتفصيل",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_inspection_for_accessory",
            field=models.BooleanField(
                default=True,
                help_text="هل يتطلب طلب الإكسسوار معاينة؟",
                verbose_name="تطلب معاينة للإكسسوار",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_inspection_for_inspection",
            field=models.BooleanField(
                default=True,
                help_text="هل يتطلب طلب المعاينة معاينة مسبقة؟",
                verbose_name="تطلب معاينة مسبقة للمعاينة",
            ),
        ),
        migrations.AddField(
            model_name="wizardglobalsettings",
            name="require_inspection_for_products",
            field=models.BooleanField(
                default=False,
                help_text="هل يتطلب طلب المنتجات معاينة؟",
                verbose_name="تطلب معاينة للمنتجات",
            ),
        ),
    ]
