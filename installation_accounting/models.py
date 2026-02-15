"""
Installation Accounting Models
نماذج حسابات التركيبات - إدارة مستحقات الفنيين
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class InstallationAccountingSettings(models.Model):
    """
    Singleton model for installation accounting settings
    إعدادات حسابات التركيبات (نموذج واحد فقط)
    """

    default_price_per_window = models.DecimalField(
        _("سعر الشباك الافتراضي"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("35.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("السعر الافتراضي لتركيب الشباك الواحد"),
    )

    updated_at = models.DateTimeField(_("آخر تحديث"), auto_now=True)

    class Meta:
        verbose_name = _("إعدادات حسابات التركيبات")
        verbose_name_plural = _("إعدادات حسابات التركيبات")

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

    def __str__(self):
        return str(_("إعدادات حسابات التركيبات"))


class InstallationCard(models.Model):
    """
    بطاقة التركيب
    Installation card for tracking installation costs and technician assignments
    """

    STATUS_CHOICES = [
        ("new", _("جديد")),
        ("pending", _("معلق")),
        ("completed", _("مكتمل")),
        ("paid", _("مدفوع")),
    ]

    installation_schedule = models.OneToOneField(
        "installations.InstallationSchedule",
        on_delete=models.PROTECT,
        related_name="accounting_card",
        verbose_name=_("جدولة التركيب"),
    )

    status = models.CharField(
        _("الحالة"), max_length=20, choices=STATUS_CHOICES, default="new", db_index=True
    )

    windows_count = models.PositiveIntegerField(
        _("عدد الشبابيك"),
        default=0,
        help_text=_("عدد الشبابيك التي تم تركيبها (يتم جلبها من الجدولة)"),
    )

    price_per_window = models.DecimalField(
        _("سعر الشباك"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("سعر التركيب للشباك الواحد لهذا الطلب"),
    )

    total_cost = models.DecimalField(
        _("إجمالي التكلفة"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("عدد الشبابيك × سعر الشباك"),
    )

    completion_date = models.DateTimeField(
        _("تاريخ الإكمال"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("تاريخ إكمال التركيب"),
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

    class Meta:
        verbose_name = _("بطاقة محاسبة التركيب")
        verbose_name_plural = _("بطاقات محاسبة التركيبات")
        ordering = ["-completion_date", "-created_at"]
        indexes = [
            models.Index(fields=["status"], name="instcard_status_idx"),
            models.Index(fields=["completion_date"], name="instcard_date_idx"),
        ]

    def __str__(self):
        return f"محاسبة تركيب {self.installation_schedule.order.order_number}"

    @property
    def order_number(self):
        return self.installation_schedule.order.order_number

    @property
    def is_modification(self):
        """التحقق مما إذا كان التركيب هو تعديل"""
        return self.installation_schedule.status.startswith("modification")

    @property
    def customer_name(self):
        return self.installation_schedule.order.customer.name

    def calculate_total(self):
        """Calculate total cost"""
        # If price is 0, use default
        if self.price_per_window == 0:
            settings = InstallationAccountingSettings.get_settings()
            self.price_per_window = settings.default_price_per_window

        self.total_cost = self.windows_count * self.price_per_window
        self.save(update_fields=["price_per_window", "total_cost"])
        return self.total_cost


class TechnicianShare(models.Model):
    """
    حصة الفني
    Share of windows/cost for a specific technician
    """

    card = models.ForeignKey(
        InstallationCard,
        on_delete=models.CASCADE,
        related_name="shares",
        verbose_name=_("بطاقة التركيب"),
    )

    technician = models.ForeignKey(
        "installations.Technician",
        on_delete=models.PROTECT,
        related_name="installation_shares",
        verbose_name=_("الفني"),
        db_index=True,
    )

    assigned_windows = models.DecimalField(
        _("عدد الشبابيك المخصصة"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("حصة الفني من عدد الشبابيك"),
    )

    amount = models.DecimalField(
        _("المبلغ المستحق"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("حصة الفني من المبلغ الإجمالي"),
    )

    is_paid = models.BooleanField(_("مدفوع"), default=False, db_index=True)
    paid_date = models.DateTimeField(_("تاريخ الدفع"), null=True, blank=True)

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("حصة فني")
        verbose_name_plural = _("حصص الفنيين")
        ordering = ["card", "technician"]
        indexes = [
            models.Index(fields=["is_paid"], name="tech_share_paid_idx"),
            models.Index(
                fields=["technician", "is_paid"], name="tech_share_status_idx"
            ),
        ]

    def __str__(self):
        return f"{self.technician.name} - {self.amount} ({self.card.order_number})"
