from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django import forms
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import (
    User, CompanyInfo, Branch, Notification, Department, Salesperson,
    Role, UserRole, SystemSettings, BranchMessage, UnifiedSystemSettings
)
from .forms import THEME_CHOICES
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
    list_display = (
        'username', 'email', 'branch', 'first_name', 'last_name', 'is_staff',
        'is_inspection_technician', 'get_roles', 'has_manufacturing_approval'
    )
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'branch',
        'is_inspection_technician', 'user_roles__role'
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
                'is_inspection_technician', 'groups', 'user_permissions'
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
                'username', 'password', 'password2', 'first_name',
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


@admin.register(UnifiedSystemSettings)
class UnifiedSystemSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات النظام الموحدة"""
    list_display = ('company_name', 'company_phone', 'company_email', 'system_version', 'currency', 'created_at')
    list_filter = ('currency', 'enable_notifications', 'enable_analytics', 'maintenance_mode', 'created_at')
    search_fields = ('company_name', 'company_phone', 'company_email', 'company_address')
    readonly_fields = ('created_at', 'updated_at', 'system_version', 'system_release_date', 'system_developer')
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('معلومات الشركة الأساسية'), {
            'fields': (
                'company_name', 'company_logo', 'company_address', 
                'company_phone', 'company_email', 'company_website',
                'working_hours'
            )
        }),
        (_('معلومات الشركة الإضافية'), {
            'fields': (
                'about_text', 'vision_text', 'mission_text', 'description',
                'tax_number', 'commercial_register'
            )
        }),
        (_('وسائل التواصل الاجتماعي'), {
            'fields': (
                'facebook_url', 'twitter_url', 'instagram_url', 
                'linkedin_url', 'social_links'
            )
        }),
        (_('إعدادات النظام الأساسية'), {
            'fields': (
                'currency', 'enable_notifications', 'enable_email_notifications',
                'items_per_page', 'low_stock_threshold', 'enable_analytics'
            )
        }),
        (_('إعدادات الواجهة'), {
            'fields': (
                'primary_color', 'secondary_color', 'accent_color',
                'default_theme', 'copyright_text'
            )
        }),
        (_('إعدادات متقدمة'), {
            'fields': (
                'maintenance_mode', 'maintenance_message'
            ),
            'classes': ('collapse',),
        }),
        (_('معلومات النظام - للعرض فقط'), {
            'fields': ('system_version', 'system_release_date', 'system_developer', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'هذه المعلومات للعرض فقط ولا يمكن تعديلها.'
        }),
    )

    def has_add_permission(self, request):
        # السماح بإضافة إعدادات جديدة
        return True

    def has_delete_permission(self, request, obj=None):
        # السماح بحذف إعدادات النظام
        return True

    def has_change_permission(self, request, obj=None):
        # السماح بتعديل إعدادات النظام
        return True

    def duplicate_settings(self, request, queryset):
        """تكرار الإعدادات المحددة"""
        count = 0
        for settings in queryset:
            # إنشاء نسخة جديدة
            new_settings = UnifiedSystemSettings.objects.create(
                company_name=f"{settings.company_name} - نسخة",
                company_logo=settings.company_logo,
                company_address=settings.company_address,
                company_phone=settings.company_phone,
                company_email=settings.company_email,
                company_website=settings.company_website,
                working_hours=settings.working_hours,
                about_text=settings.about_text,
                vision_text=settings.vision_text,
                mission_text=settings.mission_text,
                description=settings.description,
                tax_number=settings.tax_number,
                commercial_register=settings.commercial_register,
                facebook_url=settings.facebook_url,
                twitter_url=settings.twitter_url,
                instagram_url=settings.instagram_url,
                linkedin_url=settings.linkedin_url,
                social_links=settings.social_links,
                currency=settings.currency,
                enable_notifications=settings.enable_notifications,
                enable_email_notifications=settings.enable_email_notifications,
                items_per_page=settings.items_per_page,
                low_stock_threshold=settings.low_stock_threshold,
                enable_analytics=settings.enable_analytics,
                primary_color=settings.primary_color,
                secondary_color=settings.secondary_color,
                accent_color=settings.accent_color,
                default_theme=settings.default_theme,
                copyright_text=settings.copyright_text,
                maintenance_mode=settings.maintenance_mode,
                maintenance_message=settings.maintenance_message
            )
            count += 1
        
        self.message_user(
            request, 
            f'تم تكرار {count} إعدادات بنجاح'
        )
    duplicate_settings.short_description = _('تكرار الإعدادات المحددة')

    def reset_to_defaults(self, request, queryset):
        """إعادة تعيين الإعدادات إلى القيم الافتراضية"""
        count = 0
        for settings in queryset:
            settings.company_name = 'Elkhawaga'
            settings.company_phone = ''
            settings.company_email = ''
            settings.company_website = ''
            settings.working_hours = ''
            settings.about_text = ''
            settings.vision_text = ''
            settings.mission_text = ''
            settings.description = ''
            settings.tax_number = ''
            settings.commercial_register = ''
            settings.facebook_url = ''
            settings.twitter_url = ''
            settings.instagram_url = ''
            settings.linkedin_url = ''
            settings.social_links = None
            settings.currency = 'SAR'
            settings.enable_notifications = True
            settings.enable_email_notifications = False
            settings.items_per_page = 20
            settings.low_stock_threshold = 20
            settings.enable_analytics = True
            settings.primary_color = ''
            settings.secondary_color = ''
            settings.accent_color = ''
            settings.default_theme = 'default'
            settings.copyright_text = 'جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi'
            settings.maintenance_mode = False
            settings.maintenance_message = ''
            settings.save()
            count += 1
        
        self.message_user(
            request, 
            f'تم إعادة تعيين {count} إعدادات إلى القيم الافتراضية'
        )
    reset_to_defaults.short_description = _('إعادة تعيين إلى القيم الافتراضية')

    def export_settings(self, request, queryset):
        """تصدير الإعدادات المحددة"""
        from django.http import JsonResponse
        import json
        
        data = []
        for settings in queryset:
            data.append({
                'id': settings.id,
                'company_name': settings.company_name,
                'company_phone': settings.company_phone,
                'company_email': settings.company_email,
                'currency': settings.currency,
                'created_at': settings.created_at.isoformat(),
                'updated_at': settings.updated_at.isoformat()
            })
        
        response = JsonResponse(data, safe=False)
        response['Content-Disposition'] = 'attachment; filename="settings_export.json"'
        return response
    export_settings.short_description = _('تصدير الإعدادات المحددة')

    actions = ['duplicate_settings', 'reset_to_defaults', 'export_settings']

# إزالة النماذج القديمة من الإدارة
# @admin.register(CompanyInfo)
# class CompanyInfoAdmin(admin.ModelAdmin):
#     # تم إزالة هذا النموذج من الإدارة
#     pass

# @admin.register(SystemSettings)
# class SystemSettingsAdmin(admin.ModelAdmin):
#     # تم إزالة هذا النموذج من الإدارة
#     pass

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'phone', 'email')
    ordering = ['code']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """إدارة الإشعارات المحسنة"""
    list_display = [
        'title', 'notification_type', 'priority', 'sender', 
        'is_read', 'is_sent', 'created_at'
    ]
    list_filter = [
        'notification_type', 'priority', 'is_read', 'is_sent', 
        'is_archived', 'created_at', 'target_departments', 'target_branches'
    ]
    search_fields = ['title', 'message', 'sender__username', 'recipients__username']
    readonly_fields = [
        'created_at', 'sent_at', 'read_at', 'is_sent', 'is_read'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        (_('معلومات الإشعار'), {
            'fields': ('title', 'message', 'notification_type', 'priority')
        }),
        (_('المستلمون'), {
            'fields': ('recipients', 'target_departments', 'target_branches')
        }),
        (_('الكائن المرتبط'), {
            'fields': ('content_type', 'object_id', 'action_url'),
            'classes': ('collapse',)
        }),
        (_('حالة الإشعار'), {
            'fields': ('is_read', 'is_sent', 'is_archived', 'requires_action')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'sent_at', 'read_at'),
            'classes': ('collapse',)
        }),
        (_('إعدادات إضافية'), {
            'fields': ('auto_delete_after_days',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'sender', 'content_type'
        ).prefetch_related(
            'recipients', 'target_departments', 'target_branches'
        )
    
    def mark_as_sent(self, request, queryset):
        """تحديد الإشعارات كمرسلة"""
        updated = queryset.update(is_sent=True, sent_at=timezone.now())
        self.message_user(
            request, 
            f'تم تحديث {updated} إشعار كمرسل'
        )
    mark_as_sent.short_description = _('تحديد كمرسل')
    
    def mark_as_read(self, request, queryset):
        """تحديد الإشعارات كمقروءة"""
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(
            request, 
            f'تم تحديث {updated} إشعار كمقروء'
        )
    mark_as_read.short_description = _('تحديد كمقروء')
    
    def archive_notifications(self, request, queryset):
        """أرشفة الإشعارات المحددة"""
        updated = queryset.update(is_archived=True)
        self.message_user(
            request, 
            f'تم أرشفة {updated} إشعار'
        )
    archive_notifications.short_description = _('أرشفة الإشعارات')
    
    actions = [mark_as_sent, mark_as_read, archive_notifications]

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
