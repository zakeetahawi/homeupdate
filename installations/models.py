from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
import os


def installation_receipt_path(instance, filename):
    """مسار حفظ مذكرة استلام التركيب"""
    return f'installations/receipts/{instance.installation.id}/{filename}'


def modification_report_path(instance, filename):
    """مسار حفظ تقارير التعديل"""
    return f'installations/modifications/{instance.installation.id}/{filename}'


class Technician(models.Model):
    """نموذج الفنيين"""
    name = models.CharField(_('اسم الفني'), max_length=100)
    phone = models.CharField(_('رقم الهاتف'), max_length=20)
    specialization = models.CharField(_('التخصص'), max_length=100, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('فني')
        verbose_name_plural = _('الفنيين')
        ordering = ['name']

    def __str__(self):
        return self.name


class Driver(models.Model):
    """نموذج السائقين"""
    name = models.CharField(_('اسم السائق'), max_length=100)
    phone = models.CharField(_('رقم الهاتف'), max_length=20)
    license_number = models.CharField(_('رقم الرخصة'), max_length=50, blank=True)
    vehicle_number = models.CharField(_('رقم المركبة'), max_length=50, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('سائق')
        verbose_name_plural = _('السائقين')
        ordering = ['name']

    def __str__(self):
        return self.name


class InstallationTeam(models.Model):
    """نموذج فرق التركيب"""
    name = models.CharField(_('اسم الفريق'), max_length=100)
    technicians = models.ManyToManyField(Technician, verbose_name=_('الفنيين'))
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('السائق'))
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('فريق تركيب')
        verbose_name_plural = _('فرق التركيب')
        ordering = ['name']

    def __str__(self):
        return self.name


class InstallationSchedule(models.Model):
    """نموذج جدولة التركيب"""
    STATUS_CHOICES = [
        ('pending', _('في الانتظار')),
        ('scheduled', _('مجدول')),
        ('in_progress', _('قيد التنفيذ')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
        ('rescheduled', _('إعادة جدولة')),
    ]

    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, verbose_name=_('الطلب'))
    team = models.ForeignKey(InstallationTeam, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('الفريق'))
    scheduled_date = models.DateField(_('تاريخ التركيب'))
    scheduled_time = models.TimeField(_('موعد التركيب'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('جدولة تركيب')
        verbose_name_plural = _('جدولة التركيبات')
        ordering = ['-scheduled_date', '-scheduled_time']

    def __str__(self):
        return f"تركيب الطلب {self.order.order_number} - {self.get_status_display()}"

    def clean(self):
        """التحقق من صحة البيانات"""
        if self.scheduled_date and self.scheduled_date < timezone.now().date():
            raise ValidationError(_('لا يمكن جدولة تركيب في تاريخ ماضي'))


class ModificationReport(models.Model):
    """نموذج تقارير التعديل"""
    installation = models.ForeignKey(InstallationSchedule, on_delete=models.CASCADE, verbose_name=_('التركيب'))
    report_file = models.FileField(_('ملف التقرير'), upload_to=modification_report_path)
    description = models.TextField(_('وصف التعديل'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('تقرير تعديل')
        verbose_name_plural = _('تقارير التعديل')
        ordering = ['-created_at']

    def __str__(self):
        return f"تقرير تعديل - {self.installation.order.order_number}"


class ReceiptMemo(models.Model):
    """نموذج مذكرة الاستلام"""
    installation = models.OneToOneField(InstallationSchedule, on_delete=models.CASCADE, verbose_name=_('التركيب'))
    receipt_image = models.ImageField(_('صورة مذكرة الاستلام'), upload_to=installation_receipt_path)
    customer_signature = models.BooleanField(_('توقيع العميل'), default=False)
    amount_received = models.DecimalField(_('المبلغ المستلم'), max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('مذكرة استلام')
        verbose_name_plural = _('مذكرات الاستلام')

    def __str__(self):
        return f"مذكرة استلام - {self.installation.order.order_number}"


class InstallationPayment(models.Model):
    """نموذج مدفوعات التركيب"""
    PAYMENT_TYPE_CHOICES = [
        ('remaining', _('المتبقي')),
        ('additional', _('إضافي')),
        ('refund', _('استرداد')),
    ]

    installation = models.ForeignKey(InstallationSchedule, on_delete=models.CASCADE, verbose_name=_('التركيب'))
    payment_type = models.CharField(_('نوع الدفع'), max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(_('المبلغ'), max_digits=10, decimal_places=2)
    payment_method = models.CharField(_('طريقة الدفع'), max_length=50, blank=True)
    receipt_number = models.CharField(_('رقم الإيصال'), max_length=50, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('دفعة تركيب')
        verbose_name_plural = _('مدفوعات التركيب')
        ordering = ['-created_at']

    def __str__(self):
        return f"دفعة {self.get_payment_type_display()} - {self.installation.order.order_number}"


class InstallationArchive(models.Model):
    """نموذج أرشيف التركيبات المكتملة"""
    installation = models.OneToOneField(InstallationSchedule, on_delete=models.CASCADE, verbose_name=_('التركيب'))
    completion_date = models.DateTimeField(_('تاريخ الإكمال'), auto_now_add=True)
    archived_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_('تم الأرشفة بواسطة'))
    archive_notes = models.TextField(_('ملاحظات الأرشفة'), blank=True)

    class Meta:
        verbose_name = _('أرشيف تركيب')
        verbose_name_plural = _('أرشيف التركيبات')
        ordering = ['-completion_date']

    def __str__(self):
        return f"أرشيف - {self.installation.order.order_number}"
