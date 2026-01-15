from django.db import migrations


def remove_redundant_tailoring(apps, schema_editor):
    WizardFieldOption = apps.get_model("orders", "WizardFieldOption")

    # Generic options to remove
    REDUNDANT_OPTIONS = [
        "rings",
        "tape",
        "snap",
        "double_fold",
        "triple_fold",
        "pencil_pleat",
        "eyelet",
        "tab_top",
    ]

    WizardFieldOption.objects.filter(
        field_type="tailoring_type", value__in=REDUNDANT_OPTIONS
    ).delete()


def reverse_remove_redundant_tailoring(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0085_add_detailed_tailoring_options"),
    ]

    operations = [
        migrations.RunPython(
            remove_redundant_tailoring, reverse_remove_redundant_tailoring
        ),
    ]
