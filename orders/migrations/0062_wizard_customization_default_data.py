# Generated migration for wizard customization default data

from django.db import migrations


def create_default_wizard_options(apps, schema_editor):
    """إنشاء خيارات الويزارد الافتراضية"""
    WizardFieldOption = apps.get_model("orders", "WizardFieldOption")

    # طرق التفصيل
    tailoring_types = [
        ("rings", "حلقات", "fas fa-ring", 1),
        ("tape", "شريط", "fas fa-tape", 2),
        ("snap", "كبس", "fas fa-hand-point-up", 3),
        ("double_fold", "كسرة مزدوجة", "fas fa-layer-group", 4),
        ("triple_fold", "كسرة ثلاثية", "fas fa-bars", 5),
        ("pencil_pleat", "كسرة قلم", "fas fa-pen", 6),
        ("eyelet", "عراوي", "fas fa-circle", 7),
        ("tab_top", "عروة علوية", "fas fa-paperclip", 8),
    ]

    for value, display, icon, seq in tailoring_types:
        WizardFieldOption.objects.create(
            field_type="tailoring_type",
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=(value == "rings"),  # الحلقات كافتراضي
        )

    # أنواع التركيب
    installation_types = [
        ("wall_mount", "تركيب جداري", "fas fa-arrows-alt-h", 1),
        ("ceiling_mount", "تركيب سقفي", "fas fa-arrow-up", 2),
        ("curtain_box", "بيت ستارة", "fas fa-box", 3),
        ("rod_only", "قضيب فقط", "fas fa-minus", 4),
    ]

    for value, display, icon, seq in installation_types:
        WizardFieldOption.objects.create(
            field_type="installation_type",
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=(value == "wall_mount"),
        )

    # أنواع القماش
    fabric_types = [
        ("light", "قماش خفيف (شيفون/تل)", "fas fa-cloud", 1),
        ("heavy", "قماش ثقيل (قطيفة/مخمل)", "fas fa-weight-hanging", 2),
        ("blackout", "قماش معتم (بلاك أوت)", "fas fa-moon", 3),
        ("sheer", "قماش شفاف", "fas fa-eye", 4),
    ]

    for value, display, icon, seq in fabric_types:
        WizardFieldOption.objects.create(
            field_type="fabric_type",
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=(value == "light"),
        )

    # طرق الدفع
    payment_methods = [
        ("cash", "نقدي", "fas fa-money-bill-wave", 1),
        ("card", "بطاقة", "fas fa-credit-card", 2),
        ("bank_transfer", "تحويل بنكي", "fas fa-university", 3),
        ("installment", "تقسيط", "fas fa-calendar-alt", 4),
    ]

    for value, display, icon, seq in payment_methods:
        WizardFieldOption.objects.create(
            field_type="payment_method",
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=(value == "cash"),
        )

    # حالات الطلب
    order_statuses = [
        ("normal", "عادي", "fas fa-user", 1),
        ("vip", "VIP", "fas fa-crown", 2),
    ]

    for value, display, icon, seq in order_statuses:
        WizardFieldOption.objects.create(
            field_type="order_status",
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=(value == "normal"),
        )

    # أنواع الطلبات
    order_types = [
        ("installation", "تركيب ستائر", "fas fa-tools", 1),
        ("tailoring", "تفصيل ستائر", "fas fa-scissors", 2),
        ("accessory", "إكسسوارات فقط", "fas fa-puzzle-piece", 3),
        ("inspection", "معاينة", "fas fa-eye", 4),
        ("products", "منتجات", "fas fa-box-open", 5),
    ]

    for value, display, icon, seq in order_types:
        WizardFieldOption.objects.create(
            field_type="order_type",
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=(value == "installation"),
        )


def create_wizard_global_settings(apps, schema_editor):
    """إنشاء الإعدادات العامة الافتراضية للويزارد"""
    WizardGlobalSettings = apps.get_model("orders", "WizardGlobalSettings")

    # التحقق من عدم وجود إعدادات مسبقاً
    if not WizardGlobalSettings.objects.exists():
        WizardGlobalSettings.objects.create(
            pk=1,
            enable_wizard=True,
            enable_draft_auto_save=True,
            draft_expiry_days=30,
            minimum_payment_percentage="50.00",
            allow_payment_exceed_total=True,
            require_contract_for_types=["installation", "tailoring", "accessory"],
            enable_electronic_contract=True,
            enable_pdf_contract_upload=True,
            require_inspection_for_types=["installation", "tailoring", "accessory"],
            allow_customer_side_measurements=True,
            send_notification_on_draft_created=False,
            send_notification_on_order_created=True,
            show_progress_bar=True,
            theme_color="primary",
        )


def reverse_migration(apps, schema_editor):
    """التراجع عن التغييرات"""
    WizardFieldOption = apps.get_model("orders", "WizardFieldOption")
    WizardGlobalSettings = apps.get_model("orders", "WizardGlobalSettings")

    WizardFieldOption.objects.all().delete()
    WizardGlobalSettings.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0061_wizard_customization_models"),
    ]

    operations = [
        migrations.RunPython(
            create_default_wizard_options, reverse_code=reverse_migration
        ),
        migrations.RunPython(
            create_wizard_global_settings, reverse_code=reverse_migration
        ),
    ]
