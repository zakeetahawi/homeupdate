# Generated migration for wizard customization models

from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0059_remove_systemsettings"),  # آخر migration موجود
    ]

    operations = [
        # إنشاء جدول خيارات حقول الويزارد
        migrations.CreateModel(
            name="WizardFieldOption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "field_type",
                    models.CharField(
                        choices=[
                            ("tailoring_type", "طريقة التفصيل"),
                            ("installation_type", "نوع التركيب"),
                            ("fabric_type", "نوع القماش"),
                            ("payment_method", "طريقة الدفع"),
                            ("order_status", "حالة الطلب"),
                            ("order_type", "نوع الطلب"),
                        ],
                        help_text="نوع الحقل الذي ينتمي إليه هذا الخيار",
                        max_length=50,
                        verbose_name="نوع الحقل",
                    ),
                ),
                (
                    "value",
                    models.CharField(
                        help_text="القيمة المخزنة في قاعدة البيانات (يجب أن تكون فريدة لكل نوع حقل)",
                        max_length=100,
                        verbose_name="القيمة (بالإنجليزية)",
                    ),
                ),
                (
                    "display_name_ar",
                    models.CharField(
                        help_text="النص الذي سيظهر للمستخدمين",
                        max_length=200,
                        verbose_name="الاسم المعروض (عربي)",
                    ),
                ),
                (
                    "display_name_en",
                    models.CharField(
                        blank=True,
                        help_text="اختياري - الاسم بالإنجليزية",
                        max_length=200,
                        verbose_name="الاسم المعروض (إنجليزي)",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="وصف تفصيلي اختياري", verbose_name="الوصف"
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        blank=True,
                        help_text="اسم الأيقونة (Font Awesome) مثل: fas fa-scissors",
                        max_length=100,
                        verbose_name="الأيقونة",
                    ),
                ),
                (
                    "color",
                    models.CharField(
                        blank=True,
                        default="primary",
                        help_text="لون العرض (مثل: primary, success, info, warning, danger)",
                        max_length=50,
                        verbose_name="اللون",
                    ),
                ),
                (
                    "sequence",
                    models.IntegerField(
                        default=0,
                        help_text="ترتيب العرض (الأصغر أولاً)",
                        verbose_name="الترتيب",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="هل هذا الخيار متاح للاستخدام؟",
                        verbose_name="نشط",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="هل هذا الخيار الافتراضي المحدد؟",
                        verbose_name="افتراضي",
                    ),
                ),
                (
                    "extra_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="بيانات إضافية مخصصة (JSON)",
                        verbose_name="بيانات إضافية",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="تاريخ الإنشاء"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث"),
                ),
            ],
            options={
                "verbose_name": "خيار حقل الويزارد",
                "verbose_name_plural": "خيارات حقول الويزارد",
                "ordering": ["field_type", "sequence", "display_name_ar"],
            },
        ),
        # إنشاء جدول تخصيص خطوات الويزارد
        migrations.CreateModel(
            name="WizardStepConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "step_number",
                    models.IntegerField(
                        choices=[
                            (1, "الخطوة 1 - البيانات الأساسية"),
                            (2, "الخطوة 2 - نوع الطلب"),
                            (3, "الخطوة 3 - عناصر الطلب"),
                            (4, "الخطوة 4 - تفاصيل المرجع والدفع"),
                            (5, "الخطوة 5 - العقد"),
                            (6, "الخطوة 6 - المراجعة والتأكيد"),
                        ],
                        unique=True,
                        verbose_name="رقم الخطوة",
                    ),
                ),
                (
                    "step_title_ar",
                    models.CharField(
                        max_length=200, verbose_name="عنوان الخطوة (عربي)"
                    ),
                ),
                (
                    "step_title_en",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        verbose_name="عنوان الخطوة (إنجليزي)",
                    ),
                ),
                (
                    "step_description",
                    models.TextField(
                        blank=True,
                        help_text="وصف تفصيلي يظهر للمستخدم",
                        verbose_name="وصف الخطوة",
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        blank=True,
                        help_text="أيقونة الخطوة (Font Awesome)",
                        max_length=100,
                        verbose_name="الأيقونة",
                    ),
                ),
                (
                    "is_required",
                    models.BooleanField(
                        default=True,
                        help_text="هل إكمال هذه الخطوة إجباري؟",
                        verbose_name="إجبارية",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="هل هذه الخطوة متاحة؟",
                        verbose_name="نشطة",
                    ),
                ),
                (
                    "help_text",
                    models.TextField(
                        blank=True,
                        help_text="نص مساعدة يظهر للمستخدم في هذه الخطوة",
                        verbose_name="نص المساعدة",
                    ),
                ),
                (
                    "validation_rules",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="قواعد تحقق مخصصة (JSON)",
                        verbose_name="قواعد التحقق",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="تاريخ الإنشاء"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث"),
                ),
            ],
            options={
                "verbose_name": "تخصيص خطوة الويزارد",
                "verbose_name_plural": "تخصيص خطوات الويزارد",
                "ordering": ["step_number"],
            },
        ),
        # إنشاء جدول الإعدادات العامة للويزارد
        migrations.CreateModel(
            name="WizardGlobalSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "enable_wizard",
                    models.BooleanField(
                        default=True,
                        help_text="تفعيل/تعطيل نظام الويزارد بالكامل",
                        verbose_name="تفعيل الويزارد",
                    ),
                ),
                (
                    "enable_draft_auto_save",
                    models.BooleanField(
                        default=True,
                        help_text="حفظ المسودة تلقائياً أثناء التنقل بين الخطوات",
                        verbose_name="الحفظ التلقائي للمسودات",
                    ),
                ),
                (
                    "draft_expiry_days",
                    models.IntegerField(
                        default=30,
                        help_text="المدة بالأيام قبل حذف المسودات غير المكتملة تلقائياً",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(365),
                        ],
                        verbose_name="مدة صلاحية المسودات (أيام)",
                    ),
                ),
                (
                    "minimum_payment_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default="50.00",
                        help_text="نسبة الحد الأدنى المطلوب دفعه من إجمالي الطلب",
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="الحد الأدنى للدفع (%)",
                    ),
                ),
                (
                    "allow_payment_exceed_total",
                    models.BooleanField(
                        default=True,
                        help_text="هل يمكن للعميل دفع مبلغ أكبر من إجمالي الطلب؟",
                        verbose_name="السماح بتجاوز المبلغ الإجمالي",
                    ),
                ),
                (
                    "require_contract_for_types",
                    models.JSONField(
                        default=list,
                        help_text="قائمة بأنواع الطلبات التي تتطلب عقد (مثل: installation, tailoring)",
                        verbose_name="أنواع الطلبات التي تتطلب عقد",
                    ),
                ),
                (
                    "enable_electronic_contract",
                    models.BooleanField(
                        default=True,
                        help_text="السماح بإنشاء عقود إلكترونية",
                        verbose_name="تفعيل العقد الإلكتروني",
                    ),
                ),
                (
                    "enable_pdf_contract_upload",
                    models.BooleanField(
                        default=True,
                        help_text="السماح برفع عقود PDF",
                        verbose_name="تفعيل رفع عقد PDF",
                    ),
                ),
                (
                    "require_inspection_for_types",
                    models.JSONField(
                        default=list,
                        help_text="قائمة بأنواع الطلبات التي تتطلب معاينة",
                        verbose_name="أنواع الطلبات التي تتطلب معاينة",
                    ),
                ),
                (
                    "allow_customer_side_measurements",
                    models.BooleanField(
                        default=True,
                        help_text="هل يمكن إنشاء طلب بمقاسات من طرف العميل؟",
                        verbose_name="السماح بمقاسات طرف العميل",
                    ),
                ),
                (
                    "send_notification_on_draft_created",
                    models.BooleanField(
                        default=False,
                        help_text="إرسال إشعار للمدير عند إنشاء مسودة جديدة",
                        verbose_name="إرسال إشعار عند إنشاء مسودة",
                    ),
                ),
                (
                    "send_notification_on_order_created",
                    models.BooleanField(
                        default=True,
                        help_text="إرسال إشعار للمدير عند إنشاء طلب نهائي",
                        verbose_name="إرسال إشعار عند إنشاء طلب",
                    ),
                ),
                (
                    "show_progress_bar",
                    models.BooleanField(
                        default=True,
                        help_text="إظهار شريط تقدم الخطوات في الويزارد",
                        verbose_name="إظهار شريط التقدم",
                    ),
                ),
                (
                    "theme_color",
                    models.CharField(
                        default="primary",
                        help_text="اللون الأساسي للويزارد (primary, success, info, etc.)",
                        max_length=50,
                        verbose_name="لون السمة",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="تاريخ الإنشاء"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث"),
                ),
            ],
            options={
                "verbose_name": "الإعدادات العامة للويزارد",
                "verbose_name_plural": "الإعدادات العامة للويزارد",
            },
        ),
        # إضافة قيد فريد لـ field_type و value
        migrations.AddConstraint(
            model_name="wizardfieldoption",
            constraint=models.UniqueConstraint(
                fields=["field_type", "value"], name="unique_field_type_value"
            ),
        ),
        # إضافة فهارس لتحسين الأداء
        migrations.AddIndex(
            model_name="wizardfieldoption",
            index=models.Index(
                fields=["field_type", "is_active"], name="wizard_field_type_active_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="wizardfieldoption",
            index=models.Index(
                fields=["field_type", "sequence"], name="wizard_field_type_seq_idx"
            ),
        ),
    ]
