# Generated migration

from django.db import migrations


def add_all_field_options(apps, schema_editor):
    """إضافة جميع الخيارات الثابتة من النظام"""
    WizardFieldOption = apps.get_model("orders", "WizardFieldOption")

    # 1. حالات الطلب (ORDER_STATUS_CHOICES)
    order_statuses = [
        ("pending_approval", "قيد الموافقة", 1),
        ("pending", "قيد الانتظار", 2),
        ("in_progress", "قيد التصنيع", 3),
        ("ready_install", "جاهز للتركيب", 4),
        ("completed", "مكتمل", 5),
        ("delivered", "تم التسليم", 6),
        ("rejected", "مرفوض", 7),
        ("cancelled", "ملغي", 8),
        ("manufacturing_deleted", "أمر تصنيع محذوف", 9),
    ]

    # حذف حالات الطلب القديمة
    WizardFieldOption.objects.filter(field_type="order_status").delete()

    for value, display, seq in order_statuses:
        WizardFieldOption.objects.create(
            field_type="order_status",
            value=value,
            display_name=display,
            sequence=seq,
            is_active=True,
            is_default=(value == "pending"),
        )

    # 2. طرق الدفع (PAYMENT_METHOD_CHOICES)
    payment_methods = [
        ("cash", "نقداً", 1),
        ("bank_transfer", "تحويل بنكي", 2),
        ("check", "شيك", 3),
    ]

    # حذف طرق الدفع القديمة
    WizardFieldOption.objects.filter(field_type="payment_method").delete()

    for value, display, seq in payment_methods:
        WizardFieldOption.objects.create(
            field_type="payment_method",
            value=value,
            display_name=display,
            sequence=seq,
            is_active=True,
            is_default=(value == "cash"),
        )

    # 3. أنواع الخدمة (SERVICE_TYPE_CHOICES)
    service_types = [
        ("accessory", "إكسسوار", 1),
        ("products", "منتجات", 2),
        ("installation", "تركيب", 3),
        ("tailoring", "تسليم", 4),
        ("inspection", "معاينة", 5),
    ]

    # حذف أنواع الخدمة القديمة
    WizardFieldOption.objects.filter(field_type="service_type").delete()

    for value, display, seq in service_types:
        WizardFieldOption.objects.create(
            field_type="service_type",
            value=value,
            display_name=display,
            sequence=seq,
            is_active=True,
            is_default=(value == "installation"),
        )

    # 4. التحقق من وجود طرق التفصيل وأنواع التركيب (تم إضافتها سابقاً)
    # إذا لم تكن موجودة، سيتم إضافتها

    # طرق التفصيل
    if not WizardFieldOption.objects.filter(field_type="tailoring_type").exists():
        tailoring_types = [
            ("rings", "حلقات", 1),
            ("pleated", "كسرات", 2),
            ("eyelets", "ثقوب", 3),
            ("rod_pocket", "جيب عمود", 4),
            ("tab_top", "بطانة علوية", 5),
            ("tie_top", "ربطات", 6),
            ("grommet", "حلقات معدنية", 7),
            ("pinch_pleat", "كسرات مقروصة", 8),
        ]

        for value, display, seq in tailoring_types:
            WizardFieldOption.objects.create(
                field_type="tailoring_type",
                value=value,
                display_name=display,
                sequence=seq,
                is_active=True,
                is_default=(value == "rings"),
            )

    # أنواع التركيب
    if not WizardFieldOption.objects.filter(field_type="installation_type").exists():
        installation_types = [
            ("wall_gypsum", "حائط - جبس", 1),
            ("wall_concrete", "حائط - مسلح", 2),
            ("ceiling_gypsum", "سقف - جبس", 3),
            ("ceiling_concrete", "سقف - مسلح", 4),
            ("curtain_box_concrete", "بيت ستارة مسلح", 5, True),
            ("curtain_box_gypsum", "بيت ستارة جبس", 6, True),
        ]

        for item in installation_types:
            value, display, seq = item[0], item[1], item[2]
            requires_box = item[3] if len(item) > 3 else False

            extra = {"requires_curtain_box": requires_box} if requires_box else {}

            WizardFieldOption.objects.create(
                field_type="installation_type",
                value=value,
                display_name=display,
                sequence=seq,
                is_active=True,
                is_default=(value == "wall_concrete"),
                extra_data=extra,
            )


def reverse_add_field_options(apps, schema_editor):
    """عكس العملية"""
    WizardFieldOption = apps.get_model("orders", "WizardFieldOption")
    # حذف جميع الخيارات المضافة
    WizardFieldOption.objects.filter(
        field_type__in=["order_status", "payment_method", "service_type"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0067_simplify_wizard_customization"),
    ]

    operations = [
        migrations.RunPython(add_all_field_options, reverse_add_field_options),
    ]
