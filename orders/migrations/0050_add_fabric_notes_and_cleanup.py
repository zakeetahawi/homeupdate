# Generated manually on 2025-11-22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0049_dynamiccontracttemplate_templatesection_and_more"),
    ]

    operations = [
        # إضافة حقل الملاحظات للأقمشة
        migrations.AddField(
            model_name="curtainfabric",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="ملاحظات خاصة بهذا القماش",
                verbose_name="ملاحظات القماش",
            ),
        ),
        # حذف النماذج القديمة غير المستخدمة من منشئ القوالب
        migrations.DeleteModel(
            name="TemplateSectionField",
        ),
        migrations.DeleteModel(
            name="TemplateSection",
        ),
        migrations.DeleteModel(
            name="TemplateStyle",
        ),
        migrations.DeleteModel(
            name="DynamicContractTemplate",
        ),
    ]
