from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.timesince import timesince
from django.conf import settings

# التسلسل الهرمي للأدوار من الأعلى إلى الأدنى
ROLE_HIERARCHY = {
    'general_manager': {
        'level': 1,
        'display': 'مدير عام',
        'inherits_from': [],
        'permissions': ['all']
    },
    'region_manager': {
        'level': 2,
        'display': 'مدير منطقة',
        'inherits_from': ['branch_manager'],
        'permissions': ['view_all_region_orders', 'manage_branches', 'manage_users']
    },
    'branch_manager': {
        'level': 3,
        'display': 'مدير فرع',
        'inherits_from': ['salesperson'],
        'permissions': ['view_branch_orders', 'manage_branch_users', 'approve_orders']
    },
    'factory_manager': {
        'level': 2,
        'display': 'مسؤول مصنع',
        'inherits_from': [],
        'permissions': ['view_all_orders', 'manage_manufacturing', 'manage_inventory']
    },
    'inspection_manager': {
        'level': 3,
        'display': 'مسؤول معاينات',
        'inherits_from': ['inspection_technician'],
        'permissions': ['view_all_inspections', 'assign_inspections', 'manage_technicians']
    },
    'installation_manager': {
        'level': 3,
        'display': 'مسؤول تركيبات',
        'inherits_from': [],
        'permissions': ['view_all_installations', 'assign_installations', 'manage_installers']
    },
    'warehouse_staff': {
        'level': 4,
        'display': 'موظف مستودع',
        'inherits_from': [],
        'permissions': ['manage_warehouse_inventory', 'transfer_products']
    },
    'salesperson': {
        'level': 4,
        'display': 'بائع',
        'inherits_from': [],
        'permissions': ['create_orders', 'view_own_orders', 'edit_own_orders']
    },
    'inspection_technician': {
        'level': 5,
        'display': 'فني معاينة',
        'inherits_from': [],
        'permissions': ['view_assigned_inspections', 'update_inspection_status']
    },
    'user': {
        'level': 6,
        'display': 'مستخدم عادي',
        'inherits_from': [],
        'permissions': ['view_dashboard']
    }
}
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
    is_warehouse_staff = models.BooleanField(default=False, verbose_name=_("موظف مستودع"))
    assigned_warehouse = models.ForeignKey(
        'inventory.Warehouse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warehouse_staff',
        verbose_name=_('المستودع المخصص'),
        help_text=_('المستودع المخصص لموظف المستودع')
    )
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
            self.is_installation_manager,
            self.is_warehouse_staff
        ]

        active_roles = sum(roles)
        if active_roles > 1:
            raise ValidationError(_("لا يمكن اختيار أكثر من دور واحد للمستخدم"))

        # التحقق من أن موظف المستودع لديه مستودع مخصص
        if self.is_warehouse_staff and not self.assigned_warehouse:
            raise ValidationError(_("يجب تحديد مستودع مخصص لموظف المستودع"))
    
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
        elif self.is_warehouse_staff:
            return "warehouse_staff"
        elif self.is_salesperson:
            return "salesperson"
        elif self.is_inspection_technician:
            return "inspection_technician"
        else:
            return "user"

    def get_user_role_display(self):
        """الحصول على اسم الدور للعرض"""
        role = self.get_user_role()
        return ROLE_HIERARCHY.get(role, {}).get('display', 'غير محدد')
    
    def get_role_level(self):
        """الحصول على مستوى الدور في التسلسل الهرمي"""
        role = self.get_user_role()
        return ROLE_HIERARCHY.get(role, {}).get('level', 999)
    
    def get_inherited_roles(self):
        """الحصول على الأدوار التي يرثها هذا المستخدم"""
        role = self.get_user_role()
        inherited = []
        
        def collect_inherited(role_key):
            role_data = ROLE_HIERARCHY.get(role_key, {})
            inherits_from = role_data.get('inherits_from', [])
            for inherited_role in inherits_from:
                if inherited_role not in inherited:
                    inherited.append(inherited_role)
                    collect_inherited(inherited_role)
        
        collect_inherited(role)
        return inherited
    
    def get_all_permissions(self):
        """الحصول على جميع الصلاحيات بما في ذلك الموروثة"""
        role = self.get_user_role()
        all_permissions = set()
        
        # إضافة صلاحيات الدور الحالي
        current_perms = ROLE_HIERARCHY.get(role, {}).get('permissions', [])
        all_permissions.update(current_perms)
        
        # إضافة صلاحيات الأدوار الموروثة
        for inherited_role in self.get_inherited_roles():
            inherited_perms = ROLE_HIERARCHY.get(inherited_role, {}).get('permissions', [])
            all_permissions.update(inherited_perms)
        
        return list(all_permissions)
    
    def has_role_permission(self, permission):
        """التحقق من امتلاك المستخدم لصلاحية معينة (بما في ذلك الموروثة)"""
        if self.is_superuser:
            return True
        
        all_perms = self.get_all_permissions()
        return 'all' in all_perms or permission in all_perms
    
    def can_manage_user(self, other_user):
        """التحقق من إمكانية إدارة مستخدم آخر بناءً على التسلسل الهرمي"""
        if self.is_superuser:
            return True
        
        # المستخدم لا يمكنه إدارة نفسه
        if self.id == other_user.id:
            return False
        
        # المستخدم يمكنه إدارة من هم أدنى منه في التسلسل الهرمي فقط
        return self.get_role_level() < other_user.get_role_level()
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
    user = models.OneToOneField(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='salesperson_profile',
        verbose_name=_('حساب المستخدم'),
        help_text=_('ربط البائع بحساب مستخدم (اختياري)')
    )
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
        if self.user:
            return f'{self.name} ({self.user.username})'
        return f'{self.name} ({self.employee_number})' if self.employee_number else self.name

    def get_display_name(self):
        """الحصول على الاسم المناسب للعرض"""
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.name
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
    currency = models.CharField(_('العملة'), max_length=3, choices=CURRENCY_CHOICES, default='EGP')
    version = models.CharField(_('إصدار النظام'), max_length=20, default='1.0.0')

    enable_notifications = models.BooleanField(_('تفعيل الإشعارات'), default=True)
    enable_email_notifications = models.BooleanField(_('تفعيل إشعارات البريد الإلكتروني'), default=False)
    items_per_page = models.PositiveIntegerField(_('عدد العناصر في الصفحة'), default=20)
    low_stock_threshold = models.PositiveIntegerField(_('حد المخزون المنخفض (%)'), default=20)
    enable_analytics = models.BooleanField(_('تفعيل التحليلات'), default=True)
    maintenance_mode = models.BooleanField(_('وضع الصيانة'), default=False)
    maintenance_message = models.TextField(_('رسالة الصيانة'), blank=True)
    
    # إعدادات الويزارد والدرافتات
    max_draft_orders_per_user = models.PositiveIntegerField(
        _('الحد الأقصى للمسودات لكل مستخدم'),
        default=5,
        help_text=_('العدد الأقصى للمسودات (الدرافتات) المسموح بها لكل مستخدم')
    )
    
    # إعدادات أمان الأجهزة
    enable_device_restriction = models.BooleanField(
        _('تفعيل قفل الأجهزة'),
        default=False,
        help_text=_('عند التفعيل، لن يتمكن الموظفون من تسجيل الدخول إلا من الأجهزة المسجلة لفرعهم. السوبر يوزر والمدير العام معفيين.')
    )
    
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


class InternalMessage(models.Model):
    """
    نموذج الرسائل الداخلية بين المستخدمين
    """
    sender = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name=_('المرسل')
    )
    recipient = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name=_('المستلم')
    )
    subject = models.CharField(_('الموضوع'), max_length=200)
    body = models.TextField(_('المحتوى'))
    is_read = models.BooleanField(_('مقروءة'), default=False)
    read_at = models.DateTimeField(_('تاريخ القراءة'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإرسال'), auto_now_add=True)
    
    # حقول إضافية للميزات المتقدمة
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('الرسالة الأصلية')
    )
    is_important = models.BooleanField(_('مهم'), default=False)
    is_deleted_by_sender = models.BooleanField(_('محذوفة من المرسل'), default=False)
    is_deleted_by_recipient = models.BooleanField(_('محذوفة من المستلم'), default=False)
    
    class Meta:
        verbose_name = _('رسالة داخلية')
        verbose_name_plural = _('الرسائل الداخلية')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['is_read', 'recipient']),
        ]
    
    def __str__(self):
        return f"{self.sender.get_full_name()} → {self.recipient.get_full_name()}: {self.subject}"
    
    def mark_as_read(self):
        """تحديد الرسالة كمقروءة"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @classmethod
    def get_unread_count(cls, user):
        """الحصول على عدد الرسائل غير المقروءة للمستخدم"""
        return cls.objects.filter(
            recipient=user,
            is_read=False,
            is_deleted_by_recipient=False
        ).count()
    
    @classmethod
    def get_inbox(cls, user):
        """الحصول على صندوق الوارد للمستخدم"""
        return cls.objects.filter(
            recipient=user,
            is_deleted_by_recipient=False
        ).select_related('sender')
    
    @classmethod
    def get_sent_messages(cls, user):
        """الحصول على الرسائل المرسلة للمستخدم"""
        return cls.objects.filter(
            sender=user,
            is_deleted_by_sender=False
        ).select_related('recipient')


class BranchDevice(models.Model):
    """
    نموذج لربط الأجهزة بالفروع - يسمح لأي موظف في الفرع باستخدام أجهزة ذلك الفرع
    """
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.CASCADE,
        related_name='devices',
        verbose_name=_('الفرع')
    )
    device_name = models.CharField(
        _('اسم الجهاز'),
        max_length=200,
        help_text=_('اسم تعريفي للجهاز (مثل: كمبيوتر الاستقبال 1)')
    )
    device_fingerprint = models.CharField(
        _('بصمة الجهاز'),
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_('معرف فريد للجهاز يتم توليده تلقائياً (اختياري)')
    )
    hardware_serial = models.CharField(
        _('الرقم التسلسلي للجهاز'),
        max_length=200,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_('الرقم التسلسلي للجهاز (Hardware UUID/Serial)')
    )
    ip_address = models.GenericIPAddressField(
        _('عنوان IP'),
        null=True,
        blank=True,
        help_text=_('آخر عنوان IP مستخدم')
    )
    user_agent = models.TextField(
        _('معلومات المتصفح'),
        blank=True,
        help_text=_('معلومات المتصفح والنظام')
    )
    is_active = models.BooleanField(
        _('نشط'),
        default=True,
        help_text=_('هل هذا الجهاز مفعل للاستخدام؟')
    )
    is_blocked = models.BooleanField(
        _('محظور'),
        default=False,
        help_text=_('هل هذا الجهاز محظور من الاستخدام؟ (الحظر أقوى من التعطيل)')
    )
    blocked_reason = models.TextField(
        _('سبب الحظر'),
        blank=True,
        help_text=_('سبب حظر هذا الجهاز')
    )
    blocked_at = models.DateTimeField(
        _('تاريخ الحظر'),
        null=True,
        blank=True
    )
    blocked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_devices',
        verbose_name=_('تم الحظر بواسطة')
    )
    created_at = models.DateTimeField(
        _('تاريخ التسجيل'),
        auto_now_add=True
    )
    first_used = models.DateTimeField(
        _('أول استخدام'),
        null=True,
        blank=True
    )
    last_used = models.DateTimeField(
        _('آخر استخدام'),
        null=True,
        blank=True
    )
    last_used_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_used_devices',
        verbose_name=_('آخر مستخدم')
    )
    users_logged = models.ManyToManyField(
        User,
        blank=True,
        related_name='devices_used',
        verbose_name=_('المستخدمون الذين سجلوا الدخول'),
        help_text=_('قائمة المستخدمين الذين استخدموا هذا الجهاز (بدون تكرار)')
    )
    notes = models.TextField(
        _('ملاحظات'),
        blank=True,
        help_text=_('ملاحظات إضافية عن الجهاز')
    )
    
    class Meta:
        verbose_name = _('جهاز الفرع')
        verbose_name_plural = _('أجهزة الفروع')
        ordering = ['branch', 'device_name']
        indexes = [
            models.Index(fields=['device_fingerprint']),
            models.Index(fields=['branch', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.device_name} - {self.branch.name}"
    
    def mark_used(self, user=None, ip_address=None):
        """تحديث معلومات آخر استخدام للجهاز"""
        now = timezone.now()
        if not self.first_used:
            self.first_used = now
        self.last_used = now
        if user:
            self.last_used_by = user
            # إضافة المستخدم إلى قائمة المستخدمين (بدون تكرار)
            if not self.users_logged.filter(id=user.id).exists():
                self.users_logged.add(user)
        if ip_address:
            self.ip_address = ip_address
        self.save(update_fields=['first_used', 'last_used', 'last_used_by', 'ip_address'])
    
    def is_authorized_for_user(self, user):
        """التحقق من صلاحية الجهاز للمستخدم - يسمح لأي موظف في نفس الفرع"""
        if not self.is_active:
            return False
        
        # السوبر يوزر والمدير العام يستطيعون الدخول من أي جهاز
        if user.is_superuser or user.is_general_manager:
            return True
        
        # التحقق من أن المستخدم ينتمي لنفس فرع الجهاز
        return user.branch == self.branch


class UnauthorizedDeviceAttempt(models.Model):
    """
    تسجيل محاولات الدخول الفاشلة - سواء بسبب الجهاز أو بيانات الدخول
    """
    DENIAL_REASON_CHOICES = [
        ('invalid_username', 'اسم مستخدم خاطئ'),
        ('invalid_password', 'كلمة مرور خاطئة'),
        ('device_not_registered', 'جهاز غير مسجل'),
        ('wrong_branch', 'جهاز مسجل لفرع آخر'),
        ('device_inactive', 'جهاز معطل'),
        ('device_blocked', 'جهاز محظور'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('المستخدم'),
        related_name='unauthorized_attempts',
        help_text=_('المستخدم الذي حاول الدخول (null إذا كان اسم المستخدم خاطئ)')
    )
    username_attempted = models.CharField(
        _('اسم المستخدم المحاول'),
        max_length=150,
        default='',
        help_text=_('اسم المستخدم الذي تم محاولة الدخول به')
    )
    attempted_at = models.DateTimeField(
        _('وقت المحاولة'),
        auto_now_add=True,
        db_index=True
    )
    device_fingerprint = models.CharField(
        _('بصمة الجهاز'),
        max_length=64,
        null=True,
        blank=True
    )
    hardware_serial = models.CharField(
        _('الرقم التسلسلي للجهاز'),
        max_length=200,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        _('عنوان IP'),
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        _('معلومات المتصفح'),
        blank=True
    )
    denial_reason = models.CharField(
        _('سبب الرفض'),
        max_length=50,
        choices=DENIAL_REASON_CHOICES,
        default='device_not_registered'
    )
    user_branch = models.ForeignKey(
        'Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('فرع المستخدم'),
        related_name='unauthorized_login_attempts'
    )
    device_branch = models.ForeignKey(
        'Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('فرع الجهاز'),
        related_name='device_unauthorized_attempts'
    )
    is_notified = models.BooleanField(
        _('تم الإشعار'),
        default=False,
        help_text=_('هل تم إرسال إشعار لمدير النظام؟')
    )
    
    class Meta:
        verbose_name = _('محاولة دخول غير مصرح بها')
        verbose_name_plural = _('محاولات الدخول غير المصرح بها')
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['-attempted_at']),
            models.Index(fields=['user', '-attempted_at']),
            models.Index(fields=['is_notified']),
        ]
    
    def __str__(self):
        username = self.username_attempted if self.username_attempted else (self.user.username if self.user else 'غير معروف')
        return f"{username} - {self.get_denial_reason_display()} - {self.attempted_at.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def log_attempt(cls, username_attempted, user=None, device_data=None, denial_reason='invalid_password', 
                    user_branch=None, device_branch=None, ip_address=None):
        """
        تسجيل محاولة دخول فاشلة
        
        Args:
            username_attempted: اسم المستخدم الذي تم محاولة الدخول به
            user: كائن المستخدم (None إذا كان اسم المستخدم خاطئ)
            device_data: بيانات الجهاز (fingerprint, hardware_serial, user_agent)
            denial_reason: سبب الرفض
            user_branch: فرع المستخدم
            device_branch: فرع الجهاز
            ip_address: عنوان IP
        """
        device_data = device_data or {}
        
        attempt = cls.objects.create(
            user=user,
            username_attempted=username_attempted,
            device_fingerprint=device_data.get('fingerprint'),
            hardware_serial=device_data.get('hardware_serial'),
            ip_address=ip_address,
            user_agent=device_data.get('user_agent', ''),
            denial_reason=denial_reason,
            user_branch=user_branch,
            device_branch=device_branch
        )
        return attempt


class YearFilterExemption(models.Model):
    """
    إعدادات استثناء الأقسام من فلتر السنة الافتراضية
    """
    SECTION_CHOICES = [
        ('customers', 'العملاء'),
        ('inspections', 'المعاينات'),
        ('inventory', 'المخزون'),
        ('reports', 'التقارير'),
        ('orders', 'الطلبات'),
        ('installations', 'التركيبات'),
        ('manufacturing', 'التصنيع'),
    ]

    section = models.CharField(_('القسم'), max_length=50, choices=SECTION_CHOICES, unique=True)
    is_exempt = models.BooleanField(_('معفى من فلتر السنة'), default=False)
    description = models.CharField(_('الوصف'), max_length=200, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('إعفاء قسم من فلتر السنة')
        verbose_name_plural = _('إعفاءات الأقسام من فلتر السنة')
        ordering = ['section']

    def __str__(self):
        status = 'معفى' if self.is_exempt else 'غير معفى'
        return f"{self.get_section_display()} - {status}"

    @classmethod
    def is_section_exempt(cls, section_name):
        """التحقق من إعفاء قسم معين من فلتر السنة"""
        try:
            exemption = cls.objects.get(section=section_name)
            return exemption.is_exempt
        except cls.DoesNotExist:
            # إذا لم يكن هناك إعداد، فالقسم غير معفى (يطبق الفلتر)
            return False

    @classmethod
    def get_exempt_sections(cls):
        """الحصول على قائمة الأقسام المعفاة من فلتر السنة"""
        return cls.objects.filter(is_exempt=True).values_list('section', flat=True)
















