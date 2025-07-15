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


def modification_images_path(instance, filename):
    """مسار حفظ صور التعديل"""
    return f'installations/modifications/{instance.installation.id}/images/{filename}'


class CustomerDebt(models.Model):
    """نموذج مديونية العملاء"""
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, verbose_name=_('العميل'))
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, verbose_name=_('الطلب'))
    debt_amount = models.DecimalField(_('مبلغ المديونية'), max_digits=10, decimal_places=2)
    notes = models.TextField(_('ملاحظات'), blank=True)
    is_paid = models.BooleanField(_('تم الدفع'), default=False)
    payment_receipt_number = models.CharField(_('رقم إذن استلام المبلغ'), max_length=100, blank=True)
    payment_receiver_name = models.CharField(_('اسم المستلم'), max_length=100, blank=True)
    payment_date = models.DateTimeField(_('تاريخ الدفع'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مديونية عميل')
        verbose_name_plural = _('مديونيات العملاء')
        ordering = ['-created_at']

    def __str__(self):
        return f"مديونية {self.customer.name} - {self.order.order_number}"

    def save(self, *args, **kwargs):
        if self.is_paid and not self.payment_date:
            self.payment_date = timezone.now()
        super().save(*args, **kwargs)


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
        ('modification_required', _('يحتاج تعديل')),
        ('modification_in_progress', _('التعديل قيد التنفيذ')),
        ('modification_completed', _('التعديل مكتمل')),
    ]

    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, verbose_name=_('الطلب'))
    team = models.ForeignKey(InstallationTeam, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('الفريق'))
    scheduled_date = models.DateField(_('تاريخ التركيب'))
    scheduled_time = models.TimeField(_('موعد التركيب'))
    status = models.CharField(_('الحالة'), max_length=30, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(_('ملاحظات'), blank=True)
    completion_date = models.DateTimeField(_('تاريخ الإكمال'), null=True, blank=True)
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

    def save(self, *args, **kwargs):
        # تحديث حالة الطلب عند إكمال التركيب
        if self.status == 'completed' and not self.completion_date:
            self.completion_date = timezone.now()
            # تحديث حالة الطلب إلى مكتمل
            self.order.order_status = 'completed'
            self.order.save()
        super().save(*args, **kwargs)


class ModificationRequest(models.Model):
    """نموذج طلب التعديل"""
    PRIORITY_CHOICES = [
        ('low', _('منخفض')),
        ('medium', _('متوسط')),
        ('high', _('عالي')),
        ('urgent', _('عاجل')),
    ]

    installation = models.ForeignKey(InstallationSchedule, on_delete=models.CASCADE, verbose_name=_('التركيب'))
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, verbose_name=_('العميل'))
    modification_type = models.CharField(_('نوع التعديل'), max_length=100)
    description = models.TextField(_('تفاصيل التعديل'))
    priority = models.CharField(_('الأولوية'), max_length=20, choices=PRIORITY_CHOICES, default='medium')
    estimated_cost = models.DecimalField(_('التكلفة المتوقعة'), max_digits=10, decimal_places=2, default=0)
    customer_approval = models.BooleanField(_('موافقة العميل'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('طلب تعديل')
        verbose_name_plural = _('طلبات التعديل')
        ordering = ['-created_at']

    def __str__(self):
        return f"طلب تعديل - {self.installation.order.order_number}"


class ModificationImage(models.Model):
    """نموذج صور التعديل"""
    modification = models.ForeignKey(ModificationRequest, on_delete=models.CASCADE, verbose_name=_('طلب التعديل'))
    image = models.ImageField(_('صورة'), upload_to=modification_images_path)
    description = models.CharField(_('وصف الصورة'), max_length=200, blank=True)
    uploaded_at = models.DateTimeField(_('تاريخ الرفع'), auto_now_add=True)

    class Meta:
        verbose_name = _('صورة تعديل')
        verbose_name_plural = _('صور التعديل')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"صورة تعديل - {self.modification.installation.order.order_number}"


class ManufacturingOrder(models.Model):
    """نموذج أمر التصنيع للتعديلات"""
    ORDER_TYPE_CHOICES = [
        ('new', _('جديد')),
        ('modification', _('تعديل')),
        ('repair', _('إصلاح')),
    ]

    STATUS_CHOICES = [
        ('pending', _('في الانتظار')),
        ('approved', _('موافق عليه')),
        ('in_progress', _('قيد التنفيذ')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]

    modification_request = models.ForeignKey(ModificationRequest, on_delete=models.CASCADE, verbose_name=_('طلب التعديل'))
    order_type = models.CharField(_('نوع الأمر'), max_length=20, choices=ORDER_TYPE_CHOICES, default='modification')
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(_('تفاصيل الأمر'))
    estimated_completion_date = models.DateField(_('تاريخ الإكمال المتوقع'), null=True, blank=True)
    actual_completion_date = models.DateTimeField(_('تاريخ الإكمال الفعلي'), null=True, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('مُسند إلى'), related_name='installation_manufacturing_orders')
    manager_notes = models.TextField(_('ملاحظات المدير'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('أمر تصنيع')
        verbose_name_plural = _('أوامر التصنيع')
        ordering = ['-created_at']

    def __str__(self):
        return f"أمر تصنيع - {self.modification_request.installation.order.order_number}"


class ModificationReport(models.Model):
    """نموذج تقارير التعديل"""
    modification_request = models.ForeignKey(ModificationRequest, on_delete=models.CASCADE, verbose_name=_('طلب التعديل'))
    manufacturing_order = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE, verbose_name=_('أمر التصنيع'), null=True, blank=True)
    report_file = models.FileField(_('ملف التقرير'), upload_to=modification_report_path, blank=True)
    description = models.TextField(_('وصف التعديل المنجز'))
    completion_notes = models.TextField(_('ملاحظات الإكمال'), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('تقرير تعديل')
        verbose_name_plural = _('تقارير التعديل')
        ordering = ['-created_at']

    def __str__(self):
        return f"تقرير تعديل - {self.modification_request.installation.order.order_number}"


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


class InstallationAnalytics(models.Model):
    """نموذج تحليل التركيبات الشهري"""
    month = models.DateField(_('الشهر'), help_text='أول يوم من الشهر')
    total_installations = models.IntegerField(_('إجمالي التركيبات'), default=0)
    completed_installations = models.IntegerField(_('التركيبات المكتملة'), default=0)
    pending_installations = models.IntegerField(_('التركيبات في الانتظار'), default=0)
    in_progress_installations = models.IntegerField(_('التركيبات قيد التنفيذ'), default=0)
    total_customers = models.IntegerField(_('إجمالي العملاء'), default=0)
    new_customers = models.IntegerField(_('العملاء الجدد'), default=0)
    total_visits = models.IntegerField(_('إجمالي الزيارات'), default=0)
    total_modifications = models.IntegerField(_('إجمالي التعديلات'), default=0)
    modification_rate = models.DecimalField(_('نسبة التعديلات %'), max_digits=5, decimal_places=2, default=0)
    completion_rate = models.DecimalField(_('نسبة الإكمال %'), max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('تحليل تركيب شهري')
        verbose_name_plural = _('تحليلات التركيبات الشهرية')
        ordering = ['-month']
        unique_together = ['month']

    def __str__(self):
        return f"تحليل {self.month.strftime('%Y-%m')}"

    def calculate_rates(self):
        """حساب النسب المئوية"""
        if self.total_installations > 0:
            self.completion_rate = (self.completed_installations / self.total_installations) * 100
            self.modification_rate = (self.total_modifications / self.total_installations) * 100
        self.save()


class ModificationErrorType(models.Model):
    """نموذج أنواع أسباب التعديلات"""
    name = models.CharField(_('اسم السبب'), max_length=100)
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('نوع سبب تعديل')
        verbose_name_plural = _('أنواع أسباب التعديلات')
        ordering = ['name']

    def __str__(self):
        return self.name


class ModificationErrorAnalysis(models.Model):
    """نموذج تحليل أخطاء التعديلات"""
    modification_request = models.ForeignKey(ModificationRequest, on_delete=models.CASCADE, verbose_name=_('طلب التعديل'))
    error_type = models.ForeignKey(ModificationErrorType, on_delete=models.CASCADE, verbose_name=_('نوع السبب'))
    error_description = models.TextField(_('وصف الخطأ'))
    root_cause = models.TextField(_('السبب الجذري'))
    solution_applied = models.TextField(_('الحل المطبق'))
    prevention_measures = models.TextField(_('إجراءات الوقاية'), blank=True)
    cost_impact = models.DecimalField(_('التأثير المالي'), max_digits=10, decimal_places=2, default=0)
    time_impact_hours = models.IntegerField(_('التأثير الزمني (ساعات)'), default=0)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('تحليل خطأ تعديل')
        verbose_name_plural = _('تحليلات أخطاء التعديلات')
        ordering = ['-created_at']

    def __str__(self):
        return f"تحليل خطأ - {self.modification_request.installation.order.order_number}"
