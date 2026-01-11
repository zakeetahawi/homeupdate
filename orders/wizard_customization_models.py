"""
نماذج تخصيص الويزارد
Models for Wizard Customization System
"""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class WizardFieldOption(models.Model):
    """
    خيارات الحقول الثابتة في الويزارد
    Options for fixed fields in wizard (like tailoring types, installation types, etc.)
    """

    FIELD_TYPE_CHOICES = [
        ("tailoring_type", "طريقة التفصيل"),
        ("installation_type", "نوع التركيب"),
        ("payment_method", "طريقة الدفع"),
        ("order_status", "حالة الطلب"),
        ("service_type", "نوع الخدمة"),
    ]

    field_type = models.CharField(
        max_length=50,
        choices=FIELD_TYPE_CHOICES,
        verbose_name="نوع الحقل",
        help_text="نوع الحقل الذي ينتمي إليه هذا الخيار",
    )

    value = models.CharField(
        max_length=100,
        verbose_name="القيمة (بالإنجليزية)",
        help_text="القيمة المخزنة في قاعدة البيانات",
    )

    display_name = models.CharField(
        max_length=200,
        verbose_name="ما يظهر بالحقل",
        help_text="النص الذي سيظهر للمستخدم",
    )

    sequence = models.IntegerField(
        default=0, verbose_name="الترتيب", help_text="ترتيب العرض"
    )

    is_active = models.BooleanField(default=True, verbose_name="نشط")

    is_default = models.BooleanField(default=False, verbose_name="افتراضي")

    # معلومات إضافية كـ JSON (للخصائص الخاصة)
    extra_data = models.JSONField(
        default=dict, blank=True, verbose_name="بيانات إضافية"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "خيار حقل"
        verbose_name_plural = "خيارات الحقول"
        ordering = ["field_type", "sequence", "display_name"]
        unique_together = [["field_type", "value"]]

    def __str__(self):
        return f"{self.get_field_type_display()} - {self.display_name}"

    def clean(self):
        """التحقق من صحة البيانات"""
        super().clean()

        # التحقق من عدم وجود قيمة مكررة لنفس نوع الحقل
        existing = WizardFieldOption.objects.filter(
            field_type=self.field_type, value=self.value
        ).exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError({"value": f'القيمة "{self.value}" موجودة بالفعل'})

    def save(self, *args, **kwargs):
        # التحقق من البيانات قبل الحفظ
        self.full_clean()

        # تحويل القيمة إلى أحرف صغيرة
        self.value = self.value.lower().strip()
        self.display_name = self.display_name.strip()

        super().save(*args, **kwargs)

    @classmethod
    def get_active_options(cls, field_type):
        """الحصول على الخيارات النشطة لنوع حقل معين"""
        return cls.objects.filter(field_type=field_type, is_active=True).order_by(
            "sequence", "display_name"
        )

    @classmethod
    def get_choices_for_field(cls, field_type):
        """الحصول على الخيارات كقائمة choices"""
        options = cls.get_active_options(field_type)
        return [(opt.value, opt.display_name) for opt in options]

    @classmethod
    def get_default_for_field(cls, field_type):
        """الحصول على الخيار الافتراضي"""
        try:
            return cls.objects.get(
                field_type=field_type, is_active=True, is_default=True
            )
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(
                field_type=field_type, is_active=True, is_default=True
            ).first()


class WizardStepConfiguration(models.Model):
    """
    تخصيص خطوات الويزارد
    Configuration for wizard steps
    """

    STEP_CHOICES = [
        (1, "الخطوة 1 - البيانات الأساسية"),
        (2, "الخطوة 2 - نوع الطلب"),
        (3, "الخطوة 3 - عناصر الطلب"),
        (4, "الخطوة 4 - تفاصيل المرجع والدفع"),
        (5, "الخطوة 5 - العقد"),
        (6, "الخطوة 6 - المراجعة والتأكيد"),
    ]

    step_number = models.IntegerField(
        unique=True, choices=STEP_CHOICES, verbose_name="رقم الخطوة"
    )

    step_title_ar = models.CharField(max_length=200, verbose_name="عنوان الخطوة (عربي)")

    step_title_en = models.CharField(
        max_length=200, blank=True, verbose_name="عنوان الخطوة (إنجليزي)"
    )

    step_description = models.TextField(
        blank=True, verbose_name="وصف الخطوة", help_text="وصف تفصيلي يظهر للمستخدم"
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="الأيقونة",
        help_text="أيقونة الخطوة (Font Awesome)",
    )

    is_required = models.BooleanField(
        default=True, verbose_name="إجبارية", help_text="هل إكمال هذه الخطوة إجباري؟"
    )

    is_active = models.BooleanField(
        default=True, verbose_name="نشطة", help_text="هل هذه الخطوة متاحة؟"
    )

    help_text = models.TextField(
        blank=True,
        verbose_name="نص المساعدة",
        help_text="نص مساعدة يظهر للمستخدم في هذه الخطوة",
    )

    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="قواعد التحقق",
        help_text="قواعد تحقق مخصصة (JSON)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "تخصيص خطوة الويزارد"
        verbose_name_plural = "تخصيص خطوات الويزارد"
        ordering = ["step_number"]

    def __str__(self):
        return f"خطوة {self.step_number} - {self.step_title_ar}"


class WizardGlobalSettings(models.Model):
    """
    الإعدادات العامة للويزارد
    Global settings for the wizard system
    """

    # إعدادات عامة
    enable_wizard = models.BooleanField(
        default=True,
        verbose_name="تفعيل الويزارد",
        help_text="تفعيل/تعطيل نظام الويزارد بالكامل",
    )

    enable_draft_auto_save = models.BooleanField(
        default=True,
        verbose_name="الحفظ التلقائي للمسودات",
        help_text="حفظ المسودة تلقائياً أثناء التنقل بين الخطوات",
    )

    draft_expiry_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        verbose_name="مدة صلاحية المسودات (أيام)",
        help_text="المدة بالأيام قبل حذف المسودات غير المكتملة تلقائياً",
    )

    # إعدادات الحد الأدنى للدفع
    minimum_payment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="الحد الأدنى للدفع (%)",
        help_text="نسبة الحد الأدنى المطلوب دفعه من إجمالي الطلب",
    )

    allow_payment_exceed_total = models.BooleanField(
        default=True,
        verbose_name="السماح بتجاوز المبلغ الإجمالي",
        help_text="هل يمكن للعميل دفع مبلغ أكبر من إجمالي الطلب؟",
    )

    # إعدادات العقد
    require_contract_for_installation = models.BooleanField(
        default=True,
        verbose_name="تطلب عقد للتركيب",
        help_text="هل يتطلب طلب التركيب عقداً؟",
    )

    require_contract_for_tailoring = models.BooleanField(
        default=True,
        verbose_name="تطلب عقد للتفصيل",
        help_text="هل يتطلب طلب التفصيل عقداً؟",
    )

    require_contract_for_accessory = models.BooleanField(
        default=True,
        verbose_name="تطلب عقد للإكسسوار",
        help_text="هل يتطلب طلب الإكسسوار عقداً؟",
    )

    require_contract_for_inspection = models.BooleanField(
        default=False,
        verbose_name="تطلب عقد للمعاينة",
        help_text="هل يتطلب طلب المعاينة عقداً؟",
    )

    require_contract_for_products = models.BooleanField(
        default=False,
        verbose_name="تطلب عقد للمنتجات",
        help_text="هل يتطلب طلب المنتجات عقداً؟",
    )

    enable_electronic_contract = models.BooleanField(
        default=True,
        verbose_name="تفعيل العقد الإلكتروني",
        help_text="السماح بإنشاء عقود إلكترونية",
    )

    enable_pdf_contract_upload = models.BooleanField(
        default=True, verbose_name="تفعيل رفع عقد PDF", help_text="السماح برفع عقود PDF"
    )

    # إعدادات المعاينة
    require_inspection_for_installation = models.BooleanField(
        default=True,
        verbose_name="تطلب معاينة للتركيب",
        help_text="هل يتطلب طلب التركيب معاينة؟",
    )

    require_inspection_for_tailoring = models.BooleanField(
        default=True,
        verbose_name="تطلب معاينة للتفصيل",
        help_text="هل يتطلب طلب التفصيل معاينة؟",
    )

    require_inspection_for_accessory = models.BooleanField(
        default=True,
        verbose_name="تطلب معاينة للإكسسوار",
        help_text="هل يتطلب طلب الإكسسوار معاينة؟",
    )

    require_inspection_for_inspection = models.BooleanField(
        default=True,
        verbose_name="تطلب معاينة مسبقة للمعاينة",
        help_text="هل يتطلب طلب المعاينة معاينة مسبقة؟",
    )

    require_inspection_for_products = models.BooleanField(
        default=False,
        verbose_name="تطلب معاينة للمنتجات",
        help_text="هل يتطلب طلب المنتجات معاينة؟",
    )

    allow_customer_side_measurements = models.BooleanField(
        default=True,
        verbose_name="السماح بمقاسات طرف العميل",
        help_text="هل يمكن إنشاء طلب بمقاسات من طرف العميل؟",
    )

    # إعدادات الإشعارات
    send_notification_on_draft_created = models.BooleanField(
        default=False,
        verbose_name="إرسال إشعار عند إنشاء مسودة",
        help_text="إرسال إشعار للمدير عند إنشاء مسودة جديدة",
    )

    send_notification_on_order_created = models.BooleanField(
        default=True,
        verbose_name="إرسال إشعار عند إنشاء طلب",
        help_text="إرسال إشعار للمدير عند إنشاء طلب نهائي",
    )

    # إعدادات العرض
    show_progress_bar = models.BooleanField(
        default=True,
        verbose_name="إظهار شريط التقدم",
        help_text="إظهار شريط تقدم الخطوات في الويزارد",
    )

    theme_color = models.CharField(
        max_length=50,
        default="primary",
        verbose_name="لون السمة",
        help_text="اللون الأساسي للويزارد (primary, success, info, etc.)",
    )

    # معلومات التحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "الإعدادات العامة للويزارد"
        verbose_name_plural = "الإعدادات العامة للويزارد"

    def __str__(self):
        return "إعدادات الويزارد"

    def save(self, *args, **kwargs):
        # التأكد من وجود سجل واحد فقط
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات الويزارد (إنشاء إذا لم تكن موجودة)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def requires_contract(self, order_type):
        """التحقق من أن نوع الطلب يتطلب عقد"""
        mapping = {
            "installation": self.require_contract_for_installation,
            "tailoring": self.require_contract_for_tailoring,
            "accessory": self.require_contract_for_accessory,
            "inspection": self.require_contract_for_inspection,
            "products": self.require_contract_for_products,
        }
        return mapping.get(order_type, False)

    def requires_inspection(self, order_type):
        """التحقق من أن نوع الطلب يتطلب معاينة"""
        mapping = {
            "installation": self.require_inspection_for_installation,
            "tailoring": self.require_inspection_for_tailoring,
            "accessory": self.require_inspection_for_accessory,
            "inspection": self.require_inspection_for_inspection,
            "products": self.require_inspection_for_products,
        }
        return mapping.get(order_type, False)

    def clean(self):
        """التحقق من صحة البيانات"""
        super().clean()

        # التحقق من نسبة الحد الأدنى للدفع
        if self.minimum_payment_percentage < 0 or self.minimum_payment_percentage > 100:
            raise ValidationError(
                {"minimum_payment_percentage": "النسبة يجب أن تكون بين 0 و 100"}
            )

        # التحقق من مدة صلاحية المسودات
        if self.draft_expiry_days < 1:
            raise ValidationError(
                {"draft_expiry_days": "المدة يجب أن تكون على الأقل يوم واحد"}
            )
