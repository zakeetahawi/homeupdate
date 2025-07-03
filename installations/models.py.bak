from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from inspections.models import Inspection
from orders.models import Order
from accounts.models import User, Branch
class InstallationTeam(models.Model):
    """فريق التركيب"""
    name = models.CharField(_('اسم الفريق'), max_length=100)
    leader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='led_teams',
        verbose_name=_('قائد الفريق')
    )
    members = models.ManyToManyField(
        User,
        related_name='installation_teams',
        verbose_name=_('أعضاء الفريق')
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='installation_teams',
        verbose_name=_('الفرع')
    )
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    class Meta:
        verbose_name = _('فريق تركيب')
        verbose_name_plural = _('فرق التركيب')
        ordering = ['name']
    def __str__(self):
        return f"{self.name} - {self.branch.name}"
class Installation(models.Model):
    """عملية التركيب"""
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('scheduled', _('مجدول')),
        ('in_progress', _('جاري التنفيذ')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]
    QUALITY_CHOICES = [
        (1, _('ضعيف')),
        (2, _('مقبول')),
        (3, _('جيد')),
        (4, _('جيد جداً')),
        (5, _('ممتاز')),
    ]
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='installations',
        verbose_name=_('الطلب')
    )
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.SET_NULL,
        null=True,
        related_name='installations',
        verbose_name=_('المعاينة')
    )
    team = models.ForeignKey(
        InstallationTeam,
        on_delete=models.PROTECT,
        related_name='installations',
        verbose_name=_('فريق التركيب'),
        null=True,
        blank=True
    )
    scheduled_date = models.DateField(_('تاريخ التركيب المجدول'), null=True, blank=True)
    actual_start_date = models.DateTimeField(_('تاريخ بدء التركيب الفعلي'), null=True, blank=True)
    actual_end_date = models.DateTimeField(_('تاريخ انتهاء التركيب الفعلي'), null=True, blank=True)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    quality_rating = models.IntegerField(_('تقييم الجودة'), choices=QUALITY_CHOICES, null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_installations',
        verbose_name=_('تم الإنشاء بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    class Meta:
        verbose_name = _('عملية تركيب')
        verbose_name_plural = _('عمليات التركيب')
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['order'], name='install_order_idx'),
            models.Index(fields=['inspection'], name='install_inspection_idx'),
            models.Index(fields=['team'], name='install_team_idx'),
            models.Index(fields=['status'], name='install_status_idx'),
            models.Index(fields=['scheduled_date'], name='install_sched_date_idx'),
            models.Index(fields=['created_at'], name='install_created_idx'),
        ]
    def __str__(self):
        return f"تركيب طلب #{self.order.order_number}"
    def clean(self):
        if self.actual_end_date and self.actual_start_date:
            if self.actual_end_date < self.actual_start_date:
                raise ValidationError(_('تاريخ انتهاء التركيب لا يمكن أن يكون قبل تاريخ البدء'))
    def save(self, *args, **kwargs):
        # تحديث تواريخ البدء والانتهاء عند تغيير الحالة
        if self.status == 'in_progress' and not self.actual_start_date:
            self.actual_start_date = timezone.now()
        elif self.status == 'completed' and not self.actual_end_date:
            self.actual_end_date = timezone.now()
        super().save(*args, **kwargs)
class InstallationStep(models.Model):
    """خطوات التركيب"""
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name=_('عملية التركيب')
    )
    name = models.CharField(_('اسم الخطوة'), max_length=200)
    description = models.TextField(_('وصف الخطوة'), blank=True)
    order = models.PositiveIntegerField(_('الترتيب'))
    is_completed = models.BooleanField(_('مكتملة'), default=False)
    completed_at = models.DateTimeField(_('تاريخ الإكمال'), null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='completed_steps',
        verbose_name=_('تم الإكمال بواسطة')
    )
    notes = models.TextField(_('ملاحظات'), blank=True)
    photo = models.ImageField(_('صورة'), upload_to='installations/steps/', null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    class Meta:
        verbose_name = _('خطوة تركيب')
        verbose_name_plural = _('خطوات التركيب')
        ordering = ['installation', 'order']
        unique_together = ['installation', 'order']
    def __str__(self):
        return f"{self.name} - {self.installation}"
    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.is_completed:
            self.completed_at = None
            self.completed_by = None
        super().save(*args, **kwargs)
class InstallationQualityCheckOld(models.Model):
    """فحص جودة التركيب"""
    CRITERIA_CHOICES = [
        ('alignment', _('المحاذاة')),
        ('finishing', _('التشطيب')),
        ('functionality', _('الوظائف')),
        ('safety', _('السلامة')),
        ('cleanliness', _('النظافة')),
    ]
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name='quality_checks',
        verbose_name=_('عملية التركيب')
    )
    criteria = models.CharField(_('معيار التقييم'), max_length=20, choices=CRITERIA_CHOICES)
    rating = models.IntegerField(_('التقييم'), choices=Installation.QUALITY_CHOICES)
    notes = models.TextField(_('ملاحظات'), blank=True)
    photo = models.ImageField(_('صورة'), upload_to='installations/quality/', null=True, blank=True)
    checked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='quality_checks',
        verbose_name=_('تم الفحص بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الفحص'), auto_now_add=True)
    class Meta:
        verbose_name = _('فحص جودة')
        verbose_name_plural = _('فحوصات الجودة')
        ordering = ['-created_at']
        unique_together = ['installation', 'criteria']
    def __str__(self):
        return f"{self.get_criteria_display()} - {self.installation}"
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # تحديث متوسط تقييم الجودة للتركيب
        installation = self.installation
        avg_rating = installation.quality_checks.aggregate(models.Avg('rating'))['rating__avg']
        if avg_rating:
            installation.quality_rating = round(avg_rating)
            installation.save()
class InstallationIssue(models.Model):
    """مشاكل التركيب"""
    PRIORITY_CHOICES = [
        ('low', _('منخفضة')),
        ('medium', _('متوسطة')),
        ('high', _('عالية')),
        ('critical', _('حرجة')),
    ]
    STATUS_CHOICES = [
        ('open', _('مفتوحة')),
        ('in_progress', _('جاري المعالجة')),
        ('resolved', _('تم الحل')),
        ('closed', _('مغلقة')),
    ]
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name='issues',
        verbose_name=_('عملية التركيب')
    )
    title = models.CharField(_('عنوان المشكلة'), max_length=200)
    description = models.TextField(_('وصف المشكلة'))
    priority = models.CharField(_('الأولوية'), max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='open')
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_installation_issues',
        verbose_name=_('تم الإبلاغ بواسطة')
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_installation_issues',
        verbose_name=_('تم التكليف إلى')
    )
    resolution = models.TextField(_('الحل'), blank=True)
    resolved_at = models.DateTimeField(_('تاريخ الحل'), null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_installation_issues',
        verbose_name=_('تم الحل بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    class Meta:
        verbose_name = _('مشكلة تركيب')
        verbose_name_plural = _('مشاكل التركيب')
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.title} - {self.installation}"
    def save(self, *args, **kwargs):
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status != 'resolved':
            self.resolved_at = None
            self.resolved_by = None
        super().save(*args, **kwargs)
class InstallationNotification(models.Model):
    """إشعارات التركيب"""
    TYPE_CHOICES = [
        ('scheduled', _('موعد تركيب')),
        ('status_change', _('تغيير الحالة')),
        ('quality_check', _('فحص الجودة')),
        ('issue', _('مشكلة')),
    ]
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('عملية التركيب')
    )
    type = models.CharField(_('نوع الإشعار'), max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(_('عنوان الإشعار'), max_length=200)
    message = models.TextField(_('نص الإشعار'))
    is_read = models.BooleanField(_('تمت القراءة'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    class Meta:
        verbose_name = _('إشعار تركيب')
        verbose_name_plural = _('إشعارات التركيب')
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.title} - {self.installation}"
