"""
Factory Accounting Models
نماذج حسابات المصنع - إدارة مستحقات الخياطين والقصاصين
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class FactoryAccountingSettings(models.Model):
    """
    Singleton model for factory accounting settings
    إعدادات حسابات المصنع (نموذج واحد فقط)
    """

    # Excluded fabric types - which fabric types to EXCLUDE from meter calculations
    excluded_fabric_types = models.ManyToManyField(
        "orders.WizardFieldOption",
        verbose_name=_("أنواع الأقمشة المستبعدة"),
        blank=True,
        limit_choices_to={"field_type": "fabric_type", "is_active": True},
        help_text=_(
            "حدد أنواع الأقمشة التي يجب استبعادها من حساب إجمالي الأمتار (مثل: الأحزمة، الكشاكيش، إلخ)"
        ),
    )

    # Double meter tailoring types - which tailoring types trigger double meter calculation
    double_meter_tailoring_types = models.ManyToManyField(
        "orders.WizardFieldOption",
        verbose_name=_("أنواع التفصيل بأمتار مضاعفة"),
        blank=True,
        limit_choices_to={"field_type": "tailoring_type", "is_active": True},
        related_name="double_meter_settings",
        help_text=_(
            "حدد أنواع التفصيل التي يجب مضاعفة أمتارها في الحساب (مثل: كابتونيه، بليسيه)"
        ),
    )

    # Default pricing
    default_rate_per_meter = models.DecimalField(
        _("السعر الافتراضي للمتر (خياط)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("5.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("السعر الافتراضي المستخدم للخياطين الذين لا يملكون سعر مخصص"),
    )

    default_cutter_rate = models.DecimalField(
        _("السعر الافتراضي للمتر (قصاص)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("السعر الافتراضي لمتر القص"),
    )

    updated_at = models.DateTimeField(_("آخر تحديث"), auto_now=True)

    class Meta:
        verbose_name = _("إعدادات حسابات المصنع")
        verbose_name_plural = _("إعدادات حسابات المصنع")

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of settings"""
        pass

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def is_fabric_type_excluded(self, fabric_type_value):
        """Check if a fabric type should be excluded"""
        return self.excluded_fabric_types.filter(value=fabric_type_value).exists()

    def __str__(self):
        return str(_("إعدادات حسابات المصنع"))


class Tailor(models.Model):
    """
    الخياط/القصاص
    Stores information about tailors and cutters
    """

    ROLE_CHOICES = [
        ("tailor", "خياط"),
        ("cutter", "قصاص"),
    ]

    name = models.CharField(_("الاسم"), max_length=200, db_index=True)
    phone = models.CharField(_("رقم الهاتف"), max_length=20, blank=True)
    role = models.CharField(
        _("الدور"), max_length=20, choices=ROLE_CHOICES, default="tailor"
    )
    is_active = models.BooleanField(_("نشط"), default=True, db_index=True)

    use_custom_rate = models.BooleanField(
        _("استخدام سعر مخصص"),
        default=False,
        help_text=_(
            "إذا كان محدداً، سيتم استخدام السعر المخصص أدناه. وإلا سيتم استخدام السعر العام من الإعدادات"
        ),
    )

    default_rate = models.DecimalField(
        _("السعر المخصص للمتر"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("السعر المخصص لهذا الخياط (اتركه فارغاً لاستخدام السعر العام)"),
    )

    notes = models.TextField(_("ملاحظات"), blank=True)

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tailors",
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    class Meta:
        verbose_name = _("خياط/قصاص")
        verbose_name_plural = _("الخياطين والقصاصين")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="tailor_name_idx"),
            models.Index(fields=["is_active"], name="tailor_active_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    def get_rate(self):
        """Get the rate for this tailor (custom or global)"""
        if self.use_custom_rate and self.default_rate:
            return self.default_rate
        # Use global rate from settings
        settings = FactoryAccountingSettings.get_settings()
        return settings.default_rate_per_meter


class ProductionStatusLog(models.Model):
    """
    سجل حالات الإنتاج
    Logs status changes for manufacturing orders to track production dates
    """

    manufacturing_order = models.ForeignKey(
        "manufacturing.ManufacturingOrder",
        on_delete=models.CASCADE,
        related_name="production_status_logs",
        verbose_name=_("أمر التصنيع"),
    )
    status = models.CharField(_("الحالة"), max_length=30, db_index=True)
    timestamp = models.DateTimeField(
        _("التاريخ والوقت"), default=timezone.now, db_index=True
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes",
        verbose_name=_("تم التغيير بواسطة"),
    )

    notes = models.TextField(_("ملاحظات"), blank=True)

    class Meta:
        verbose_name = _("سجل حالة الإنتاج")
        verbose_name_plural = _("سجلات حالات الإنتاج")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["manufacturing_order", "status"],
                name="prodlog_order_status_idx",
            ),
            models.Index(fields=["timestamp"], name="prodlog_timestamp_idx"),
        ]

    def __str__(self):
        return f"{self.manufacturing_order.order.order_number} - {self.status} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class FactoryCard(models.Model):
    """
    بطاقة المصنع
    Factory card for tracking production costs and tailor assignments
    """

    STATUS_CHOICES = [
        ("new", "جديد"),
        ("reviewing", "قيد المراجعة"),
        ("completed", "مكتمل"),
        ("paid", "مدفوع"),
    ]

    manufacturing_order = models.OneToOneField(
        "manufacturing.ManufacturingOrder",
        on_delete=models.CASCADE,
        related_name="factory_card",
        verbose_name=_("أمر التصنيع"),
    )

    status = models.CharField(
        _("الحالة"), max_length=20, choices=STATUS_CHOICES, default="new", db_index=True
    )

    total_billable_meters = models.DecimalField(
        _("إجمالي الأمتار المستحقة"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Cutter accounting
    cutter_price = models.DecimalField(
        _("سعر متر القصاص"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("سعر المتر للقصاص في هذا الأمر"),
    )

    total_cutter_cost = models.DecimalField(
        _("إجمالي تكلفة القصاص"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("إجمالي الأمتار الفعلية × سعر القصاص"),
    )

    total_double_meters = models.DecimalField(
        _("إجمالي الأمتار (مضاعف)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("مجموع الأمتار بعد تطبيق المضاعفة لأنواع التفصيل المحددة"),
    )

    production_date = models.DateTimeField(
        _("تاريخ الإنتاج"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("التاريخ الذي أصبح فيه الأمر جاهزاً أو مكتملاً"),
    )

    payment_date = models.DateTimeField(
        _("تاريخ الدفع"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("تاريخ سداد المستحقات"),
    )

    notes = models.TextField(_("ملاحظات"), blank=True)

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_factory_cards",
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    class Meta:
        verbose_name = _("بطاقة المصنع")
        verbose_name_plural = _("بطاقات المصنع")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="factcard_status_idx"),
            models.Index(fields=["production_date"], name="factcard_proddate_idx"),
            models.Index(fields=["-created_at"], name="factcard_created_idx"),
        ]

    def __str__(self):
        return f"بطاقة {self.manufacturing_order.order.order_number}"

    @property
    def order_number(self):
        """رقم الطلب"""
        return self.manufacturing_order.order.order_number

    @property
    def customer_name(self):
        """اسم العميل"""
        return self.manufacturing_order.order.customer.name

    @property
    def invoice_number(self):
        """رقم الفاتورة"""
        return self.manufacturing_order.order.invoice_number or "-"

    @property
    def total_cost(self):
        """إجمالي التكلفة من جميع التقسيمات"""
        from django.db.models import Sum

        total = self.splits.aggregate(total=Sum("monetary_value"))["total"]
        return total or Decimal("0.00")

    @property
    def cutter_name(self):
        """اسم القصاص من خط الإنتاج"""
        try:
            if (
                hasattr(self.manufacturing_order, "production_line")
                and self.manufacturing_order.production_line
            ):
                return self.manufacturing_order.production_line.name or "-"
        except:
            pass
        return "-"

    def update_production_date(self):
        """
        Update production date from status log
        تحديث تاريخ الإنتاج من سجل الحالات
        """
        log = (
            ProductionStatusLog.objects.filter(
                manufacturing_order=self.manufacturing_order,
                status__in=["ready_install", "completed"],
            )
            .order_by("timestamp")
            .first()
        )

        if log:
            self.production_date = log.timestamp
            self.save(update_fields=["production_date", "updated_at"])

    def calculate_total_meters(self):
        """
        Calculate total billable meters from contract materials
        حساب إجمالي الأمتار من مواد العقد
        """
        try:
            from orders.contract_models import ContractCurtain

            # Get all curtains for this order
            curtains = ContractCurtain.objects.filter(
                order=self.manufacturing_order.order
            ).prefetch_related("fabrics")

            # Get exclusion settings from admin
            settings = FactoryAccountingSettings.get_settings()
            excluded_fabric_type_values = set(
                settings.excluded_fabric_types.values_list("value", flat=True)
            )

            # Get double meter settings - Comprehensive List
            double_meter_tailoring_values = list(
                settings.double_meter_tailoring_types.values_list("value", flat=True)
            ) + list(
                settings.double_meter_tailoring_types.values_list(
                    "display_name", flat=True
                )
            )

            # Always exclude belts and accessories (hardcoded)
            ALWAYS_EXCLUDED = {"belt", "accessory", "additional"}
            excluded_fabric_type_values.update(ALWAYS_EXCLUDED)

            total_actual = Decimal("0.00")
            total_double_calc = Decimal("0.00")

            # Sum up meters from all fabrics
            for curtain in curtains:
                for fabric in curtain.fabrics.all():
                    # Skip if fabric type is in excluded list
                    if fabric.fabric_type in excluded_fabric_type_values:
                        continue

                    meters = Decimal("0.00")
                    if fabric.meters:
                        meters = Decimal(str(fabric.meters))
                        total_actual += meters

                    # Check if this specific fabric needs double metering based on ITS tailoring type
                    is_double = False

                    t_type_val = fabric.tailoring_type
                    t_type_display = fabric.get_tailoring_type_display()

                    if (t_type_val and t_type_val in double_meter_tailoring_values) or (
                        t_type_display
                        and t_type_display in double_meter_tailoring_values
                    ):
                        is_double = True

                    if is_double:
                        total_double_calc += meters * 2
                    else:
                        total_double_calc += meters

            self.total_billable_meters = total_actual
            self.total_double_meters = total_double_calc

            # Calculate cutter cost
            # 1. Try to get rate from production line
            cutter_rate = None
            if (
                hasattr(self.manufacturing_order, "production_line")
                and self.manufacturing_order.production_line
            ):
                # Assuming production_line has a cutter_rate field, otherwise use default
                # Since we don't know if ProductionLine has specific rates, we might need to check
                pass

            # 2. If no specific rate, use default from settings supply
            if not cutter_rate:
                cutter_rate = settings.default_cutter_rate

            self.cutter_price = cutter_rate
            self.total_cutter_cost = total_actual * cutter_rate

            self.save(
                update_fields=[
                    "total_billable_meters",
                    "total_double_meters",
                    "cutter_price",
                    "total_cutter_cost",
                    "updated_at",
                ]
            )
            return total_actual

        except Exception as e:
            print(f"Error calculating total meters: {e}")
            # Log error for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating total meters for {self.order_number}: {e}")
            return self.total_billable_meters

    def get_production_user_info(self):
        """
        Get user who changed status to production (ready/completed)
        الحصول على المستخدم الذي غيّر الحالة للإنتاج
        """
        log = (
            ProductionStatusLog.objects.filter(
                manufacturing_order=self.manufacturing_order,
                status__in=["ready_install", "completed"],
            )
            .order_by("timestamp")
            .first()
        )

        if log:
            return {
                "user": (
                    log.changed_by.get_full_name() if log.changed_by else "غير محدد"
                ),
                "timestamp": log.timestamp,
                "status": (
                    log.get_status_display()
                    if hasattr(log, "get_status_display")
                    else log.status
                ),
            }
        return None

    def get_current_cutter_price(self):
        """
        Get current cutter price based on payment status
        إذا مدفوع: استخدم السعر المخزن
        إذا غير مدفوع: استخدم السعر الحالي من الإعدادات
        """
        if self.status == "paid":
            # Preserve original price for paid items
            return self.cutter_price

        # Use current settings for unpaid items
        settings = FactoryAccountingSettings.get_settings()
        return settings.default_cutter_rate

    def get_current_cutter_cost(self):
        """
        Calculate current cutter cost based on payment status
        التكلفة الحالية للقصاص حسب حالة الدفع
        """
        if self.status == "paid":
            # Preserve original cost for paid items
            return self.total_cutter_cost

        # Recalculate using current price for unpaid items
        current_price = self.get_current_cutter_price()
        return self.total_billable_meters * current_price


class CardMeasurementSplit(models.Model):
    """
    تقسيم القياسات
    Split of billable meters among tailors
    """

    factory_card = models.ForeignKey(
        FactoryCard,
        on_delete=models.CASCADE,
        related_name="splits",
        verbose_name=_("بطاقة المصنع"),
    )

    tailor = models.ForeignKey(
        Tailor,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name=_("الخياط/القصاص"),
        db_index=True,
    )

    share_amount = models.DecimalField(
        _("الكمية المخصصة (متر)"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("عدد الأمتار المخصصة للخياط"),
    )

    unit_rate = models.DecimalField(
        _("السعر للمتر"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("يتم جلبه تلقائياً من إعدادات الخياط"),
    )

    monetary_value = models.DecimalField(
        _("القيمة المالية"), max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    is_paid = models.BooleanField(_("مدفوع"), default=False, db_index=True)
    paid_date = models.DateTimeField(_("تاريخ الدفع"), null=True, blank=True)

    notes = models.TextField(_("ملاحظات"), blank=True)

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("تقسيم القياسات")
        verbose_name_plural = _("تقسيمات القياسات")
        ordering = ["factory_card", "tailor"]
        indexes = [
            models.Index(
                fields=["factory_card", "tailor"], name="split_card_tailor_idx"
            ),
            models.Index(fields=["is_paid"], name="split_paid_idx"),
        ]

    def __str__(self):
        return f"{self.tailor.name} - {self.share_amount}م @ {self.factory_card.order_number}"

    def get_current_unit_rate(self):
        """
        Get current unit rate based on payment status
        إذا مدفوع: استخدم السعر المخزن
        إذا غير مدفوع: استخدم السعر الحالي
        """
        if self.is_paid:
            # Preserve original price for paid items
            return self.unit_rate

        # Use current tailor rate for unpaid items
        return self.tailor.get_rate()

    def get_current_monetary_value(self):
        """
        Calculate current monetary value based on payment status
        القيمة المالية الحالية حسب حالة الدفع
        """
        if self.is_paid:
            # Preserve original value for paid items
            return self.monetary_value

        # Recalculate using current rate for unpaid items
        current_rate = self.get_current_unit_rate()
        return self.share_amount * current_rate

    def save(self, *args, **kwargs):
        """Calculate monetary value: meters × rate"""
        # Use tailor's rate (custom or global)
        if not self.unit_rate or self.unit_rate == 0:
            self.unit_rate = self.tailor.get_rate()

        # Calculate: meters × rate
        self.monetary_value = self.share_amount * self.unit_rate
        super().save(*args, **kwargs)
