from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from datetime import timedelta

User = get_user_model()


class ComplaintType(models.Model):
    """نوع الشكوى مع إعدادات تلقائية"""
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='نوع الشكوى',
        unique=True
    )
    description = models.TextField(
        blank=True,
        verbose_name='وصف النوع'
    )
    default_priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='الأولوية الافتراضية'
    )
    default_deadline_hours = models.PositiveIntegerField(
        default=72,
        verbose_name='المهلة الافتراضية (بالساعات)',
        help_text='المهلة الزمنية المحددة تلقائياً لحل الشكوى'
    )
    responsible_department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='القسم المسؤول',
        help_text='القسم المحول إليه تلقائياً'
    )
    default_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المسؤول الافتراضي',
        help_text='الموظف المسؤول عن المتابعة'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='الترتيب'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )
    
    class Meta:
        verbose_name = 'نوع شكوى'
        verbose_name_plural = 'أنواع الشكاوى'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Complaint(models.Model):
    """نموذج الشكوى الرئيسي"""
    STATUS_CHOICES = [
        ('new', 'جديدة'),
        ('in_progress', 'قيد الحل'),
        ('resolved', 'محلولة'),
        ('closed', 'مغلقة'),
        ('overdue', 'متأخرة'),
        ('escalated', 'مصعدة'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    
    RATING_CHOICES = [
        (1, 'غير راضي جداً'),
        (2, 'غير راضي'),
        (3, 'محايد'),
        (4, 'راضي'),
        (5, 'راضي جداً'),
    ]
    
    # معلومات أساسية
    complaint_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='رقم الشكوى',
        editable=False
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='complaints',
        verbose_name='العميل'
    )
    complaint_type = models.ForeignKey(
        ComplaintType,
        on_delete=models.CASCADE,
        verbose_name='نوع الشكوى'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='موضوع الشكوى'
    )
    description = models.TextField(
        verbose_name='وصف الشكوى'
    )
    
    # الطلب المرتبط
    related_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='complaints',
        verbose_name='الطلب المرتبط'
    )
    
    # الأنظمة المرتبطة - Generic Relations
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='نوع المحتوى المرتبط'
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='معرف الكائن المرتبط'
    )
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # حالة ومعلومات الشكوى
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name='حالة الشكوى'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='الأولوية'
    )
    
    # التوقيتات
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ التقديم'
    )
    deadline = models.DateTimeField(
        verbose_name='الموعد النهائي للحل'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ الحل'
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ الإغلاق'
    )
    
    # المسؤوليات
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_complaints',
        verbose_name='مسؤول المتابعة'
    )
    assigned_department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='القسم المحول إليه'
    )
    
    # معلومات الإنشاء
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_complaints',
        verbose_name='تم الإنشاء بواسطة'
    )
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الفرع'
    )
    
    # تقييم العميل
    customer_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='تقييم العميل'
    )
    customer_feedback = models.TextField(
        blank=True,
        verbose_name='تعليق العميل على الحل'
    )
    
    # ملاحظات إضافية
    internal_notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات داخلية'
    )
    
    # تتبع التحديثات
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )
    last_activity_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر نشاط'
    )
    
    class Meta:
        verbose_name = 'شكوى'
        verbose_name_plural = 'الشكاوى'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['complaint_number']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['deadline']),
            models.Index(fields=['created_at']),
        ]
    
    def save(self, *args, **kwargs):
        # إنشاء رقم الشكوى تلقائياً
        if not self.complaint_number:
            from datetime import datetime
            import uuid
            year = datetime.now().year
            month = datetime.now().month
            self.complaint_number = f"C-{year}{month:02d}-{uuid.uuid4().hex[:6].upper()}"
        
        # تحديد الموعد النهائي إذا لم يكن محدداً
        if not self.deadline and self.complaint_type:
            self.deadline = timezone.now() + timedelta(
                hours=self.complaint_type.default_deadline_hours
            )
        
        # تحديد القسم والمسؤول تلقائياً من نوع الشكوى
        if self.complaint_type:
            if not self.assigned_department and self.complaint_type.responsible_department:
                self.assigned_department = self.complaint_type.responsible_department
            if not self.assigned_to and self.complaint_type.default_assignee:
                self.assigned_to = self.complaint_type.default_assignee
            if not self.priority:
                self.priority = self.complaint_type.default_priority
        
        # تحديث حالة الشكوى إذا تجاوزت الموعد النهائي
        if self.deadline and timezone.now() > self.deadline and self.status in ['new', 'in_progress']:
            self.status = 'overdue'
        
        # تحديد تاريخ الحل
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        # تحديد تاريخ الإغلاق
        if self.status == 'closed' and not self.closed_at:
            self.closed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.complaint_number} - {self.customer.name}"
    
    def get_absolute_url(self):
        return reverse('complaints:complaint_detail', kwargs={'pk': self.pk})
    
    @property
    def is_overdue(self):
        """التحقق من تجاوز الموعد النهائي"""
        if self.status in ['resolved', 'closed']:
            return False
        return timezone.now() > self.deadline
    
    @property
    def time_remaining(self):
        """الوقت المتبقي للحل"""
        if self.status in ['resolved', 'closed']:
            return None
        remaining = self.deadline - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    @property
    def resolution_time(self):
        """وقت الحل الفعلي"""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None
    
    def get_status_badge_class(self):
        """لون الشارة حسب الحالة"""
        status_classes = {
            'new': 'bg-primary',
            'in_progress': 'bg-warning',
            'resolved': 'bg-success',
            'closed': 'bg-secondary',
            'overdue': 'bg-danger',
            'escalated': 'bg-dark',
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def get_priority_badge_class(self):
        """لون الشارة حسب الأولوية"""
        priority_classes = {
            'low': 'bg-info',
            'medium': 'bg-warning',
            'high': 'bg-danger',
            'urgent': 'bg-dark',
        }
        return priority_classes.get(self.priority, 'bg-secondary')


class ComplaintUpdate(models.Model):
    """سجل التحديثات والإجراءات على الشكوى"""
    UPDATE_TYPES = [
        ('status_change', 'تغيير الحالة'),
        ('assignment', 'تعيين مسؤول'),
        ('comment', 'تعليق'),
        ('escalation', 'تصعيد'),
        ('resolution', 'حل'),
        ('customer_response', 'رد العميل'),
        ('internal_note', 'ملاحظة داخلية'),
    ]
    
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='updates',
        verbose_name='الشكوى'
    )
    update_type = models.CharField(
        max_length=20,
        choices=UPDATE_TYPES,
        verbose_name='نوع التحديث'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='عنوان التحديث'
    )
    description = models.TextField(
        verbose_name='الوصف'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='تم الإنشاء بواسطة'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ التحديث'
    )
    is_visible_to_customer = models.BooleanField(
        default=True,
        verbose_name='مرئي للعميل'
    )
    
    # للتحديثات التي تغير الحالة
    old_status = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='الحالة السابقة'
    )
    new_status = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='الحالة الجديدة'
    )
    
    # للتحديثات التي تغير المسؤول
    old_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='old_assignments',
        verbose_name='المسؤول السابق'
    )
    new_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='new_assignments',
        verbose_name='المسؤول الجديد'
    )
    
    class Meta:
        verbose_name = 'تحديث شكوى'
        verbose_name_plural = 'تحديثات الشكاوى'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.get_update_type_display()}"


class ComplaintAttachment(models.Model):
    """مرفقات الشكوى"""
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='الشكوى'
    )
    file = models.FileField(
        upload_to='complaints/attachments/%Y/%m/%d/',
        verbose_name='الملف'
    )
    filename = models.CharField(
        max_length=255,
        verbose_name='اسم الملف'
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='وصف الملف'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='رفع بواسطة'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الرفع'
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='حجم الملف (بايت)'
    )
    
    class Meta:
        verbose_name = 'مرفق شكوى'
        verbose_name_plural = 'مرفقات الشكاوى'
        ordering = ['-uploaded_at']
    
    def save(self, *args, **kwargs):
        if self.file:
            self.filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.filename}"


class ComplaintNotification(models.Model):
    """إشعارات الشكاوى"""
    NOTIFICATION_TYPES = [
        ('new_complaint', 'شكوى جديدة'),
        ('status_change', 'تغيير الحالة'),
        ('assignment', 'تعيين مسؤول'),
        ('deadline_reminder', 'تذكير الموعد النهائي'),
        ('overdue', 'تجاوز الموعد النهائي'),
        ('escalation', 'تصعيد'),
        ('resolution', 'حل'),
        ('customer_rating', 'تقييم العميل'),
    ]
    
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='الشكوى'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name='نوع الإشعار'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='عنوان الإشعار'
    )
    message = models.TextField(
        verbose_name='نص الإشعار'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='المستلم'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='تم القراءة'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ القراءة'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإرسال'
    )
    
    class Meta:
        verbose_name = 'إشعار شكوى'
        verbose_name_plural = 'إشعارات الشكاوى'
        ordering = ['-created_at']
    
    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.title}"


class ComplaintEscalation(models.Model):
    """تصعيد الشكاوى"""
    ESCALATION_REASONS = [
        ('overdue', 'تجاوز الموعد النهائي'),
        ('high_priority', 'أولوية عالية'),
        ('customer_request', 'طلب العميل'),
        ('complex_issue', 'مشكلة معقدة'),
        ('department_change', 'تغيير القسم'),
        ('unsatisfactory_response', 'استجابة غير مرضية'),
    ]
    
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name='escalations',
        verbose_name='الشكوى'
    )
    reason = models.CharField(
        max_length=30,
        choices=ESCALATION_REASONS,
        verbose_name='سبب التصعيد'
    )
    description = models.TextField(
        verbose_name='وصف التصعيد'
    )
    escalated_from = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='escalated_from_complaints',
        verbose_name='المصعد من'
    )
    escalated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='escalated_to_complaints',
        verbose_name='المصعد إلى'
    )
    escalated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='escalation_actions',
        verbose_name='تم التصعيد بواسطة'
    )
    escalated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ التصعيد'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ حل التصعيد'
    )
    resolution_notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات الحل'
    )
    
    class Meta:
        verbose_name = 'تصعيد شكوى'
        verbose_name_plural = 'تصعيدات الشكاوى'
        ordering = ['-escalated_at']
    
    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.get_reason_display()}"


class ComplaintSLA(models.Model):
    """اتفاقية مستوى الخدمة للشكاوى"""
    complaint_type = models.OneToOneField(
        ComplaintType,
        on_delete=models.CASCADE,
        related_name='sla',
        verbose_name='نوع الشكوى'
    )
    response_time_hours = models.PositiveIntegerField(
        default=4,
        verbose_name='وقت الاستجابة (ساعات)'
    )
    resolution_time_hours = models.PositiveIntegerField(
        default=72,
        verbose_name='وقت الحل (ساعات)'
    )
    escalation_time_hours = models.PositiveIntegerField(
        default=48,
        verbose_name='وقت التصعيد (ساعات)'
    )
    target_satisfaction_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=90.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='معدل الرضا المستهدف (%)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )
    
    class Meta:
        verbose_name = 'اتفاقية مستوى خدمة'
        verbose_name_plural = 'اتفاقيات مستوى الخدمة'
    
    def __str__(self):
        return f"SLA - {self.complaint_type.name}"
