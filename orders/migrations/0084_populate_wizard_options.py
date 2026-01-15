from django.db import migrations


def populate_wizard_options(apps, schema_editor):
    WizardFieldOption = apps.get_model("orders", "WizardFieldOption")

    OPTIONS = [
        # Order Types
        {
            "field_type": "order_type",
            "value": "accessory",
            "display_name": "إكسسوار",
            "sequence": 1,
            "extra_data": {
                "icon": "fas fa-gem",
                "color_class": "text-primary",
                "description": "موجه إلى ورشة الإكسسوار",
            },
        },
        {
            "field_type": "order_type",
            "value": "installation",
            "display_name": "التركيب",
            "sequence": 2,
            "extra_data": {
                "icon": "fas fa-tools",
                "color_class": "text-success",
                "description": "موجه إلى المصنع",
            },
        },
        {
            "field_type": "order_type",
            "value": "tailoring",
            "display_name": "التنجيد/التفصيل",
            "sequence": 3,
            "extra_data": {
                "icon": "fas fa-cut",
                "color_class": "text-warning",
                "description": "موجه إلى المصنع",
            },
        },
        {
            "field_type": "order_type",
            "value": "inspection",
            "display_name": "المعاينة",
            "sequence": 4,
            "extra_data": {
                "icon": "fas fa-eye",
                "color_class": "text-info",
                "description": "موجه لقسم المعاينات",
            },
        },
        {
            "field_type": "order_type",
            "value": "products",
            "display_name": "المنتجات",
            "sequence": 5,
            "extra_data": {
                "icon": "fas fa-boxes",
                "color_class": "text-secondary",
                "description": "موجه للمخازن",
            },
        },
        # Fabric Types
        {
            "field_type": "fabric_type",
            "value": "light",
            "display_name": "خفيف",
            "sequence": 1,
            "extra_data": {"badge_class": "warning"},
        },
        {
            "field_type": "fabric_type",
            "value": "heavy",
            "display_name": "ثقيل",
            "sequence": 2,
            "extra_data": {"badge_class": "danger"},
        },
        {
            "field_type": "fabric_type",
            "value": "blackout",
            "display_name": "بلاك أوت",
            "sequence": 3,
            "extra_data": {"badge_class": "dark"},
        },
        {
            "field_type": "fabric_type",
            "value": "additional",
            "display_name": "إضافي",
            "sequence": 4,
            "extra_data": {"badge_class": "secondary"},
        },
        # Installation Types
        {
            "field_type": "installation_type",
            "value": "wall_mount",
            "display_name": "تركيب جداري",
            "sequence": 1,
            "extra_data": {"requires_curtain_box": False},
        },
        {
            "field_type": "installation_type",
            "value": "ceiling_mount",
            "display_name": "تركيب سقفي",
            "sequence": 2,
            "extra_data": {"requires_curtain_box": False},
        },
        {
            "field_type": "installation_type",
            "value": "curtain_box",
            "display_name": "بيت ستارة",
            "sequence": 3,
            "extra_data": {"requires_curtain_box": True},
        },
        {
            "field_type": "installation_type",
            "value": "rod_only",
            "display_name": "قضيب فقط",
            "sequence": 4,
            "extra_data": {"requires_curtain_box": False},
        },
        # Tailoring Types
        {
            "field_type": "tailoring_type",
            "value": "rings",
            "display_name": "حلقات",
            "sequence": 1,
            "extra_data": {},
        },
        {
            "field_type": "tailoring_type",
            "value": "tape",
            "display_name": "شريط",
            "sequence": 2,
            "extra_data": {},
        },
        {
            "field_type": "tailoring_type",
            "value": "snap",
            "display_name": "كبس",
            "sequence": 3,
            "extra_data": {},
        },
        {
            "field_type": "tailoring_type",
            "value": "double_fold",
            "display_name": "كسرة مزدوجة",
            "sequence": 4,
            "extra_data": {},
        },
        {
            "field_type": "tailoring_type",
            "value": "triple_fold",
            "display_name": "كسرة ثلاثية",
            "sequence": 5,
            "extra_data": {},
        },
        {
            "field_type": "tailoring_type",
            "value": "pencil_pleat",
            "display_name": "كسرة قلم",
            "sequence": 6,
            "extra_data": {},
        },
        {
            "field_type": "tailoring_type",
            "value": "eyelet",
            "display_name": "عراوي",
            "sequence": 7,
            "extra_data": {},
        },
        {
            "field_type": "tailoring_type",
            "value": "tab_top",
            "display_name": "عروة علوية",
            "sequence": 8,
            "extra_data": {},
        },
    ]

    for option in OPTIONS:
        WizardFieldOption.objects.update_or_create(
            field_type=option["field_type"],
            value=option["value"],
            defaults={
                "display_name": option["display_name"],
                "sequence": option["sequence"],
                "extra_data": option["extra_data"],
                "is_active": True,
            },
        )


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0083_alter_wizardfieldoption_field_type"),
    ]

    operations = [
        migrations.RunPython(populate_wizard_options, reverse_populate),
    ]
