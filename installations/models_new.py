from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from decimal import Decimal
import json
from datetime import datetime, timedelta

# استيراد النماذج المطلوبة
try:
    from inspections.models import Inspection
except ImportError:
    Inspection = None

try:
    from orders.models import Order
except ImportError:
    Order = None

try:
    from accounts.models import User, Branch
except ImportError:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    Branch = None


class InstallationTeamNew(models.Model):
    """فريق التركيب المحسن"""
    name = models.CharField(_('اسم الفريق'), max_length=100)
    leader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='led_teams_new',
        verbose_name=_('قائد الفريق')
    )
    members = models.ManyToManyField(
        User,
        related_name='installation_teams_new',
        verbose_name=_('أعضاء الفريق')
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='installation_teams_new',
        verbose_name=_('الفرع')
    )
    is_active = models.BooleanField(_('نشط'), default=True)
    max_daily_installations = models.PositiveIntegerField(_('الحد الأقصى للتركيبات اليومية'), default=5)
    specializations = models.JSONField(_('التخصصات'), default=list, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('فريق تركيب محسن')
        verbose_name_plural = _('فرق التركيب المحسنة')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.branch.name}"

    @property
    def members_count(self):
        """عدد أعضاء الفريق"""
        return self.members.count()

    def get_daily_installations_count(self, date=None):
        """عدد التركيبات المجدولة في يوم معين"""
        if not date:
            date = timezone.now().date()
        return self.installations_new.filter(scheduled_date=date).count()

    def can_schedule_installation(self, date=None):
        """التحقق من إمكانية جدولة تركيب جديد"""
        if not date:
            date = timezone.now().date()
        return self.get_daily_installations_count(date) < self.max_daily_installations


class InstallationNew(models.Model):
    """عملية التركيب المحسنة"""
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('in_production', _('قيد الإنتاج')),
        ('ready', _('جاهز للتركيب')),
        ('scheduled', _('مجدول')),
        ('in_progress', _('جاري التنفيذ')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
        ('on_hold', _('معلق')),
        ('rescheduled', _('تم إعادة الجدولة')),
    ]
    
    QUALITY_CHOICES = [
        (1, _('ضعيف')),
        (2, _('مقبول')),
        (3, _('جيد')),
        (4, _('جيد جداً')),
        (5, _('ممتاز')),
    ]
    
    LOCATION_TYPE_CHOICES = [
        ('open', _('مكان مفتوح')),
        ('compound', _('كومبوند')),
        ('apartment', _('شقة')),
        ('villa', _('فيلا')),
        ('office', _('مكتب')),
        ('shop', _('محل تجاري')),
        ('warehouse', _('مستودع')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('منخفضة')),
        ('normal', _('عادية')),
        ('high', _('عالية')),
        ('urgent', _('عاجل')),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', _('لم يتم السداد')),
        ('partial', _('سداد جزئي')),
        ('paid', _('تم السداد')),
        ('overdue', _('متأخر السداد')),
    ]

    # العلاقات الأساسية
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='installations_new',
        verbose_name=_('الطلب'),
        null=True,
        blank=True
    )
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installations_new',
        verbose_name=_('المعاينة')
    )
    team = models.ForeignKey(
        InstallationTeamNew,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installations_new',
        verbose_name=_('فريق التركيب')
    )
    
    # معلومات العميل (مكررة للوصول السريع)
    customer_name = models.CharField(_('اسم العميل'), max_length=200, db_index=True)
    customer_phone = models.CharField(_('رقم هاتف العميل'), max_length=20, db_index=True)
    customer_phone2 = models.CharField(_('رقم الهاتف الثاني'), max_length=20, blank=True, null=True)
    customer_address = models.TextField(_('عنوان العميل'))
    
    # معلومات البائع والفرع (مكررة للوصول السريع)
    salesperson_name = models.CharField(_('اسم البائع'), max_length=200, blank=True)
    branch_name = models.CharField(_('اسم الفرع'), max_length=200, db_index=True)
    
    # تفاصيل التركيب
    windows_count = models.PositiveIntegerField(_('عدد الشبابيك'), default=0)
    location_type = models.CharField(_('نوع المكان'), max_length=20, choices=LOCATION_TYPE_CHOICES, default='open')
    floor_number = models.PositiveIntegerField(_('رقم الطابق'), null=True, blank=True)
    
    # التواريخ والجدولة
    order_date = models.DateTimeField(_('تاريخ الطلب'))
    scheduled_date = models.DateField(_('تاريخ التركيب المجدول'), null=True, blank=True, db_index=True)
    scheduled_time_start = models.TimeField(_('وقت البدء المجدول'), null=True, blank=True)
    scheduled_time_end = models.TimeField(_('وقت الانتهاء المجدول'), null=True, blank=True)
    actual_start_date = models.DateTimeField(_('تاريخ بدء التركيب الفعلي'), null=True, blank=True)
    actual_end_date = models.DateTimeField(_('تاريخ انتهاء التركيب الفعلي'), null=True, blank=True)
    
    # الحالة والأولوية
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    priority = models.CharField(_('الأولوية'), max_length=10, choices=PRIORITY_CHOICES, default='normal')
    is_ready_for_installation = models.BooleanField(_('جاهز للتركيب من المصنع'), default=False, db_index=True)
    payment_status = models.CharField(_('حالة السداد'), max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # التقييم والجودة
    quality_rating = models.IntegerField(_('تقييم الجودة'), choices=QUALITY_CHOICES, null=True, blank=True)
    customer_satisfaction = models.IntegerField(_('رضا العميل'), choices=QUALITY_CHOICES, null=True, blank=True)
    
    # الملاحظات والتفاصيل
    notes = models.TextField(_('ملاحظات'), blank=True)
    special_instructions = models.TextField(_('تعليمات خاصة'), blank=True)
    access_instructions = models.TextField(_('تعليمات الوصول'), blank=True)
    
    # معلومات النظام
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_installations_new',
        verbose_name=_('تم الإنشاء بواسطة')
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_installations_new',
        verbose_name=_('تم التحديث بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    # تواريخ الإنتاج
    production_started_at = models.DateTimeField(_('تاريخ بدء الإنتاج'), null=True, blank=True)
    production_completed_at = models.DateTimeField(_('تاريخ اكتمال الإنتاج'), null=True, blank=True)

    class Meta:
        verbose_name = _('عملية تركيب محسنة')
        verbose_name_plural = _('عمليات التركيب المحسنة')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_date'], name='inst_new_status_date_idx'),
            models.Index(fields=['customer_name'], name='inst_new_customer_idx'),
            models.Index(fields=['branch_name', 'status'], name='inst_new_branch_status_idx'),
            models.Index(fields=['is_ready_for_installation'], name='inst_new_ready_idx'),
            models.Index(fields=['payment_status'], name='inst_new_payment_idx'),
            models.Index(fields=['team', 'scheduled_date'], name='inst_new_team_date_idx'),
        ]

    def __str__(self):
        if self.order:
            return f"تركيب {self.customer_name} - طلب #{self.order.order_number}"
        else:
            return f"تركيب {self.customer_name} - #{self.id}"

    def clean(self):
        """التحقق من صحة البيانات"""
        if self.actual_end_date and self.actual_start_date:
            if self.actual_end_date < self.actual_start_date:
                raise ValidationError(_('تاريخ انتهاء التركيب لا يمكن أن يكون قبل تاريخ البدء'))
        
        if self.scheduled_time_end and self.scheduled_time_start:
            if self.scheduled_time_end <= self.scheduled_time_start:
                raise ValidationError(_('وقت الانتهاء يجب أن يكون بعد وقت البدء'))

    def save(self, *args, **kwargs):
        # تحديث معلومات العميل والطلب من الطلب المرتبط
        if self.order:
            self.customer_name = self.order.customer.name
            self.customer_phone = self.order.customer.phone
            self.customer_phone2 = getattr(self.order.customer, 'phone2', '')
            self.customer_address = self.order.customer.address
            self.order_date = self.order.order_date
            if self.order.salesperson:
                self.salesperson_name = str(self.order.salesperson)
            if self.order.branch:
                self.branch_name = self.order.branch.name
            
            # تحديث حالة السداد
            if self.order.payment_verified:
                self.payment_status = 'paid'
            elif self.order.paid_amount > 0:
                self.payment_status = 'partial'
            else:
                self.payment_status = 'pending'
        
        # تحديث تواريخ البدء والانتهاء عند تغيير الحالة
        if self.status == 'in_progress' and not self.actual_start_date:
            self.actual_start_date = timezone.now()
        elif self.status == 'completed' and not self.actual_end_date:
            self.actual_end_date = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def duration_hours(self):
        """مدة التركيب بالساعات"""
        if self.actual_start_date and self.actual_end_date:
            duration = self.actual_end_date - self.actual_start_date
            return duration.total_seconds() / 3600
        return None

    @property
    def is_overdue(self):
        """التحقق من تأخر التركيب"""
        if self.scheduled_date and self.status not in ['completed', 'cancelled']:
            return self.scheduled_date < timezone.now().date()
        return False

    @property
    def technicians_list(self):
        """قائمة أسماء الفنيين"""
        if self.team:
            return [member.get_full_name() or member.username for member in self.team.members.all()]
        return []

    @property
    def technicians_names(self):
        """أسماء الفنيين كنص"""
        return ', '.join(self.technicians_list)


class InstallationSchedule(models.Model):
    """جدولة التركيبات الذكية"""
    installation = models.OneToOneField(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='schedule',
        verbose_name=_('التركيب')
    )
    date = models.DateField(_('التاريخ'), db_index=True)
    time_slot_start = models.TimeField(_('بداية الفترة الزمنية'))
    time_slot_end = models.TimeField(_('نهاية الفترة الزمنية'))
    estimated_duration = models.DurationField(_('المدة المقدرة'), null=True, blank=True)
    buffer_time = models.DurationField(_('وقت إضافي'), null=True, blank=True)
    is_confirmed = models.BooleanField(_('مؤكد'), default=False)
    auto_scheduled = models.BooleanField(_('جدولة تلقائية'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('جدولة تركيب')
        verbose_name_plural = _('جدولة التركيبات')
        ordering = ['date', 'time_slot_start']
        unique_together = ['installation', 'date']

    def __str__(self):
        return f"جدولة {self.installation.customer_name} - {self.date}"


class InstallationTechnician(models.Model):
    """فنيو التركيب"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='technician_profile',
        verbose_name=_('المستخدم')
    )
    employee_id = models.CharField(_('رقم الموظف'), max_length=20, unique=True)
    specializations = models.JSONField(_('التخصصات'), default=list)
    experience_years = models.PositiveIntegerField(_('سنوات الخبرة'), default=0)
    max_windows_per_day = models.PositiveIntegerField(_('الحد الأقصى للشبابيك يومياً'), default=20)
    hourly_rate = models.DecimalField(_('الأجر بالساعة'), max_digits=8, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='technicians',
        verbose_name=_('الفرع')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('فني تركيب')
        verbose_name_plural = _('فنيو التركيب')
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"

    def get_daily_windows_count(self, date=None):
        """عدد الشبابيك المجدولة في يوم معين"""
        if not date:
            date = timezone.now().date()

        installations = InstallationNew.objects.filter(
            team__members=self.user,
            scheduled_date=date,
            status__in=['scheduled', 'in_progress']
        )
        return sum(installation.windows_count for installation in installations)

    def can_handle_windows(self, windows_count, date=None):
        """التحقق من إمكانية التعامل مع عدد شبابيك إضافي"""
        current_count = self.get_daily_windows_count(date)
        return (current_count + windows_count) <= self.max_windows_per_day


class InstallationAlert(models.Model):
    """تنبيهات التركيب"""
    ALERT_TYPES = [
        ('overdue', _('تأخير')),
        ('capacity_exceeded', _('تجاوز السعة')),
        ('quality_issue', _('مشكلة جودة')),
        ('customer_complaint', _('شكوى عميل')),
        ('schedule_conflict', _('تعارض في الجدولة')),
        ('payment_overdue', _('تأخر في السداد')),
    ]

    SEVERITY_CHOICES = [
        ('low', _('منخفض')),
        ('medium', _('متوسط')),
        ('high', _('عالي')),
        ('critical', _('حرج')),
    ]

    installation = models.ForeignKey(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name=_('التركيب')
    )
    alert_type = models.CharField(_('نوع التنبيه'), max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(_('الخطورة'), max_length=10, choices=SEVERITY_CHOICES, default='medium')
    title = models.CharField(_('العنوان'), max_length=200)
    message = models.TextField(_('الرسالة'))
    is_resolved = models.BooleanField(_('تم الحل'), default=False)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name=_('تم الحل بواسطة')
    )
    resolved_at = models.DateTimeField(_('تاريخ الحل'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('تنبيه تركيب')
        verbose_name_plural = _('تنبيهات التركيب')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'is_resolved'], name='alert_type_resolved_idx'),
            models.Index(fields=['severity', 'created_at'], name='alert_severity_date_idx'),
        ]

    def __str__(self):
        return f"{self.title} - {self.installation.customer_name}"


class DailyInstallationReport(models.Model):
    """تقرير التركيبات اليومي"""
    date = models.DateField(_('التاريخ'), unique=True, db_index=True)
    total_scheduled = models.PositiveIntegerField(_('إجمالي المجدول'), default=0)
    total_completed = models.PositiveIntegerField(_('إجمالي المكتمل'), default=0)
    total_cancelled = models.PositiveIntegerField(_('إجمالي الملغي'), default=0)
    total_windows = models.PositiveIntegerField(_('إجمالي الشبابيك'), default=0)
    average_quality_rating = models.FloatField(_('متوسط تقييم الجودة'), null=True, blank=True)
    average_customer_satisfaction = models.FloatField(_('متوسط رضا العملاء'), null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    generated_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('تقرير يومي للتركيبات')
        verbose_name_plural = _('التقارير اليومية للتركيبات')
        ordering = ['-date']

    def __str__(self):
        return f"تقرير {self.date}"

    @classmethod
    def generate_report(cls, date=None):
        """إنشاء تقرير يومي"""
        if not date:
            date = timezone.now().date()

        installations = InstallationNew.objects.filter(scheduled_date=date)

        report, created = cls.objects.get_or_create(
            date=date,
            defaults={
                'total_scheduled': installations.filter(status='scheduled').count(),
                'total_completed': installations.filter(status='completed').count(),
                'total_cancelled': installations.filter(status='cancelled').count(),
                'total_windows': sum(inst.windows_count for inst in installations),
            }
        )

        # حساب متوسط التقييمات
        completed_installations = installations.filter(status='completed')
        if completed_installations.exists():
            quality_ratings = [inst.quality_rating for inst in completed_installations if inst.quality_rating]
            satisfaction_ratings = [inst.customer_satisfaction for inst in completed_installations if inst.customer_satisfaction]

            if quality_ratings:
                report.average_quality_rating = sum(quality_ratings) / len(quality_ratings)
            if satisfaction_ratings:
                report.average_customer_satisfaction = sum(satisfaction_ratings) / len(satisfaction_ratings)

        report.save()
        return report


class InstallationCompletionLog(models.Model):
    """سجل إكمال التركيب"""
    installation = models.OneToOneField(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='completion_log',
        verbose_name=_('التركيب')
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='completed_installations_log',
        verbose_name=_('تم الإكمال بواسطة')
    )
    completion_date = models.DateTimeField(_('تاريخ الإكمال'))
    quality_rating = models.IntegerField(_('تقييم الجودة'), null=True, blank=True)
    customer_satisfaction = models.IntegerField(_('رضا العميل'), null=True, blank=True)
    completion_notes = models.TextField(_('ملاحظات الإكمال'), blank=True)
    duration_hours = models.FloatField(_('مدة التركيب بالساعات'), null=True, blank=True)
    issues_encountered = models.TextField(_('المشاكل المواجهة'), blank=True)
    customer_feedback = models.TextField(_('تعليقات العميل'), blank=True)
    photos_taken = models.BooleanField(_('تم التصوير'), default=False)
    warranty_explained = models.BooleanField(_('تم شرح الضمان'), default=False)
    cleanup_completed = models.BooleanField(_('تم التنظيف'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل إكمال تركيب')
        verbose_name_plural = _('سجلات إكمال التركيبات')
        ordering = ['-completion_date']

    def __str__(self):
        return f"إكمال {self.installation.customer_name} - {self.completion_date.strftime('%Y-%m-%d')}"


class InstallationMaterial(models.Model):
    """مواد التركيب"""
    installation = models.ForeignKey(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name=_('التركيب')
    )
    material_name = models.CharField(_('اسم المادة'), max_length=200)
    material_code = models.CharField(_('كود المادة'), max_length=50, blank=True)
    quantity_required = models.PositiveIntegerField(_('الكمية المطلوبة'))
    quantity_used = models.PositiveIntegerField(_('الكمية المستخدمة'), default=0)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(_('التكلفة الإجمالية'), max_digits=10, decimal_places=2, default=0)
    supplier = models.CharField(_('المورد'), max_length=200, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مادة تركيب')
        verbose_name_plural = _('مواد التركيب')
        ordering = ['material_name']

    def __str__(self):
        return f"{self.material_name} - {self.installation}"

    def save(self, *args, **kwargs):
        # حساب التكلفة الإجمالية
        self.total_cost = self.quantity_used * self.unit_price
        super().save(*args, **kwargs)


class InstallationPhoto(models.Model):
    """صور التركيب"""
    installation = models.ForeignKey(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name=_('التركيب')
    )
    photo = models.ImageField(_('الصورة'), upload_to='installations/photos/')
    description = models.CharField(_('وصف الصورة'), max_length=200, blank=True)
    photo_type = models.CharField(
        _('نوع الصورة'),
        max_length=20,
        choices=[
            ('before', 'قبل التركيب'),
            ('during', 'أثناء التركيب'),
            ('after', 'بعد التركيب'),
            ('problem', 'مشكلة'),
            ('solution', 'حل'),
        ],
        default='during'
    )
    taken_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('تم التقاط بواسطة')
    )
    taken_at = models.DateTimeField(_('تاريخ التقاط'), auto_now_add=True)

    class Meta:
        verbose_name = _('صورة تركيب')
        verbose_name_plural = _('صور التركيب')
        ordering = ['-taken_at']

    def __str__(self):
        return f"صورة {self.get_photo_type_display()} - {self.installation}"


class InstallationNote(models.Model):
    """ملاحظات التركيب"""
    installation = models.ForeignKey(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='installation_notes',
        verbose_name=_('التركيب')
    )
    note_type = models.CharField(
        _('نوع الملاحظة'),
        max_length=20,
        choices=[
            ('general', 'عامة'),
            ('technical', 'فنية'),
            ('customer', 'خاصة بالعميل'),
            ('quality', 'جودة'),
            ('safety', 'سلامة'),
            ('delay', 'تأخير'),
        ],
        default='general'
    )
    title = models.CharField(_('العنوان'), max_length=200)
    content = models.TextField(_('المحتوى'))
    priority = models.CharField(
        _('الأولوية'),
        max_length=10,
        choices=[
            ('low', 'منخفضة'),
            ('normal', 'عادية'),
            ('high', 'عالية'),
            ('urgent', 'عاجلة'),
        ],
        default='normal'
    )
    is_resolved = models.BooleanField(_('تم الحل'), default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='installation_notes',
        verbose_name=_('أنشئ بواسطة')
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_installation_notes',
        verbose_name=_('تم الحل بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    resolved_at = models.DateTimeField(_('تاريخ الحل'), null=True, blank=True)

    class Meta:
        verbose_name = _('ملاحظة تركيب')
        verbose_name_plural = _('ملاحظات التركيب')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.installation}"

    def resolve(self, user):
        """حل الملاحظة"""
        self.is_resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()


class InstallationQualityCheck(models.Model):
    """فحص جودة التركيب"""
    installation = models.OneToOneField(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='quality_check',
        verbose_name=_('التركيب')
    )
    checked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('فحص بواسطة')
    )

    # معايير الجودة
    alignment_score = models.IntegerField(
        _('درجة المحاذاة'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    finish_score = models.IntegerField(
        _('درجة التشطيب'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    functionality_score = models.IntegerField(
        _('درجة الوظائف'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    cleanliness_score = models.IntegerField(
        _('درجة النظافة'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    safety_score = models.IntegerField(
        _('درجة السلامة'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )

    overall_rating = models.DecimalField(
        _('التقييم الإجمالي'),
        max_digits=3,
        decimal_places=2,
        default=5.0
    )

    # ملاحظات الجودة
    positive_notes = models.TextField(_('ملاحظات إيجابية'), blank=True)
    improvement_notes = models.TextField(_('ملاحظات للتحسين'), blank=True)
    defects_found = models.TextField(_('عيوب تم اكتشافها'), blank=True)

    # حالة الفحص
    is_approved = models.BooleanField(_('معتمد'), default=False)
    requires_rework = models.BooleanField(_('يتطلب إعادة عمل'), default=False)

    checked_at = models.DateTimeField(_('تاريخ الفحص'), auto_now_add=True)
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)

    class Meta:
        verbose_name = _('فحص جودة تركيب')
        verbose_name_plural = _('فحوصات جودة التركيب')

    def __str__(self):
        return f"فحص جودة - {self.installation} - {self.overall_rating}"

    def save(self, *args, **kwargs):
        # حساب التقييم الإجمالي
        scores = [
            self.alignment_score,
            self.finish_score,
            self.functionality_score,
            self.cleanliness_score,
            self.safety_score
        ]
        self.overall_rating = sum(scores) / len(scores)

        # تحديد حالة الاعتماد
        if self.overall_rating >= 4.0 and not self.requires_rework:
            self.is_approved = True
            if not self.approved_at:
                self.approved_at = timezone.now()
        else:
            self.is_approved = False
            self.approved_at = None

        super().save(*args, **kwargs)


class InstallationCustomerFeedback(models.Model):
    """تقييم العميل للتركيب"""
    installation = models.OneToOneField(
        InstallationNew,
        on_delete=models.CASCADE,
        related_name='customer_feedback',
        verbose_name=_('التركيب')
    )

    # تقييمات العميل
    overall_satisfaction = models.IntegerField(
        _('الرضا العام'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    quality_rating = models.IntegerField(
        _('تقييم الجودة'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    timeliness_rating = models.IntegerField(
        _('تقييم الالتزام بالوقت'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    professionalism_rating = models.IntegerField(
        _('تقييم الاحترافية'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )
    cleanliness_rating = models.IntegerField(
        _('تقييم النظافة'),
        choices=[(i, i) for i in range(1, 6)],
        default=5
    )

    # تعليقات العميل
    positive_feedback = models.TextField(_('التعليقات الإيجابية'), blank=True)
    negative_feedback = models.TextField(_('التعليقات السلبية'), blank=True)
    suggestions = models.TextField(_('اقتراحات للتحسين'), blank=True)

    # معلومات إضافية
    would_recommend = models.BooleanField(_('يوصي بالخدمة'), default=True)
    would_use_again = models.BooleanField(_('سيستخدم الخدمة مرة أخرى'), default=True)

    feedback_date = models.DateTimeField(_('تاريخ التقييم'), auto_now_add=True)
    feedback_method = models.CharField(
        _('طريقة التقييم'),
        max_length=20,
        choices=[
            ('phone', 'هاتف'),
            ('email', 'بريد إلكتروني'),
            ('sms', 'رسالة نصية'),
            ('in_person', 'شخصياً'),
            ('online', 'عبر الإنترنت'),
        ],
        default='phone'
    )

    class Meta:
        verbose_name = _('تقييم عميل للتركيب')
        verbose_name_plural = _('تقييمات العملاء للتركيبات')

    def __str__(self):
        return f"تقييم {self.installation.customer_name} - {self.overall_satisfaction}/5"

    @property
    def average_rating(self):
        """متوسط التقييمات"""
        ratings = [
            self.overall_satisfaction,
            self.quality_rating,
            self.timeliness_rating,
            self.professionalism_rating,
            self.cleanliness_rating
        ]
        return sum(ratings) / len(ratings)
