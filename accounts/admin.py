from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import (
    User, CompanyInfo, Branch, Department, Salesperson,
    Role, UserRole, SystemSettings, BranchMessage, DashboardYearSettings,
    ActivityLog, Employee, FormField, ContactFormSettings, FooterSettings, AboutPageSettings,
    SimpleNotification, ComplaintNotification, GroupNotification
)
from .forms import THEME_CHOICES
from .widgets import ColorPickerWidget, IconPickerWidget, DurationRangeWidget
from manufacturing.models import ManufacturingOrder


class DepartmentFilter(admin.SimpleListFilter):
    title = _('Department')
    parameter_name = 'department'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            departments = Department.objects.filter(is_active=True)
        else:
            departments = request.user.departments.filter(is_active=True)

        return [(dept.id, dept.name) for dept in departments]

    def queryset(self, request, queryset):
        if self.value():
            if hasattr(queryset.model, 'departments'):
                return queryset.filter(departments__id=self.value())
            elif hasattr(queryset.model, 'department'):
                return queryset.filter(department__id=self.value())
            elif (hasattr(queryset.model, 'user') and
                  hasattr(
                      queryset.model.user.field.related_model, 'departments'
                  )):
                return queryset.filter(user__departments__id=self.value())
        return queryset


def add_manufacturing_approval_permission(modeladmin, request, queryset):
    """Grant manufacturing approval permission to selected users."""
    content_type = ContentType.objects.get_for_model(ManufacturingOrder)
    approve_permission, _ = Permission.objects.get_or_create(
        codename='can_approve_orders',
        content_type=content_type,
        defaults={'name': 'Can approve manufacturing orders'}
    )
    reject_permission, _ = Permission.objects.get_or_create(
        codename='can_reject_orders',
        content_type=content_type,
        defaults={'name': 'Can reject manufacturing orders'}
    )

    count = 0
    for user in queryset:
        if not user.user_permissions.filter(id=approve_permission.id).exists():
            user.user_permissions.add(approve_permission, reject_permission)
            count += 1

    messages.success(
        request,
        f'تم إعطاء صلاحيات الموافقة على التصنيع لـ {count} مستخدم'
    )


add_manufacturing_approval_permission.short_description = _(
    'إعطاء صلاحيات الموافقة على التصنيع'
)


def remove_manufacturing_approval_permission(modeladmin, request, queryset):
    """Remove manufacturing approval permission from selected users."""
    content_type = ContentType.objects.get_for_model(ManufacturingOrder)
    try:
        approve_permission = Permission.objects.get(
            codename='can_approve_orders',
            content_type=content_type
        )
        reject_permission = Permission.objects.get(
            codename='can_reject_orders',
            content_type=content_type
        )
    except Permission.DoesNotExist:
        messages.warning(request, "لم يتم العثور على صلاحيات التصنيع.")
        return

    count = 0
    for user in queryset:
        if user.user_permissions.filter(id=approve_permission.id).exists():
            user.user_permissions.remove(approve_permission, reject_permission)
            count += 1

    messages.success(
        request,
        f'تم إزالة صلاحيات الموافقة على التصنيع من {count} مستخدم'
    )


remove_manufacturing_approval_permission.short_description = _(
    'إزالة صلاحيات الموافقة على التصنيع'
)


class UserRoleInline(admin.TabularInline):
    """Manage user roles directly from the user page."""
    model = UserRole
    extra = 1
    verbose_name = _('دور المستخدم')
    verbose_name_plural = _('أدوار المستخدم')
    autocomplete_fields = ['role']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "role":
            kwargs["queryset"] = Role.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = (
        'username', 'email', 'branch', 'first_name', 'last_name', 'is_staff',
        'get_user_role_display', 'get_roles', 'has_manufacturing_approval'
    )
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'branch',
        'is_inspection_technician', 'is_salesperson', 'is_branch_manager', 
        'is_region_manager', 'is_general_manager', 'is_factory_manager',
        'is_inspection_manager', 'is_installation_manager', 'user_roles__role'
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    inlines = [UserRoleInline]
    actions = [
        add_manufacturing_approval_permission,
        remove_manufacturing_approval_permission
    ]

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('معلومات شخصية'), {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'image', 'branch',
                'departments', 'default_theme'
            )
        }),
        (_('الصلاحيات'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'is_inspection_technician', 'is_salesperson', 'is_branch_manager', 
                'is_region_manager', 'is_general_manager', 'is_factory_manager',
                'is_inspection_manager', 'is_installation_manager', 'managed_branches', 
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',),
            'description': _(
                'يمكنك إدارة أدوار المستخدم بشكل أسهل '
                'من خلال قسم "أدوار المستخدم" أدناه.'
            )
        }),
        (_('تواريخ مهمة'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2', 'first_name',
                'last_name', 'email', 'phone', 'image', 'branch',
                'departments', 'default_theme'
            ),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'default_theme' in form.base_fields:
            form.base_fields['default_theme'].widget = forms.Select(
                choices=THEME_CHOICES
            )
        return form

    def get_roles(self, obj):
        """Display user roles in the user list."""
        roles = obj.user_roles.all().select_related('role')
        if not roles:
            return "-"
        return ", ".join([role.role.name for role in roles])
    get_roles.short_description = _('الأدوار')

    def has_manufacturing_approval(self, obj):
        """Display if the user has manufacturing approval permission."""
        content_type = ContentType.objects.get_for_model(ManufacturingOrder)
        return obj.user_permissions.filter(
            codename='can_approve_orders',
            content_type=content_type
        ).exists()

    has_manufacturing_approval.boolean = True
    has_manufacturing_approval.short_description = _(
        'صلاحية الموافقة على التصنيع'
    )

    def get_inline_instances(self, request, obj=None):
        """Add a help message above the user roles section."""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add a link to the roles management page."""
        extra_context = extra_context or {}
        extra_context['show_roles_management'] = True
        extra_context['roles_list_url'] = '/admin/accounts/role/'
        extra_context['add_role_url'] = '/admin/accounts/role/add/'
        return super().change_view(
            request, object_id, form_url, extra_context
        )


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('name', 'phone', 'email', 'website')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': (
                'name', 'address', 'phone', 'email', 'website',
                'working_hours'
            )
        }),
        (_('لوغوهات النظام'), {
            'fields': (
                'logo', 'header_logo'
            ),
            'description': 'لوغو النظام: يستخدم في جميع أنحاء النظام | لوغو الهيدر: يستخدم في الهيدر فقط'
        }),
        (_('عن النظام'), {
            'fields': ('description',)
        }),
        (_('معلومات قانونية'), {
            'fields': ('tax_number', 'commercial_register')
        }),
        (_('وسائل التواصل الاجتماعي'), {
            'fields': (
                'facebook', 'twitter', 'instagram', 'linkedin', 'social_links'
            )
        }),
        (_('معلومات إضافية'), {
            'fields': ('about', 'vision', 'mission')
        }),
        (_('إعدادات النظام'), {
            'fields': (
                'primary_color', 'secondary_color', 'accent_color',
                'copyright_text'
            )
        }),
        (_('معلومات النظام - للعرض فقط'), {
            'fields': ('developer', 'version', 'release_date'),
            'classes': ('collapse',),
            'description': 'هذه المعلومات للعرض فقط ولا يمكن تعديلها إلا من قبل مطور النظام.'
        }),
    )

    readonly_fields = ('developer', 'version', 'release_date')
    
    def get_model_perms(self, request):
        """
        إظهار النموذج في قائمة لوحة التحكم مع إضافة رابط سريع
        """
        perms = super().get_model_perms(request)
        if request.user.is_superuser:
            perms['view'] = True
            perms['change'] = True
        return perms

    def has_add_permission(self, request):
        # السماح للموظفين بإضافة معلومات الشركة
        if request.user.is_staff:
            return True
        # Check if there's already an instance
        return not CompanyInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # السماح للموظفين بحذف معلومات الشركة
        return request.user.is_staff

    def changelist_view(self, request, extra_context=None):
        """
        إضافة رابط سريع لإعدادات الشركة في قائمة لوحة التحكم
        """
        extra_context = extra_context or {}
        extra_context['company_settings_url'] = reverse('accounts:company_info')
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        إضافة رابط سريع لإعدادات الشركة في صفحة التعديل
        """
        extra_context = extra_context or {}
        extra_context['company_settings_url'] = reverse('accounts:company_info')
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('code', 'name', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'phone', 'email')
    ordering = ['code']



@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('name', 'code', 'department_type', 'is_active', 'is_core', 'parent', 'manager')
    list_filter = (DepartmentFilter, 'department_type', 'is_active', 'is_core', 'parent')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('is_core',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter by departments that the user belongs to
        user_departments = request.user.departments.all()
        # Include departments and their child departments
        department_ids = set()
        for dept in user_departments:
            department_ids.add(dept.id)
            # Add children recursively
            children = Department.objects.filter(parent=dept)
            for child in children:
                department_ids.add(child.id)
        return qs.filter(id__in=department_ids)

    def has_delete_permission(self, request, obj=None):
        # السماح للموظفين بحذف جميع الأقسام (بما في ذلك الأساسية)
        if request.user.is_staff:
            return True  # صلاحيات كاملة للموظفين

        # للمستخدمين العاديين - منع الحذف
        return False

    def has_add_permission(self, request):
        # السماح للموظفين بإضافة أقسام جديدة
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        # السماح للموظفين بتعديل جميع الأقسام
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        # السماح للموظفين بعرض جميع الأقسام
        return request.user.is_staff

    def delete_model(self, request, obj):
        """حذف قسم واحد - صلاحيات كاملة"""
        from django.contrib import messages

        if obj.is_core:
            messages.warning(
                request,
                f"تم حذف القسم الأساسي: {obj.name} - تأكد من أن هذا ما تريده!"
            )

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """حذف مجموعة أقسام - صلاحيات كاملة"""
        from django.contrib import messages

        # عد الأقسام الأساسية وغير الأساسية
        core_departments = queryset.filter(is_core=True)
        non_core_departments = queryset.filter(is_core=False)
        total_count = queryset.count()

        if core_departments.exists():
            messages.warning(
                request,
                f"تحذير: سيتم حذف {core_departments.count()} قسم أساسي من أصل {total_count} قسم!"
            )

        # حذف جميع الأقسام المحددة
        queryset.delete()

        messages.success(
            request,
            f"تم حذف {total_count} قسم بنجاح (منها {core_departments.count()} أساسي و {non_core_departments.count()} غير أساسي)."
        )

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'code', 'department_type', 'description', 'is_active')
        }),
        (_('العلاقات'), {
            'fields': ('parent', 'manager')
        }),
        (_('خيارات إضافية'), {
            'fields': ('order', 'icon', 'url_name', 'has_pages'),
            'classes': ('collapse',),
        }),
        (_('معلومات النظام'), {
            'fields': ('is_core',),
            'classes': ('collapse',),
            'description': _('الأقسام الأساسية هي جزء من أساس التطبيق ولا يمكن حذفها أو تعديلها بشكل كامل.'),
        }),
    )
    autocomplete_fields = ['parent', 'manager']

@admin.register(Salesperson)
class SalespersonAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('name', 'employee_number', 'branch', 'is_active')
    list_filter = (DepartmentFilter, 'is_active', 'branch')
    search_fields = ('name', 'employee_number', 'phone', 'email')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'employee_number', 'branch', 'is_active')
        }),
        (_('معلومات الاتصال'), {
            'fields': ('phone', 'email', 'address')
        }),
        (_('معلومات إضافية'), {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter by branches that the user belongs to
        if request.user.branch:
            return qs.filter(branch=request.user.branch)
        return qs.none()

# تسجيل نموذج Role في الإدارة ولكن بدون إظهاره في القائمة الرئيسية
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_system_role', 'created_at', 'get_users_count')
    list_filter = ('is_system_role', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',)
    readonly_fields = ('created_at', 'updated_at')

    # إخفاء من القائمة الرئيسية
    def get_model_perms(self, request):
        """
        إخفاء النموذج من القائمة الرئيسية مع الاحتفاظ بإمكانية الوصول إليه
        """
        return {}

    fieldsets = (
        (_('معلومات الدور'), {
            'fields': ('name', 'description', 'is_system_role')
        }),
        (_('الصلاحيات'), {
            'fields': ('permissions',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(is_system_role=False)  # المستخدم العادي لا يمكنه رؤية أدوار النظام

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_system_role:
            return False  # لا يمكن حذف أدوار النظام
        return super().has_delete_permission(request, obj)

    def get_users_count(self, obj):
        return obj.user_roles.count()
    get_users_count.short_description = _('عدد المستخدمين')

# تسجيل نموذج Role في الإدارة
admin.site.register(Role, RoleAdmin)

# لا نحتاج إلى تسجيل UserRole كنموذج منفصل لأنه متاح الآن من خلال صفحة المستخدم

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('name', 'codename', 'content_type')
    list_filter = ('content_type__app_label',)
    search_fields = ('name', 'codename')
    readonly_fields = ('codename', 'content_type')

    fieldsets = (
        (_('معلومات الصلاحية'), {
            'fields': ('name', 'codename', 'content_type')
        }),
    )

    def has_add_permission(self, request):
        # السماح للموظفين بإضافة صلاحيات جديدة
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        # السماح للموظفين بحذف الصلاحيات
        return request.user.is_staff


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('name', 'currency', 'version')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('معلومات النظام'), {
            'fields': ('name', 'version')
        }),
        (_('إعدادات العملة'), {
            'fields': ('currency',),
            'description': _('تحديد العملة المستخدمة في النظام')
        }),
        (_('إعدادات العرض'), {
            'fields': ('items_per_page', 'low_stock_threshold')
        }),

        (_('إعدادات متقدمة'), {
            'fields': ('enable_analytics', 'maintenance_mode', 'maintenance_message'),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # السماح للموظفين بإضافة إعدادات النظام
        if request.user.is_staff:
            return True
        # Check if there's already an instance
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # السماح للموظفين بحذف إعدادات النظام
        return request.user.is_staff

@admin.register(BranchMessage)
class BranchMessageAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('title', 'branch', 'is_for_all_branches', 'message_type', 'display_style', 'display_duration', 'is_active', 'start_date', 'end_date', 'color_preview', 'icon_preview')
    list_filter = ('branch', 'is_for_all_branches', 'message_type', 'display_style', 'is_active', 'display_duration')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات الرسالة', {
            'fields': ('title', 'message', 'message_type')
        }),
        ('الاستهداف', {
            'fields': ('is_for_all_branches', 'branch'),
            'description': 'حدد إما فرع معين أو اختر "لجميع الفروع"'
        }),
        ('المظهر والعرض', {
            'fields': ('color', 'icon', 'icon_size', 'display_style'),
            'description': 'تحكم في مظهر ونمط عرض الرسالة'
        }),
        ('إعدادات العرض', {
            'fields': ('display_duration', 'auto_close', 'show_close_button', 'allow_outside_click'),
            'description': 'تحكم في سلوك عرض الرسالة'
        }),
        ('التوقيت', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # استخدام ColorPickerWidget للحقل color
        if 'color' in form.base_fields:
            form.base_fields['color'].widget = ColorPickerWidget()
            
        # استخدام IconPickerWidget للحقل icon
        if 'icon' in form.base_fields:
            form.base_fields['icon'].widget = IconPickerWidget()
            
        # استخدام DurationRangeWidget للحقل display_duration
        if 'display_duration' in form.base_fields:
            form.base_fields['display_duration'].widget = DurationRangeWidget()
            
        return form
    
    def color_preview(self, obj):
        """عرض معاينة اللون في قائمة الإدارة"""
        if obj.color:
            color_map = {
                'primary': '#007bff',
                'secondary': '#6c757d', 
                'success': '#28a745',
                'danger': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8',
                'light': '#f8f9fa',
                'dark': '#343a40'
            }
            
            color_value = color_map.get(obj.color, obj.color)
            text_color = '#333' if obj.color == 'light' else 'white'
            
            return mark_safe(f'''
                <div style="
                    background-color: {color_value}; 
                    color: {text_color}; 
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    font-size: 12px;
                    text-align: center;
                    min-width: 60px;
                ">
                    {obj.color}
                </div>
            ''')
        return '-'
    
    color_preview.short_description = 'معاينة اللون'
    
    def icon_preview(self, obj):
        """عرض معاينة الأيقونة في قائمة الإدارة"""
        if obj.icon:
            size_class = obj.get_icon_size_class() if hasattr(obj, 'get_icon_size_class') else 'fa-lg'
            return mark_safe(f'''
                <div style="text-align: center;">
                    <i class="{obj.icon} {size_class}" style="color: #333;"></i>
                    <br>
                    <small style="color: #666; font-size: 10px;">{obj.icon}</small>
                    <br>
                    <small style="color: #999; font-size: 9px;">({obj.icon_size if hasattr(obj, 'icon_size') else 'متوسط'})</small>
                </div>
            ''')
        return '-'
    
    icon_preview.short_description = 'معاينة الأيقونة'
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',)
        }

@admin.register(DashboardYearSettings)
class DashboardYearSettingsAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    """إدارة إعدادات السنوات في الداش بورد"""
    list_display = ('year', 'is_active', 'is_default', 'description', 'created_at')
    list_filter = ('is_active', 'is_default', 'created_at')
    search_fields = ('year', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-year',)
    
    fieldsets = (
        (_('معلومات السنة'), {
            'fields': ('year', 'description')
        }),
        (_('حالة السنة'), {
            'fields': ('is_active', 'is_default'),
            'description': _('يمكن تعيين سنة واحدة فقط كافتراضية')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_years', 'deactivate_years', 'set_as_default']
    
    def activate_years(self, request, queryset):
        """تفعيل السنوات المحددة"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'تم تفعيل {updated} سنة بنجاح')
    activate_years.short_description = 'تفعيل السنوات المحددة'
    
    def deactivate_years(self, request, queryset):
        """إلغاء تفعيل السنوات المحددة"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'تم إلغاء تفعيل {updated} سنة بنجاح')
    deactivate_years.short_description = 'إلغاء تفعيل السنوات المحددة'
    
    def set_as_default(self, request, queryset):
        """تعيين السنة المحددة كافتراضية"""
        if queryset.count() != 1:
            self.message_user(request, 'يرجى تحديد سنة واحدة فقط', level='ERROR')
            return
        
        year = queryset.first()
        year.is_default = True
        year.save()
        self.message_user(request, f'تم تعيين سنة {year.year} كافتراضية بنجاح')
    set_as_default.short_description = 'تعيين كافتراضية'
    
    def has_delete_permission(self, request, obj=None):
        """منع حذف السنة الافتراضية"""
        if obj and obj.is_default:
            return False
        return super().has_delete_permission(request, obj)


# ==================== 🎨 إدارة نظام الإشعارات البسيط والجميل ====================

@admin.register(SimpleNotification)
class SimpleNotificationAdmin(admin.ModelAdmin):
    """إدارة الإشعارات البسيطة"""

    list_display = [
        'notification_icon',
        'title',
        'customer_name',
        'order_number',
        'status',
        'notification_type',
        'priority_badge',
        'recipient',
        'is_read_badge',
        'created_at'
    ]

    list_filter = [
        'notification_type',
        'priority',
        'is_read',
        'created_at',
        'recipient__username',
        'recipient__is_superuser',
        'recipient__is_staff',
    ]

    search_fields = [
        'title',
        'customer_name',
        'order_number',
        'recipient__username',
        'recipient__first_name',
        'recipient__last_name'
    ]

    readonly_fields = [
        'created_at',
        'read_at',
        'content_type',
        'object_id'
    ]

    fieldsets = (
        ('📋 معلومات الإشعار', {
            'fields': (
                'title',
                'customer_name',
                'order_number',
                'status'
            )
        }),
        ('🎯 تصنيف الإشعار', {
            'fields': (
                'notification_type',
                'priority',
                'recipient'
            )
        }),
        ('📖 حالة القراءة', {
            'fields': (
                'is_read',
                'read_at'
            )
        }),
        ('🔗 الربط', {
            'fields': (
                'content_type',
                'object_id'
            ),
            'classes': ('collapse',)
        }),
        ('📅 التواريخ', {
            'fields': (
                'created_at',
            ),
            'classes': ('collapse',)
        })
    )

    actions = ['mark_as_read', 'mark_as_unread', 'delete_selected', 'delete_old_notifications', 'mark_all_as_read', 'delete_all_notifications']

    # إعدادات العرض
    list_per_page = 50  # عرض 50 إشعار في الصفحة
    list_max_show_all = 200  # إمكانية عرض 200 إشعار في صفحة واحدة
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    show_full_result_count = True  # عرض العدد الكامل

    def notification_icon(self, obj):
        """عرض أيقونة الإشعار"""
        return mark_safe(f'<span style="font-size: 20px;">{obj.get_icon()}</span>')
    notification_icon.short_description = '🔔'

    def priority_badge(self, obj):
        """عرض شارة الأولوية"""
        colors = {
            'low': '#28a745',
            'normal': '#17a2b8',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return mark_safe(
            f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;">{obj.get_priority_display()}</span>'
        )
    priority_badge.short_description = 'الأولوية'

    def is_read_badge(self, obj):
        """عرض حالة القراءة"""
        if obj.is_read:
            return mark_safe('<span style="color: #28a745; font-weight: bold;">✅ مقروء</span>')
        else:
            return mark_safe('<span style="color: #dc3545; font-weight: bold;">🔴 غير مقروء</span>')
    is_read_badge.short_description = 'حالة القراءة'

    def mark_as_read(self, request, queryset):
        """تحديد كمقروء"""
        from django.utils import timezone
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(
            request,
            f'تم تحديد {updated} إشعار كمقروء',
            messages.SUCCESS
        )
    mark_as_read.short_description = 'تحديد كمقروء'

    def mark_as_unread(self, request, queryset):
        """تحديد كغير مقروء"""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(
            request,
            f'تم تحديد {updated} إشعار كغير مقروء',
            messages.SUCCESS
        )
    mark_as_unread.short_description = 'تحديد كغير مقروء'

    def delete_old_notifications(self, request, queryset):
        """حذف الإشعارات القديمة (أكثر من 30 يوم)"""
        from django.utils import timezone
        from datetime import timedelta

        thirty_days_ago = timezone.now() - timedelta(days=30)
        old_notifications = SimpleNotification.objects.filter(created_at__lt=thirty_days_ago)
        count = old_notifications.count()
        old_notifications.delete()

        self.message_user(
            request,
            f'تم حذف {count} إشعار قديم (أكثر من 30 يوم)',
            messages.SUCCESS
        )
    delete_old_notifications.short_description = 'حذف الإشعارات القديمة (30+ يوم)'

    def mark_all_as_read(self, request, queryset):
        """تحديد جميع الإشعارات كمقروءة"""
        from django.utils import timezone

        updated = SimpleNotification.objects.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )

        self.message_user(
            request,
            f'تم تحديد جميع الإشعارات ({updated}) كمقروءة',
            messages.SUCCESS
        )
    mark_all_as_read.short_description = 'تحديد جميع الإشعارات كمقروءة'

    def delete_all_notifications(self, request, queryset):
        """حذف جميع الإشعارات البسيطة"""
        if request.user.is_superuser:
            total_count = SimpleNotification.objects.count()
            SimpleNotification.objects.all().delete()

            self.message_user(
                request,
                f'تم حذف جميع الإشعارات البسيطة ({total_count}) بنجاح',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'يجب أن تكون مدير نظام لتنفيذ هذا الإجراء',
                messages.ERROR
            )
    delete_all_notifications.short_description = '🗑️ حذف جميع الإشعارات (مديرين فقط)'

    def get_queryset(self, request):
        """تحسين الاستعلامات"""
        return super().get_queryset(request).select_related(
            'recipient',
            'content_type'
        )

    def changelist_view(self, request, extra_context=None):
        """إضافة إحصائيات الإشعارات إلى صفحة القائمة"""
        extra_context = extra_context or {}

        # إحصائيات الإشعارات
        total_notifications = SimpleNotification.objects.count()
        unread_notifications = SimpleNotification.objects.filter(is_read=False).count()
        urgent_notifications = SimpleNotification.objects.filter(
            is_read=False,
            priority='urgent'
        ).count()
        high_notifications = SimpleNotification.objects.filter(
            is_read=False,
            priority='high'
        ).count()

        extra_context['notifications_stats'] = {
            'total': total_notifications,
            'unread': unread_notifications,
            'urgent': urgent_notifications,
            'high': high_notifications,
        }

        # إذا طلب المستخدم عرض الكل
        if request.GET.get('all') == '1':
            self.list_per_page = total_notifications if total_notifications > 0 else 1
            extra_context['showing_all'] = True
        else:
            self.list_per_page = 50  # العودة للقيمة الافتراضية
            extra_context['showing_all'] = False

        return super().changelist_view(request, extra_context)


@admin.register(ComplaintNotification)
class ComplaintNotificationAdmin(admin.ModelAdmin):
    """إدارة إشعارات الشكاوى"""

    list_display = [
        'complaint_icon',
        'title',
        'customer_name',
        'complaint_number',
        'complaint_type',
        'priority_badge',
        'recipient',
        'is_read_badge',
        'created_at'
    ]

    list_filter = [
        'complaint_type',
        'priority',
        'is_read',
        'created_at',
        'recipient__departments'
    ]

    search_fields = [
        'title',
        'customer_name',
        'complaint_number',
        'recipient__username',
        'recipient__first_name',
        'recipient__last_name'
    ]

    readonly_fields = [
        'created_at',
        'read_at',
        'content_type',
        'object_id'
    ]

    fieldsets = (
        ('📢 معلومات الشكوى', {
            'fields': (
                'title',
                'customer_name',
                'complaint_number'
            )
        }),
        ('🎯 تصنيف الشكوى', {
            'fields': (
                'complaint_type',
                'priority',
                'recipient'
            )
        }),
        ('📖 حالة القراءة', {
            'fields': (
                'is_read',
                'read_at'
            )
        }),
        ('🔗 الربط', {
            'fields': (
                'content_type',
                'object_id'
            ),
            'classes': ('collapse',)
        }),
        ('📅 التواريخ', {
            'fields': (
                'created_at',
            ),
            'classes': ('collapse',)
        })
    )

    actions = ['mark_as_read', 'mark_as_unread', 'delete_selected']

    def complaint_icon(self, obj):
        """عرض أيقونة الشكوى"""
        return mark_safe(f'<span style="font-size: 20px;">{obj.get_icon()}</span>')
    complaint_icon.short_description = '📢'

    def priority_badge(self, obj):
        """عرض شارة الأولوية"""
        colors = {
            'low': '#28a745',
            'medium': '#17a2b8',
            'high': '#ffc107',
            'critical': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return mark_safe(
            f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;">{obj.get_priority_display()}</span>'
        )
    priority_badge.short_description = 'الأولوية'

    def is_read_badge(self, obj):
        """عرض حالة القراءة"""
        if obj.is_read:
            return mark_safe('<span style="color: #28a745; font-weight: bold;">✅ مقروء</span>')
        else:
            return mark_safe('<span style="color: #dc3545; font-weight: bold;">🔴 غير مقروء</span>')
    is_read_badge.short_description = 'حالة القراءة'

    def mark_as_read(self, request, queryset):
        """تحديد كمقروء"""
        from django.utils import timezone
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(
            request,
            f'تم تحديد {updated} إشعار كمقروء',
            messages.SUCCESS
        )
    mark_as_read.short_description = 'تحديد كمقروء'

    def mark_as_unread(self, request, queryset):
        """تحديد كغير مقروء"""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(
            request,
            f'تم تحديد {updated} إشعار كغير مقروء',
            messages.SUCCESS
        )
    mark_as_unread.short_description = 'تحديد كغير مقروء'

    def get_queryset(self, request):
        """تحسين الاستعلامات"""
        return super().get_queryset(request).select_related(
            'recipient',
            'content_type'
        )


@admin.register(GroupNotification)
class GroupNotificationAdmin(admin.ModelAdmin):
    """إدارة الإشعارات الجماعية - هذه هي الإشعارات الظاهرة في الواجهة """

    list_display = [
        'notification_icon',
        'title',
        'customer_name',
        'order_number',
        'notification_type',
        'priority_badge',
        'target_users_count',
        'read_count',
        'created_at'
    ]

    list_filter = [
        'notification_type',
        'priority',
        'created_at',
        'target_users',
    ]

    search_fields = [
        'title',
        'customer_name',
        'order_number',
        'target_users__username',
        'target_users__first_name',
        'target_users__last_name'
    ]

    readonly_fields = [
        'created_at',
        'related_object_id',
        'related_object_type'
    ]

    filter_horizontal = ['target_users']

    actions = ['delete_selected', 'delete_old_notifications', 'mark_all_as_read', 'delete_all_notifications']

    # إعدادات العرض
    list_per_page = 50
    list_max_show_all = 200
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    show_full_result_count = True

    def notification_icon(self, obj):
        """عرض أيقونة الإشعار"""
        return mark_safe(f'<span style="font-size: 20px;">{obj.get_icon()}</span>')
    notification_icon.short_description = '🔔'

    def priority_badge(self, obj):
        """عرض شارة الأولوية"""
        colors = {
            'low': '#28a745',
            'normal': '#17a2b8',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return mark_safe(
            f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;">{obj.get_priority_display()}</span>'
        )
    priority_badge.short_description = 'الأولوية'

    def target_users_count(self, obj):
        """عدد المستخدمين المستهدفين"""
        count = obj.target_users.count()
        return mark_safe(f'<span style="background: #007bff; color: white; padding: 2px 6px; border-radius: 8px; font-size: 11px;">{count} مستخدم</span>')
    target_users_count.short_description = 'المستهدفين'

    def read_count(self, obj):
        """عدد المستخدمين الذين قرأوا الإشعار"""
        read_count = obj.get_read_count()
        total_count = obj.target_users.count()
        percentage = (read_count / total_count * 100) if total_count > 0 else 0

        color = '#28a745' if percentage > 50 else '#ffc107' if percentage > 0 else '#dc3545'
        return mark_safe(
            f'<span style="background: {color}; color: white; padding: 2px 6px; border-radius: 8px; font-size: 11px;">{read_count}/{total_count} ({percentage:.0f}%)</span>'
        )
    read_count.short_description = 'معدل القراءة'

    def delete_old_notifications(self, request, queryset):
        """حذف الإشعارات القديمة (أكثر من 30 يوم)"""
        from django.utils import timezone
        from datetime import timedelta

        thirty_days_ago = timezone.now() - timedelta(days=30)
        old_notifications = GroupNotification.objects.filter(created_at__lt=thirty_days_ago)
        count = old_notifications.count()
        old_notifications.delete()

        self.message_user(
            request,
            f'تم حذف {count} إشعار جماعي قديم (أكثر من 30 يوم)',
            messages.SUCCESS
        )
    delete_old_notifications.short_description = 'حذف الإشعارات القديمة (30+ يوم)'

    def mark_all_as_read(self, request, queryset):
        """تحديد جميع الإشعارات كمقروءة للمستخدم الحالي"""
        from accounts.models import GroupNotificationRead
        from django.utils import timezone

        count = 0
        for notification in GroupNotification.objects.all():
            read_obj, created = GroupNotificationRead.objects.get_or_create(
                notification=notification,
                user=request.user,
                defaults={'read_at': timezone.now()}
            )
            if created:
                count += 1

        self.message_user(
            request,
            f'تم تحديد {count} إشعار جماعي كمقروء للمستخدم {request.user.username}',
            messages.SUCCESS
        )
    mark_all_as_read.short_description = 'تحديد جميع الإشعارات كمقروءة لي'

    def delete_all_notifications(self, request, queryset):
        """حذف جميع الإشعارات الجماعية"""
        if request.user.is_superuser:
            total_count = GroupNotification.objects.count()
            GroupNotification.objects.all().delete()

            self.message_user(
                request,
                f'تم حذف جميع الإشعارات الجماعية ({total_count}) بنجاح',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'يجب أن تكون مدير نظام لتنفيذ هذا الإجراء',
                messages.ERROR
            )
    delete_all_notifications.short_description = '🗑️ حذف جميع الإشعارات الجماعية (مديرين فقط)'

    def changelist_view(self, request, extra_context=None):
        """إضافة إحصائيات الإشعارات الجماعية إلى صفحة القائمة"""
        extra_context = extra_context or {}

        # إحصائيات الإشعارات الجماعية
        total_notifications = GroupNotification.objects.count()
        user_notifications = GroupNotification.objects.filter(target_users=request.user).count()
        urgent_notifications = GroupNotification.objects.filter(
            target_users=request.user,
            priority='urgent'
        ).count()
        high_notifications = GroupNotification.objects.filter(
            target_users=request.user,
            priority='high'
        ).count()

        # حساب الإشعارات غير المقروءة للمستخدم الحالي
        unread_count = 0
        for notification in GroupNotification.objects.filter(target_users=request.user):
            if not notification.is_read_by_user(request.user):
                unread_count += 1

        extra_context['notifications_stats'] = {
            'total': total_notifications,
            'user_total': user_notifications,
            'unread': unread_count,
            'urgent': urgent_notifications,
            'high': high_notifications,
        }

        # إذا طلب المستخدم عرض الكل
        if request.GET.get('all') == '1':
            self.list_per_page = total_notifications if total_notifications > 0 else 1
            extra_context['showing_all'] = True
        else:
            self.list_per_page = 50
            extra_context['showing_all'] = False

        return super().changelist_view(request, extra_context)

    def get_queryset(self, request):
        """تحسين الاستعلامات"""
        return super().get_queryset(request).prefetch_related(
            'target_users',
            'created_by'
        )