import logging
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# ─── Decimal Field Constants ──────────────────────────────────────────
# Use these when defining DecimalFields for consistency across the codebase.
CURRENCY_MAX_DIGITS = 15
CURRENCY_DECIMAL_PLACES = 2
QUANTITY_MAX_DIGITS = 12
QUANTITY_DECIMAL_PLACES = 3
PERCENTAGE_MAX_DIGITS = 5
PERCENTAGE_DECIMAL_PLACES = 2


# ─── Abstract Base Models ────────────────────────────────────────────


class TimeStampedModel(models.Model):
    """
    نموذج أساسي مجرد يوفر حقول تاريخ الإنشاء والتعديل تلقائياً.

    Abstract base model providing:
    - created_at: Auto-set on creation
    - updated_at: Auto-set on every save

    Usage:
        class MyModel(TimeStampedModel):
            name = models.CharField(max_length=100)
    """

    created_at = models.DateTimeField(
        _("تاريخ الإنشاء"),
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        _("تاريخ التعديل"),
        auto_now=True,
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class AuditableModel(TimeStampedModel):
    """
    نموذج أساسي مجرد يوفر حقول تتبع المستخدم بالإضافة لحقول التاريخ.

    Abstract base model extending TimeStampedModel with user-tracking:
    - created_by: The user who created the record
    - updated_by: The user who last modified the record

    Usage:
        class MyModel(AuditableModel):
            name = models.CharField(max_length=100)
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name=_("أنشأ بواسطة"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        verbose_name=_("عُدّل بواسطة"),
    )

    class Meta(TimeStampedModel.Meta):
        abstract = True


class SoftDeleteModel(models.Model):
    """
    نموذج أساسي مجرد يوفر حذف ناعم بدلاً من الحذف الدائم.

    Abstract base model providing soft-delete support:
    - is_deleted: Flag to mark as deleted
    - deleted_at: When it was deleted
    - deleted_by: Who deleted it

    Usage:
        class MyModel(SoftDeleteModel, TimeStampedModel):
            name = models.CharField(max_length=100)

        # Query active records:
        MyModel.objects.filter(is_deleted=False)
    """

    is_deleted = models.BooleanField(
        _("محذوف"),
        default=False,
        db_index=True,
    )
    deleted_at = models.DateTimeField(
        _("تاريخ الحذف"),
        null=True,
        blank=True,
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_deleted",
        verbose_name=_("حُذف بواسطة"),
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """Mark this record as deleted instead of removing from DB."""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])


class RecycleBin(models.Model):
    """
    Unmanaged model for Global Recycle Bin Dashboard.
    This model doesn't have a database table - it's used only for Admin UI.
    """
    
    class Meta:
        managed = False
        verbose_name = _("سلة المحذوفات")
        verbose_name_plural = _("سلة المحذوفات")
        app_label = 'core'
