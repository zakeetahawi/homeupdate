from django.db import migrations


def add_detailed_tailoring_options(apps, schema_editor):
    WizardFieldOption = apps.get_model("orders", "WizardFieldOption")

    TAILORING_OPTIONS = [
        {"value": "tape15", "display_name": "وصلات", "sequence": 1},
        {"value": "tape3", "display_name": "شريط 3 فتلة", "sequence": 2},
        {"value": "tape4", "display_name": "شريط 4 فتلة", "sequence": 3},
        {"value": "tape11", "display_name": "ويف كبسولة", "sequence": 4},
        {"value": "tape9", "display_name": "تكسير يمين شمال", "sequence": 5},
        {"value": "tape5", "display_name": "شوكة مزدوجة", "sequence": 6},
        {"value": "tape6", "display_name": "شوكة ثلاثية", "sequence": 7},
        {"value": "tape14", "display_name": "شريط ايكيا", "sequence": 8},
        {"value": "tape7", "display_name": "تكسير يمين", "sequence": 9},
        {"value": "tape8", "display_name": "تكسير شمال", "sequence": 10},
        {"value": "tape10", "display_name": "كالونات 9 سنتم", "sequence": 11},
        {"value": "tape1", "display_name": "حلقات بلاستك", "sequence": 12},
        {"value": "tape2", "display_name": "حلقات كبس معدن", "sequence": 13},
        {"value": "tape12", "display_name": "تفصيل كوشن", "sequence": 14},
        {"value": "belt", "display_name": "حزام", "sequence": 15},
    ]

    for option in TAILORING_OPTIONS:
        WizardFieldOption.objects.update_or_create(
            field_type="tailoring_type",
            value=option["value"],
            defaults={
                "display_name": option["display_name"],
                "sequence": option["sequence"],
                "is_active": True,
            },
        )


def reverse_add_detailed_tailoring_options(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0084_populate_wizard_options"),
    ]

    operations = [
        migrations.RunPython(
            add_detailed_tailoring_options, reverse_add_detailed_tailoring_options
        ),
    ]
