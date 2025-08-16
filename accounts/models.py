from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.timesince import timesince
from django.conf import settings
class User(AbstractUser):
    """Custom User model for the application."""
    image = models.ImageField(upload_to='users/', verbose_name=_('صورة المستخدم'), blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name=_('رقم الهاتف'), blank=True)
    branch = models.ForeignKey('Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name=_('الفرع'))
    departments = models.ManyToManyField('Department', blank=True, related_name='users', verbose_name=_('الأقسام'))
    is_inspection_technician = models.BooleanField(default=False, verbose_name=_('فني معاينة'))
    is_salesperson = models.BooleanField(default=False, verbose_name=_("بائع"))
    is_branch_manager = models.BooleanField(default=False, verbose_name=_("مدير فرع"))
    is_region_manager = models.BooleanField(default=False, verbose_name=_("مدير منطقة"))
    is_general_manager = models.BooleanField(default=False, verbose_name=_("مدير عام"))
    is_factory_manager = models.BooleanField(default=False, verbose_name=_("مسؤول مصنع"))
    is_inspection_manager = models.BooleanField(default=False, verbose_name=_("مسؤول معاينات"))
    is_installation_manager = models.BooleanField(default=False, verbose_name=_("مسؤول تركيبات"))
    managed_branches = models.ManyToManyField("Branch", blank=True, related_name="region_managers", verbose_name=_("الفروع المُدارة"))
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

    def clean(self):
        """التحقق من صحة البيانات"""
        super().clean()
        
        # التحقق من أن المستخدم لديه دور واحد فقط
        roles = [
            self.is_salesperson,
            self.is_branch_manager,
            self.is_region_manager,
            self.is_general_manager,
            self.is_factory_manager,
            self.is_inspection_manager,
            self.is_installation_manager
        ]
        
        active_roles = sum(roles)
        if active_roles > 1:
            raise ValidationError(_("لا يمكن اختيار أكثر من دور واحد للمستخدم"))
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def get_user_role(self):
        """الحصول على دور المستخدم"""
        if self.is_general_manager:
            return "general_manager"
        elif self.is_region_manager:
            return "region_manager"
        elif self.is_branch_manager:
            return "branch_manager"
        elif self.is_factory_manager:
            return "factory_manager"
        elif self.is_inspection_manager:
            return "inspection_manager"
        elif self.is_installation_manager:
            return "installation_manager"
        elif self.is_salesperson:
            return "salesperson"
        elif self.is_inspection_technician:
            return "inspection_technician"
        else:
            return "user"
    
    def get_user_role_display(self):
        """الحصول على اسم الدور للعرض"""
        role_names = {
            "general_manager": "مدير عام",
            "region_manager": "مدير منطقة",
            "branch_manager": "مدير فرع",
            "factory_manager": "مسؤول مصنع",
            "inspection_manager": "مسؤول معاينات",
            "installation_manager": "مسؤول تركيبات",
            "salesperson": "بائع",
            "inspection_technician": "فني معاينة",
            "user": "مستخدم عادي"
        }
        return role_names.get(self.get_user_role(), "غير محدد")
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
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True, verbose_name='لوغو النظام')
    header_logo = models.ImageField(upload_to='company_logos/header/', null=True, blank=True, verbose_name='لوغو الهيدر', 
                                   help_text='لوغو خاص بالهيدر يمكن أن يكون مختلفاً عن لوغو النظام العام')
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
        ('info', 'معلومات'),
    ]

    DISPLAY_STYLES = [
        ('sweetalert2', 'SweetAlert2 - حديث وأنيق'),
        ('toastr', 'Toastr - إشعارات جانبية'),
        ('notyf', 'Notyf - بسيط وسريع'),
        ('alertify', 'Alertify - كلاسيكي'),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="الفرع", related_name='messages', blank=True, null=True)
    is_for_all_branches = models.BooleanField(default=False, verbose_name="لجميع الفروع")
    title = models.CharField(max_length=200, verbose_name="العنوان")
    message = models.TextField(verbose_name="نص الرسالة")
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='announcement', verbose_name="نوع الرسالة")
    color = models.CharField(max_length=50, default='primary', verbose_name="لون الرسالة")
    icon = models.CharField(max_length=50, default='fas fa-bell', verbose_name="الأيقونة")
    
    # إعدادات التوقيت والعرض الجديدة
    display_duration = models.IntegerField(default=20, verbose_name="مدة العرض (ثانية)", 
                                         help_text="المدة بالثواني (10-50 ثانية)")
    display_style = models.CharField(max_length=20, choices=DISPLAY_STYLES, default='sweetalert2', 
                                   verbose_name="نمط العرض")
    icon_size = models.CharField(max_length=10, default='medium', verbose_name="حجم الأيقونة",
                               choices=[
                                   ('small', 'صغير'),
                                   ('medium', 'متوسط'),
                                   ('large', 'كبير'),
                               ])
    auto_close = models.BooleanField(default=True, verbose_name="إغلاق تلقائي")
    show_close_button = models.BooleanField(default=True, verbose_name="إظهار زر الإغلاق")
    allow_outside_click = models.BooleanField(default=True, verbose_name="السماح بالإغلاق عند النقر خارج الرسالة")
    
    start_date = models.DateTimeField(verbose_name="تاريخ البداية")
    end_date = models.DateTimeField(verbose_name="تاريخ النهاية")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "رسالة الفرع"
        verbose_name_plural = "رسائل الفروع"
        ordering = ['-created_at']

    def clean(self):
        """التحقق من صحة البيانات"""
        super().clean()
        
        if not self.is_for_all_branches and not self.branch:
            raise ValidationError("يجب تحديد الفرع أو اختيار 'لجميع الفروع'")
        
        if self.is_for_all_branches and self.branch:
            raise ValidationError("لا يمكن تحديد فرع معين مع اختيار 'لجميع الفروع'")
        
        # التحقق من مدة العرض
        if self.display_duration < 10 or self.display_duration > 50:
            raise ValidationError("مدة العرض يجب أن تكون بين 10 و 50 ثانية")

    def __str__(self):
        if self.is_for_all_branches:
            return f"جميع الفروع - {self.title}"
        elif self.branch:
            return f"{self.branch.name} - {self.title}"
        else:
            return self.title

    @property
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def get_icon_size_class(self):
        """الحصول على كلاس CSS لحجم الأيقونة"""
        size_map = {
            'small': 'fa-sm',
            'medium': 'fa-lg', 
            'large': 'fa-2x'
        }
        return size_map.get(self.icon_size, 'fa-lg')

    def get_display_duration_ms(self):
        """الحصول على مدة العرض بالميلي ثانية"""
        return self.display_duration * 1000

class DashboardYearSettings(models.Model):
    """
    إعدادات السنوات المتاحة في داش بورد الإدارة
    """
    year = models.IntegerField(_('السنة'), unique=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    is_default = models.BooleanField(_('افتراضي'), default=False)
    description = models.CharField(_('الوصف'), max_length=200, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('إعدادات سنة الداش بورد')
        verbose_name_plural = _('إعدادات سنوات الداش بورد')
        ordering = ['-year']
    
    def __str__(self):
        return f"{self.year} - {'نشط' if self.is_active else 'غير نشط'}"
    
    def save(self, *args, **kwargs):
        # إذا تم تعيين هذه السنة كافتراضية، إلغاء الافتراضية من السنوات الأخرى
        if self.is_default:
            DashboardYearSettings.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_available_years(cls):
        """الحصول على السنوات المتاحة للداش بورد"""
        return cls.objects.filter(is_active=True).values_list('year', flat=True).order_by('-year')
    
    @classmethod
    def get_default_year(cls):
        """الحصول على السنة الافتراضية"""
        default = cls.objects.filter(is_default=True).first()
        if default:
            return default.year
        # إذا لم تكن هناك سنة افتراضية، استخدم السنة الحالية
        from django.utils import timezone
        return timezone.now().year
















