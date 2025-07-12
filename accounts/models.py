from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings
from datetime import timedelta

class User(AbstractUser):
    """Custom User model for the application."""
    image = models.ImageField(upload_to='users/', verbose_name=_('صورة المستخدم'), blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name=_('رقم الهاتف'), blank=True)
    branch = models.ForeignKey('Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name=_('الفرع'))
    departments = models.ManyToManyField('Department', blank=True, related_name='users', verbose_name=_('الأقسام'))
    is_inspection_technician = models.BooleanField(default=False, verbose_name=_('فني معاينة'))
    default_theme = models.CharField(max_length=50, default='default', verbose_name=_('الثيم الافتراضي'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))
    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمين')
    def __str__(self):
        return self.username
    def get_default_theme(self):
        """
        جلب الثيم الافتراضي للمستخدم
        """
        return self.default_theme or 'default'
class Branch(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_main_branch = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = 'فرع'
        verbose_name_plural = 'الفروع'
class Department(models.Model):
    DEPARTMENT_TYPE_CHOICES = [
        ('administration', 'إدارة'),
        ('department', 'قسم'),
        ('unit', 'وحدة'),
    ]
    name = models.CharField(max_length=100, verbose_name='الاسم')
    code = models.CharField(max_length=50, unique=True, verbose_name='الرمز')
    department_type = models.CharField(
        max_length=20,
        choices=DEPARTMENT_TYPE_CHOICES,
        default='department',
        verbose_name='النوع'
    )
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    icon = models.CharField(max_length=50, blank=True, null=True, help_text='Font Awesome icon name', verbose_name='الأيقونة')
    url_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='اسم الرابط')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    is_core = models.BooleanField(
        default=False,
        verbose_name='قسم أساسي',
        help_text='حدد هذا الخيار إذا كان هذا القسم من أقسام النظام الأساسية التي لا يمكن حذفها أو تعديلها'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='الترتيب')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='القسم الرئيسي'
    )
    has_pages = models.BooleanField(
        default=False,
        verbose_name='يحتوي على صفحات',
        help_text='حدد هذا الخيار إذا كان هذا القسم يحتوي على صفحات متعددة'
    )
    manager = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        verbose_name='المدير'
    )
    def get_full_path(self):
        """إرجاع المسار الكامل للقسم من الأعلى إلى الأسفل"""
        path = [self.name]
        current = self.parent
        while current:
            path.append(current.name)
            current = current.parent
        return ' / '.join(reversed(path))
    def save(self, *args, **kwargs):
        """حفظ القسم مع التحقق من الأقسام الأساسية"""
        if self.pk:
            # إذا كان القسم موجودًا بالفعل، نتحقق مما إذا كان قسمًا أساسيًا
            try:
                original = Department.objects.get(pk=self.pk)
                if original.is_core:
                    # لا يمكن تغيير الاسم أو الرمز أو نوع القسم أو الرابط للأقسام الأساسية
                    self.name = original.name
                    self.code = original.code
                    self.department_type = original.department_type
                    self.url_name = original.url_name
                    self.is_core = True  # لا يمكن تغيير حالة القسم الأساسي
            except Department.DoesNotExist:
                pass
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        """حذف القسم مع التحقق من الأقسام الأساسية"""
        if self.is_core:
            # لا يمكن حذف الأقسام الأساسية
            return
        super().delete(*args, **kwargs)
    def __str__(self):
        return f"{self.get_department_type_display()} - {self.name}"
    class Meta:
        verbose_name = 'قسم'
        verbose_name_plural = 'الأقسام'
        ordering = ['order', 'name']
class Notification(models.Model):
    """نموذج الإشعارات المحسن"""
    PRIORITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ]
    
    TYPE_CHOICES = [
        ('info', 'معلومات'),
        ('success', 'نجاح'),
        ('warning', 'تحذير'),
        ('error', 'خطأ'),
        ('order', 'طلب'),
        ('inspection', 'معاينة'),
        ('manufacturing', 'تصنيع'),
        ('inventory', 'مخزون'),
        ('system', 'نظام'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='العنوان')
    message = models.TextField(verbose_name='الرسالة')
    notification_type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default='info',
        verbose_name='نوع الإشعار'
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='medium',
        verbose_name='الأولوية'
    )
    
    # المستلمون
    recipients = models.ManyToManyField(
        User, 
        related_name='received_notifications',
        verbose_name='المستلمون'
    )
    target_departments = models.ManyToManyField(
        Department, 
        blank=True,
        verbose_name='الأقسام المستهدفة'
    )
    target_branches = models.ManyToManyField(
        Branch, 
        blank=True,
        verbose_name='الفروع المستهدفة'
    )
    
    # الكائن المرتبط
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name='نوع المحتوى'
    )
    object_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='معرف الكائن'
    )
    
    # حالة الإشعار
    is_read = models.BooleanField(default=False, verbose_name='مقروء')
    is_sent = models.BooleanField(default=False, verbose_name='تم الإرسال')
    is_archived = models.BooleanField(default=False, verbose_name='مؤرشف')
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإرسال')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ القراءة')
    
    # المرسل
    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sent_notifications',
        verbose_name='المرسل'
    )
    
    # إعدادات إضافية
    auto_delete_after_days = models.PositiveIntegerField(
        default=30,
        verbose_name='حذف تلقائي بعد (أيام)'
    )
    requires_action = models.BooleanField(
        default=False,
        verbose_name='يتطلب إجراء'
    )
    action_url = models.URLField(
        blank=True,
        verbose_name='رابط الإجراء'
    )
    
    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification_type', 'priority']),
            models.Index(fields=['is_read', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"
    
    def mark_as_read(self, user):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_sent(self):
        """تحديد الإشعار كمرسل"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = timezone.now()
            self.save(update_fields=['is_sent', 'sent_at'])
    
    def archive(self):
        """أرشفة الإشعار"""
        self.is_archived = True
        self.save(update_fields=['is_archived'])
    
    @classmethod
    def create_notification(cls, title, message, notification_type='info', 
                          priority='medium', recipients=None, **kwargs):
        """إنشاء إشعار جديد"""
        notification = cls.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            **kwargs
        )
        
        if recipients:
            notification.recipients.set(recipients)
        
        return notification
    
    @classmethod
    def get_unread_for_user(cls, user):
        """الحصول على الإشعارات غير المقروءة للمستخدم"""
        return cls.objects.filter(
            recipients=user,
            is_read=False,
            is_archived=False
        ).select_related('sender', 'content_type')
    
    @classmethod
    def get_recent_for_user(cls, user, limit=10):
        """الحصول على أحدث الإشعارات للمستخدم"""
        return cls.objects.filter(
            recipients=user,
            is_archived=False
        ).select_related('sender', 'content_type').order_by('-created_at')[:limit]
class CompanyInfo(models.Model):
    # حقول مخصصة للنظام - لا يمكن تغييرها إلا من المبرمج
    version = models.CharField(max_length=50, blank=True, default='1.0.0', verbose_name='إصدار النظام', editable=False)
    release_date = models.CharField(max_length=50, blank=True, default='2025-04-30', verbose_name='تاريخ الإطلاق', editable=False)
    developer = models.CharField(max_length=100, blank=True, default='zakee tahawi', verbose_name='المطور', editable=False)
    working_hours = models.CharField(max_length=100, blank=True, default='', verbose_name='ساعات العمل')
    # اسم الشركة
    name = models.CharField(max_length=200, default='Elkhawaga', verbose_name='اسم الشركة')
    # نص حقوق النشر المخصص
    copyright_text = models.CharField(
        max_length=255,
        default='جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi',
        verbose_name='نص حقوق النشر',
        blank=True
    )
    # باقي الحقول
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    commercial_register = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    social_links = models.JSONField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    vision = models.TextField(blank=True, null=True)
    mission = models.TextField(blank=True, null=True)
    primary_color = models.CharField(max_length=20, blank=True, null=True)
    secondary_color = models.CharField(max_length=20, blank=True, null=True)
    accent_color = models.CharField(max_length=20, blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = 'معلومات الشركة'
        verbose_name_plural = 'معلومات الشركة'
class FormField(models.Model):
    FORM_TYPE_CHOICES = [
        ('customer', 'نموذج العميل'),
        ('order', 'نموذج الطلب'),
        ('inspection', 'نموذج المعاينة'),
        ('installation', 'نموذج التركيب'),
        ('product', 'نموذج المنتج'),
    ]
    FIELD_TYPE_CHOICES = [
        ('text', 'نص'),
        ('number', 'رقم'),
        ('email', 'بريد إلكتروني'),
        ('phone', 'هاتف'),
        ('date', 'تاريخ'),
        ('select', 'قائمة اختيار'),
        ('checkbox', 'مربع اختيار'),
        ('radio', 'زر اختيار'),
        ('textarea', 'منطقة نص'),
        ('file', 'ملف'),
    ]
    form_type = models.CharField(max_length=20, choices=FORM_TYPE_CHOICES)
    field_name = models.CharField(max_length=100)
    field_label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    required = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    choices = models.TextField(blank=True, null=True, help_text='قائمة الخيارات مفصولة بفواصل (للحقول من نوع select, radio, checkbox)')
    default_value = models.CharField(max_length=255, blank=True, null=True)
    help_text = models.CharField(max_length=255, blank=True, null=True)
    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    def __str__(self):
        return f'{self.get_form_type_display()}: {self.field_label}'
    class Meta:
        verbose_name = 'حقل نموذج'
        verbose_name_plural = 'حقول النماذج'
        unique_together = ('form_type', 'field_name')
class Employee(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم الموظف')
    employee_id = models.CharField(max_length=50, unique=True, verbose_name='رقم الموظف')
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='employees', verbose_name='الفرع')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    class Meta:
        verbose_name = 'موظف'
        verbose_name_plural = 'الموظفون'
        ordering = ['name']
    def __str__(self):
        return f'{self.name} ({self.employee_id})'
class Salesperson(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('اسم البائع'))
    employee_number = models.CharField(max_length=50, verbose_name=_('الرقم الوظيفي'), blank=True, null=True)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='salespersons', verbose_name=_('الفرع'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('رقم الهاتف'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('البريد الإلكتروني'))
    address = models.TextField(blank=True, null=True, verbose_name=_('العنوان'))
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))
    class Meta:
        verbose_name = _('بائع')
        verbose_name_plural = _('البائعون')
        ordering = ['name']
    def __str__(self):
        return f'{self.name} ({self.employee_number})' if self.employee_number else self.name
    def clean(self):
        if self.branch and not self.branch.is_active:
            raise ValidationError(_('لا يمكن إضافة بائع لفرع غير نشط'))
        if self.employee_number and self.branch:
            exists = Salesperson.objects.filter(
                employee_number=self.employee_number,
                branch=self.branch
            ).exclude(pk=self.pk).exists()
            if exists:
                raise ValidationError(_('هذا الرقم الوظيفي مستخدم بالفعل في هذا الفرع'))
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
class ContactFormSettings(models.Model):
    """إعدادات نموذج الاتصال"""
    title = models.CharField(max_length=100, default='اتصل بنا', verbose_name='عنوان الصفحة')
    description = models.TextField(blank=True, null=True, verbose_name='وصف الصفحة')
    # اسم الشركة المعروض في صفحة الاتصال
    company_name = models.CharField(max_length=200, default='Elkhawaga', verbose_name='اسم الشركة')
    # معلومات جهات الاتصال
    contact_email = models.EmailField(default='info@elkhawaga.com', verbose_name='البريد الإلكتروني للاتصال')
    contact_phone = models.CharField(max_length=20, default='+20 123 456 7890', verbose_name='رقم الهاتف للاتصال')
    contact_address = models.TextField(blank=True, null=True, verbose_name='عنوان المكتب')
    contact_hours = models.CharField(max_length=100, default='9 صباحاً - 5 مساءً', verbose_name='ساعات العمل')
    # إعدادات النموذج
    form_title = models.CharField(max_length=100, default='نموذج الاتصال', verbose_name='عنوان النموذج')
    form_success_message = models.CharField(max_length=200, default='تم إرسال رسالتك بنجاح. سنتواصل معك قريباً.', verbose_name='رسالة النجاح')
    form_error_message = models.CharField(max_length=200, default='يرجى ملء جميع الحقول المطلوبة.', verbose_name='رسالة الخطأ')
    class Meta:
        verbose_name = 'إعدادات نموذج الاتصال'
        verbose_name_plural = 'إعدادات نموذج الاتصال'
    def __str__(self):
        return 'إعدادات نموذج الاتصال'
    def save(self, *args, **kwargs):
        # نتأكد أن هناك صف واحد فقط من الإعدادات
        if not self.pk and ContactFormSettings.objects.exists():
            return  # لا تحفظ إذا كان هناك صف موجود بالفعل
        super().save(*args, **kwargs)
class FooterSettings(models.Model):
    """إعدادات تذييل الصفحة"""
    left_column_title = models.CharField(max_length=100, default='عن الشركة', verbose_name='عنوان العمود الأيسر')
    left_column_text = models.TextField(default='نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون', verbose_name='نص العمود الأيسر')
    middle_column_title = models.CharField(max_length=100, default='روابط سريعة', verbose_name='عنوان العمود الأوسط')
    right_column_title = models.CharField(max_length=100, default='تواصل معنا', verbose_name='عنوان العمود الأيمن')
    class Meta:
        verbose_name = 'إعدادات تذييل الصفحة'
        verbose_name_plural = 'إعدادات تذييل الصفحة'
    def __str__(self):
        return 'إعدادات تذييل الصفحة'
    def save(self, *args, **kwargs):
        # نتأكد أن هناك صف واحد فقط من الإعدادات
        if not self.pk and FooterSettings.objects.exists():
            return  # لا تحفظ إذا كان هناك صف موجود بالفعل
        super().save(*args, **kwargs)
class AboutPageSettings(models.Model):
    """إعدادات صفحة عن النظام"""
    title = models.CharField(max_length=100, default='عن النظام', verbose_name='عنوان الصفحة')
    subtitle = models.CharField(max_length=200, default='نظام إدارة المصنع والعملاء', verbose_name='العنوان الفرعي')
    # معلومات النظام - للعرض فقط
    system_version = models.CharField(max_length=50, default='1.0.0', editable=False, verbose_name='إصدار النظام')
    system_release_date = models.CharField(max_length=50, default='2025-04-30', editable=False, verbose_name='تاريخ الإطلاق')
    system_developer = models.CharField(max_length=100, default='zakee tahawi', editable=False, verbose_name='المطور')
    # وصف النظام - قابل للتعديل
    system_description = models.TextField(default='نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون', verbose_name='وصف النظام')
    class Meta:
        verbose_name = 'إعدادات صفحة عن النظام'
        verbose_name_plural = 'إعدادات صفحة عن النظام'
    def __str__(self):
        return 'إعدادات صفحة عن النظام'
    def save(self, *args, **kwargs):
        # نتأكد أن هناك صف واحد فقط من الإعدادات
        if not self.pk and AboutPageSettings.objects.exists():
            return  # لا تحفظ إذا كان هناك صف موجود بالفعل
        super().save(*args, **kwargs)
class Role(models.Model):
    """نموذج الأدوار للمستخدمين في النظام"""
    name = models.CharField(max_length=100, unique=True, verbose_name='اسم الدور')
    description = models.TextField(blank=True, null=True, verbose_name='وصف الدور')
    permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='الصلاحيات',
        blank=True,
    )
    is_system_role = models.BooleanField(default=False, verbose_name='دور نظام',
                                         help_text='تحديد ما إذا كان هذا الدور من أدوار النظام الأساسية التي لا يمكن تعديلها')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    class Meta:
        verbose_name = 'دور'
        verbose_name_plural = 'الأدوار'
        ordering = ['name']
    def __str__(self):
        return self.name
    def assign_to_user(self, user):
        """إسناد هذا الدور للمستخدم المحدد"""
        # إضافة المستخدم إلى هذا الدور
        UserRole.objects.get_or_create(user=user, role=self)
        # إضافة صلاحيات الدور للمستخدم
        for permission in self.permissions.all():
            user.user_permissions.add(permission)
    def remove_from_user(self, user):
        """إزالة هذا الدور من المستخدم المحدد"""
        # حذف المستخدم من هذا الدور
        UserRole.objects.filter(user=user, role=self).delete()
        # حذف صلاحيات الدور من المستخدم
        # نحذف فقط الصلاحيات التي تنتمي حصرياً لهذا الدور وليست موجودة في أي دور آخر للمستخدم
        for permission in self.permissions.all():
            if not UserRole.objects.filter(user=user, role__permissions=permission).exists():
                user.user_permissions.remove(permission)
class UserRole(models.Model):
    """العلاقة بين المستخدمين والأدوار"""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='user_roles', verbose_name='المستخدم')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles', verbose_name='الدور')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإسناد')
    class Meta:
        verbose_name = 'دور المستخدم'
        verbose_name_plural = 'أدوار المستخدمين'
        unique_together = ['user', 'role']  # لضمان عدم تكرار الدور للمستخدم
    def __str__(self):
        return f"{self.user} - {self.role}"
class ActivityLog(models.Model):
    ACTIVITY_TYPES = [
        ('عميل', 'عميل'),
        ('طلب', 'طلب'),
        ('مخزون', 'مخزون'),
        ('تركيب', 'تركيب'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-timestamp']
class SystemSettings(models.Model):
    """
    نموذج لإعدادات النظام العامة
    """
    CURRENCY_CHOICES = [
        ('SAR', _('ريال سعودي')),
        ('EGP', _('جنيه مصري')),
        ('USD', _('دولار أمريكي')),
        ('EUR', _('يورو')),
        ('AED', _('درهم إماراتي')),
        ('KWD', _('دينار كويتي')),
        ('QAR', _('ريال قطري')),
        ('BHD', _('دينار بحريني')),
        ('OMR', _('ريال عماني')),
    ]
    CURRENCY_SYMBOLS = {
        'SAR': 'ر.س',
        'EGP': 'ج.م',
        'USD': '$',
        'EUR': '€',
        'AED': 'د.إ',
        'KWD': 'د.ك',
        'QAR': 'ر.ق',
        'BHD': 'د.ب',
        'OMR': 'ر.ع',
    }
    name = models.CharField(_('اسم النظام'), max_length=100, default='نظام الخواجه')
    currency = models.CharField(_('العملة'), max_length=3, choices=CURRENCY_CHOICES, default='SAR')
    version = models.CharField(_('إصدار النظام'), max_length=20, default='1.0.0')
    enable_notifications = models.BooleanField(_('تفعيل الإشعارات'), default=True)
    enable_email_notifications = models.BooleanField(_('تفعيل إشعارات البريد الإلكتروني'), default=False)
    items_per_page = models.PositiveIntegerField(_('عدد العناصر في الصفحة'), default=20)
    low_stock_threshold = models.PositiveIntegerField(_('حد المخزون المنخفض (%)'), default=20)
    enable_analytics = models.BooleanField(_('تفعيل التحليلات'), default=True)
    maintenance_mode = models.BooleanField(_('وضع الصيانة'), default=False)
    maintenance_message = models.TextField(_('رسالة الصيانة'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    class Meta:
        verbose_name = _('إعدادات النظام')
        verbose_name_plural = _('إعدادات النظام')
    def __str__(self):
        return self.name
    @property
    def currency_symbol(self):
        """الحصول على رمز العملة"""
        return self.CURRENCY_SYMBOLS.get(self.currency, self.currency)
    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات النظام (إنشاء إذا لم تكن موجودة)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
class BranchMessage(models.Model):
    MESSAGE_TYPES = [
        ('welcome', 'رسالة ترحيبية'),
        ('goal', 'هدف'),
        ('announcement', 'إعلان'),
        ('holiday', 'إجازة'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="الفرع", related_name='messages')
    title = models.CharField(max_length=200, verbose_name="العنوان")
    message = models.TextField(verbose_name="نص الرسالة")
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='announcement', verbose_name="نوع الرسالة")
    color = models.CharField(max_length=50, default='primary', verbose_name="لون الرسالة")
    icon = models.CharField(max_length=50, default='fas fa-bell', verbose_name="الأيقونة")
    start_date = models.DateTimeField(verbose_name="تاريخ البداية")
    end_date = models.DateTimeField(verbose_name="تاريخ النهاية")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "رسالة الفرع"
        verbose_name_plural = "رسائل الفروع"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.branch.name} - {self.title}"

    @property
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class UnifiedSystemSettings(models.Model):
    """
    نموذج موحد لإعدادات النظام ومعلومات الشركة
    يجمع بين CompanyInfo و SystemSettings في نموذج واحد
    """
    CURRENCY_CHOICES = [
        ('SAR', _('ريال سعودي')),
        ('EGP', _('جنيه مصري')),
        ('USD', _('دولار أمريكي')),
        ('EUR', _('يورو')),
        ('AED', _('درهم إماراتي')),
        ('KWD', _('دينار كويتي')),
        ('QAR', _('ريال قطري')),
        ('BHD', _('دينار بحريني')),
        ('OMR', _('ريال عماني')),
    ]
    
    # معلومات الشركة الأساسية
    company_name = models.CharField(max_length=200, default='Elkhawaga', verbose_name='اسم الشركة')
    company_logo = models.ImageField(upload_to='company_logos/', null=True, blank=True, verbose_name='شعار الشركة')
    company_address = models.TextField(blank=True, null=True, verbose_name='عنوان الشركة')
    company_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='هاتف الشركة')
    company_email = models.EmailField(blank=True, null=True, verbose_name='بريد الشركة')
    company_website = models.URLField(blank=True, null=True, verbose_name='موقع الشركة')
    
    # معلومات قانونية
    tax_number = models.CharField(max_length=50, blank=True, null=True, verbose_name='الرقم الضريبي')
    commercial_register = models.CharField(max_length=50, blank=True, null=True, verbose_name='السجل التجاري')
    
    # إعدادات النظام
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='SAR', verbose_name='العملة')
    enable_notifications = models.BooleanField(default=True, verbose_name='تفعيل الإشعارات')
    enable_email_notifications = models.BooleanField(default=False, verbose_name='تفعيل إشعارات البريد الإلكتروني')
    items_per_page = models.PositiveIntegerField(default=20, verbose_name='عدد العناصر في الصفحة')
    low_stock_threshold = models.PositiveIntegerField(default=20, verbose_name='حد المخزون المنخفض (%)')
    enable_analytics = models.BooleanField(default=True, verbose_name='تفعيل التحليلات')
    
    # إعدادات الواجهة
    primary_color = models.CharField(max_length=20, blank=True, null=True, verbose_name='اللون الأساسي')
    secondary_color = models.CharField(max_length=20, blank=True, null=True, verbose_name='اللون الثانوي')
    accent_color = models.CharField(max_length=20, blank=True, null=True, verbose_name='لون التمييز')
    default_theme = models.CharField(max_length=50, default='default', verbose_name='الثيم الافتراضي')
    
    # معلومات إضافية
    working_hours = models.CharField(max_length=100, blank=True, default='', verbose_name='ساعات العمل')
    about_text = models.TextField(blank=True, null=True, verbose_name='نص عن الشركة')
    vision_text = models.TextField(blank=True, null=True, verbose_name='رؤية الشركة')
    mission_text = models.TextField(blank=True, null=True, verbose_name='رسالة الشركة')
    description = models.TextField(blank=True, null=True, verbose_name='وصف الشركة')
    
    # وسائل التواصل الاجتماعي
    facebook_url = models.URLField(blank=True, null=True, verbose_name='رابط فيسبوك')
    twitter_url = models.URLField(blank=True, null=True, verbose_name='رابط تويتر')
    instagram_url = models.URLField(blank=True, null=True, verbose_name='رابط انستغرام')
    linkedin_url = models.URLField(blank=True, null=True, verbose_name='رابط لينكد إن')
    social_links = models.JSONField(blank=True, null=True, verbose_name='روابط التواصل الاجتماعي الإضافية')
    
    # إعدادات متقدمة
    maintenance_mode = models.BooleanField(default=False, verbose_name='وضع الصيانة')
    maintenance_message = models.TextField(blank=True, verbose_name='رسالة الصيانة')
    
    # معلومات النظام (للعرض فقط)
    system_version = models.CharField(max_length=50, default='1.0.0', editable=False, verbose_name='إصدار النظام')
    system_release_date = models.CharField(max_length=50, default='2025-04-30', editable=False, verbose_name='تاريخ الإطلاق')
    system_developer = models.CharField(max_length=100, default='zakee tahawi', editable=False, verbose_name='المطور')
    
    # حقوق النشر
    copyright_text = models.CharField(
        max_length=255,
        default='جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi',
        verbose_name='نص حقوق النشر',
        blank=True
    )
    
    # تواريخ النظام
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
    class Meta:
        verbose_name = 'إعدادات النظام الموحدة'
        verbose_name_plural = 'إعدادات النظام الموحدة'
    
    def __str__(self):
        return f"إعدادات {self.company_name}"
    
    @property
    def currency_symbol(self):
        """إرجاع رمز العملة"""
        symbols = {
            'SAR': 'ر.س', 'EGP': 'ج.م', 'USD': '$', 'EUR': '€',
            'AED': 'د.إ', 'KWD': 'د.ك', 'QAR': 'ر.ق', 'BHD': 'د.ب', 'OMR': 'ر.ع'
        }
        return symbols.get(self.currency, self.currency)
    
    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات النظام (إنشاء واحدة إذا لم تكن موجودة)"""
        settings, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'company_name': 'Elkhawaga',
                'currency': 'SAR',
                'enable_notifications': True,
                'items_per_page': 20,
                'low_stock_threshold': 20,
                'enable_analytics': True,
                'default_theme': 'default',
                'working_hours': '9 صباحاً - 5 مساءً',
                'copyright_text': 'جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi'
            }
        )
        return settings
    
    def save(self, *args, **kwargs):
        """حفظ الإعدادات مع التأكد من وجود صف واحد فقط"""
        if not self.pk:
            # إذا كان هذا أول صف، تأكد من عدم وجود صفوف أخرى
            UnifiedSystemSettings.objects.all().delete()
        super().save(*args, **kwargs)

class UserSecurityProfile(models.Model):
    """
    نموذج لملف الأمان المتقدم للمستخدم
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_profile')
    
    # Two-Factor Authentication
    two_factor_enabled = models.BooleanField(_('تفعيل المصادقة الثنائية'), default=False)
    two_factor_secret = models.CharField(_('مفتاح المصادقة الثنائية'), max_length=32, blank=True)
    backup_codes = models.JSONField(_('رموز النسخ الاحتياطي'), default=list, blank=True)
    
    # Password Security
    password_changed_at = models.DateTimeField(_('تاريخ تغيير كلمة المرور'), auto_now_add=True)
    password_expires_at = models.DateTimeField(_('تاريخ انتهاء كلمة المرور'), null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(_('محاولات تسجيل الدخول الفاشلة'), default=0)
    locked_until = models.DateTimeField(_('مقفل حتى'), null=True, blank=True)
    
    # Session Security
    last_login_ip = models.GenericIPAddressField(_('آخر IP لتسجيل الدخول'), null=True, blank=True)
    last_login_user_agent = models.TextField(_('آخر User Agent'), blank=True)
    session_timeout = models.PositiveIntegerField(_('مهلة الجلسة (دقائق)'), default=30)
    
    # Audit Logging
    login_history = models.JSONField(_('سجل تسجيل الدخول'), default=list, blank=True)
    security_events = models.JSONField(_('الأحداث الأمنية'), default=list, blank=True)
    
    class Meta:
        verbose_name = _('ملف الأمان')
        verbose_name_plural = _('ملفات الأمان')
    
    def __str__(self):
        return f"ملف الأمان - {self.user.username}"
    
    def is_locked(self):
        """التحقق من حالة القفل"""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def increment_failed_attempts(self):
        """زيادة محاولات تسجيل الدخول الفاشلة"""
        self.failed_login_attempts += 1
        
        # قفل الحساب بعد 5 محاولات فاشلة
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=30)
        
        self.save()
    
    def reset_failed_attempts(self):
        """إعادة تعيين محاولات تسجيل الدخول الفاشلة"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save()
    
    def log_login_attempt(self, success, ip_address, user_agent):
        """تسجيل محاولة تسجيل الدخول"""
        login_record = {
            'timestamp': timezone.now().isoformat(),
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        self.login_history.append(login_record)
        
        # الاحتفاظ بآخر 100 محاولة فقط
        if len(self.login_history) > 100:
            self.login_history = self.login_history[-100:]
        
        if success:
            self.last_login_ip = ip_address
            self.last_login_user_agent = user_agent
            self.reset_failed_attempts()
        
        self.save()
    
    def log_security_event(self, event_type, description, severity='medium'):
        """تسجيل حدث أمني"""
        event = {
            'timestamp': timezone.now().isoformat(),
            'type': event_type,
            'description': description,
            'severity': severity
        }
        
        self.security_events.append(event)
        
        # الاحتفاظ بآخر 50 حدث فقط
        if len(self.security_events) > 50:
            self.security_events = self.security_events[-50:]
        
        self.save()
    
    def is_password_expired(self):
        """التحقق من انتهاء صلاحية كلمة المرور"""
        if self.password_expires_at and timezone.now() > self.password_expires_at:
            return True
        return False
    
    def set_password_expiry(self, days=90):
        """تعيين تاريخ انتهاء كلمة المرور"""
        self.password_expires_at = timezone.now() + timedelta(days=days)
        self.save()


class AuditLog(models.Model):
    """
    نموذج لتسجيل الأحداث الأمنية
    """
    EVENT_TYPES = [
        ('login', _('تسجيل دخول')),
        ('logout', _('تسجيل خروج')),
        ('password_change', _('تغيير كلمة المرور')),
        ('permission_change', _('تغيير الصلاحيات')),
        ('data_access', _('الوصول للبيانات')),
        ('data_modification', _('تعديل البيانات')),
        ('security_violation', _('انتهاك أمني')),
        ('system_event', _('حدث نظام')),
    ]
    
    SEVERITY_LEVELS = [
        ('low', _('منخفض')),
        ('medium', _('متوسط')),
        ('high', _('عالي')),
        ('critical', _('حرج')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(_('نوع الحدث'), max_length=20, choices=EVENT_TYPES)
    severity = models.CharField(_('مستوى الخطورة'), max_length=10, choices=SEVERITY_LEVELS, default='medium')
    description = models.TextField(_('الوصف'))
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    related_object_type = models.CharField(_('نوع الكائن المرتبط'), max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(_('معرف الكائن المرتبط'), null=True, blank=True)
    additional_data = models.JSONField(_('بيانات إضافية'), default=dict, blank=True)
    timestamp = models.DateTimeField(_('التوقيت'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل تدقيق')
        verbose_name_plural = _('سجلات التدقيق')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.user.username if self.user else 'Unknown'} - {self.timestamp}"
    
    @classmethod
    def log_event(cls, user, event_type, description, severity='medium', **kwargs):
        """تسجيل حدث أمني"""
        return cls.objects.create(
            user=user,
            event_type=event_type,
            severity=severity,
            description=description,
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent'),
            related_object_type=kwargs.get('related_object_type'),
            related_object_id=kwargs.get('related_object_id'),
            additional_data=kwargs.get('additional_data', {})
        )
