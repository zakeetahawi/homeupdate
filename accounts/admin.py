from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django import forms
from django.urls import path
from django.utils.html import format_html
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import (
    User, CompanyInfo, Branch, Notification, Department, Salesperson,
    Role, UserRole, SystemSettings, BranchMessage
)

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
            elif hasattr(queryset.model, 'user') and hasattr(queryset.model.user.field.related_model, 'departments'):
                return queryset.filter(user__departments__id=self.value())
        return queryset


class UserRoleInline(admin.TabularInline):
    """إدارة أدوار المستخدم مباشرة من صفحة المستخدم"""
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
    list_display = ('username', 'email', 'branch', 'first_name', 'last_name', 'is_staff', 'is_inspection_technician', 'get_roles')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'branch', 'is_inspection_technician', 'user_roles__role')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    inlines = [UserRoleInline]

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('معلومات شخصية'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'image', 'branch', 'departments')}),
        (_('الصلاحيات'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_inspection_technician', 'groups', 'user_permissions'),
            'classes': ('collapse',),
            'description': _('يمكنك إدارة أدوار المستخدم بشكل أسهل من خلال قسم "أدوار المستخدم" أدناه.')
        }),
        (_('تواريخ مهمة'), {'fields': ('last_login', 'date_joined')}),
    )

    def get_roles(self, obj):
        """عرض أدوار المستخدم في قائمة المستخدمين"""
        roles = obj.user_roles.all().select_related('role')
        if not roles:
            return "-"
        return ", ".join([role.role.name for role in roles])
    get_roles.short_description = _('الأدوار')

    def get_inline_instances(self, request, obj=None):
        """إضافة رسالة توضيحية فوق قسم أدوار المستخدم"""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """إضافة رابط لإدارة الأدوار من صفحة المستخدم"""
        extra_context = extra_context or {}
        extra_context['show_roles_management'] = True
        extra_context['roles_list_url'] = '/admin/accounts/role/'
        extra_context['add_role_url'] = '/admin/accounts/role/add/'
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'website')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'logo', 'address', 'phone', 'email', 'website', 'working_hours')
        }),
        (_('عن النظام'), {
            'fields': ('description',)
        }),
        (_('معلومات قانونية'), {
            'fields': ('tax_number', 'commercial_register')
        }),
        (_('وسائل التواصل الاجتماعي'), {
            'fields': ('facebook', 'twitter', 'instagram', 'linkedin', 'social_links')
        }),
        (_('معلومات إضافية'), {
            'fields': ('about', 'vision', 'mission')
        }),
        (_('إعدادات النظام'), {
            'fields': ('primary_color', 'secondary_color', 'accent_color', 'copyright_text')
        }),
        (_('معلومات النظام - للعرض فقط'), {
            'fields': ('developer', 'version', 'release_date'),
            'classes': ('collapse',),
            'description': 'هذه المعلومات للعرض فقط ولا يمكن تعديلها إلا من قبل مطور النظام.'
        }),
    )

    readonly_fields = ('developer', 'version', 'release_date')

    def has_add_permission(self, request):
        # السماح للموظفين بإضافة معلومات الشركة
        if request.user.is_staff:
            return True
        # Check if there's already an instance
        return not CompanyInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # السماح للموظفين بحذف معلومات الشركة
        return request.user.is_staff

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'phone', 'email')
    ordering = ['code']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'sender', 'sender_department', 'target_department', 'priority', 'created_at', 'is_read')
    list_filter = ('is_read', 'priority', 'sender_department', 'target_department', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'updated_at', 'read_at', 'read_by')
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('title', 'message', 'priority')
        }),
        (_('معلومات المرسل'), {
            'fields': ('sender', 'sender_department')
        }),
        (_('معلومات المستلم'), {
            'fields': ('target_department', 'target_branch')
        }),
        (_('الكائن المرتبط'), {
            'fields': ('content_type', 'object_id')
        }),
        (_('حالة الإشعار'), {
            'fields': ('is_read', 'read_at', 'read_by')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
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
        (_('إعدادات الإشعارات'), {
            'fields': ('enable_notifications', 'enable_email_notifications')
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
    list_display = ('title', 'branch', 'message_type', 'is_active', 'start_date', 'end_date')
    list_filter = ('branch', 'message_type', 'is_active')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('معلومات الرسالة', {
            'fields': ('branch', 'title', 'message', 'message_type')
        }),
        ('المظهر', {
            'fields': ('color', 'icon')
        }),
        ('التوقيت', {
            'fields': ('start_date', 'end_date', 'is_active')
        })
    )
