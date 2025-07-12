"""
تحسينات استعلامات Admin
يوفر هذا الملف تحسينات لاستعلامات Admin لتحسين الأداء
"""

from django.contrib import admin
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from .models import User, Department, Notification, UnifiedSystemSettings


class OptimizedUserAdmin(admin.ModelAdmin):
    """
    إدارة المستخدمين المحسنة مع استعلامات محسنة
    """
    
    def get_queryset(self, request):
        """
        تحسين استعلام المستخدمين مع تحميل البيانات المرتبطة مسبقاً
        """
        return super().get_queryset(request).select_related(
            'branch'
        ).prefetch_related(
            'departments',
            'user_roles__role',
            'groups',
            'user_permissions'
        )
    
    def get_context_data(self, request, extra_context=None):
        """
        إضافة إحصائيات محسنة للسياق
        """
        context = super().get_context_data(request, extra_context)
        context['user_statistics'] = self.get_user_statistics()
        return context
    
    def get_user_statistics(self):
        """
        الحصول على إحصائيات المستخدمين
        """
        queryset = self.get_queryset(None)
        
        return {
            'total_users': queryset.count(),
            'active_users': queryset.filter(is_active=True).count(),
            'staff_users': queryset.filter(is_staff=True).count(),
            'superusers': queryset.filter(is_superuser=True).count(),
            'users_by_branch': queryset.values('branch__name').annotate(
                count=Count('id')
            ).order_by('-count')[:5],
            'recent_users': queryset.order_by('-date_joined')[:10]
        }


class OptimizedDepartmentAdmin(admin.ModelAdmin):
    """
    إدارة الأقسام المحسنة
    """
    
    def get_queryset(self, request):
        """
        تحسين استعلام الأقسام
        """
        return super().get_queryset(request).select_related(
            'parent', 'manager'
        ).prefetch_related(
            'children',
            'users',
            'managed_departments'
        )
    
    def get_context_data(self, request, extra_context=None):
        """
        إضافة إحصائيات الأقسام
        """
        context = super().get_context_data(request, extra_context)
        context['department_statistics'] = self.get_department_statistics()
        return context
    
    def get_department_statistics(self):
        """
        الحصول على إحصائيات الأقسام
        """
        queryset = self.get_queryset(None)
        
        return {
            'total_departments': queryset.count(),
            'active_departments': queryset.filter(is_active=True).count(),
            'core_departments': queryset.filter(is_core=True).count(),
            'departments_by_type': queryset.values('department_type').annotate(
                count=Count('id')
            ),
            'departments_with_managers': queryset.filter(manager__isnull=False).count()
        }


class OptimizedNotificationAdmin(admin.ModelAdmin):
    """
    إدارة الإشعارات المحسنة
    """
    
    def get_queryset(self, request):
        """
        تحسين استعلام الإشعارات
        """
        return super().get_queryset(request).select_related(
            'sender',
            'sender_department',
            'target_department',
            'target_branch',
            'read_by'
        ).prefetch_related(
            'target_users'
        )
    
    def get_context_data(self, request, extra_context=None):
        """
        إضافة إحصائيات الإشعارات
        """
        context = super().get_context_data(request, extra_context)
        context['notification_statistics'] = self.get_notification_statistics()
        return context
    
    def get_notification_statistics(self):
        """
        الحصول على إحصائيات الإشعارات
        """
        queryset = self.get_queryset(None)
        
        return {
            'total_notifications': queryset.count(),
            'unread_notifications': queryset.filter(is_read=False).count(),
            'high_priority_notifications': queryset.filter(priority='high').count(),
            'notifications_by_priority': queryset.values('priority').annotate(
                count=Count('id')
            ),
            'recent_notifications': queryset.order_by('-created_at')[:10]
        }


class OptimizedUnifiedSystemSettingsAdmin(admin.ModelAdmin):
    """
    إدارة إعدادات النظام الموحدة
    """
    
    list_display = ('company_name', 'currency', 'enable_notifications', 'maintenance_mode')
    list_filter = ('enable_notifications', 'enable_analytics', 'maintenance_mode')
    readonly_fields = ('system_version', 'system_release_date', 'system_developer', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('معلومات الشركة'), {
            'fields': (
                'company_name', 'company_logo', 'company_address', 'company_phone',
                'company_email', 'company_website'
            )
        }),
        (_('معلومات قانونية'), {
            'fields': ('tax_number', 'commercial_register')
        }),
        (_('إعدادات النظام'), {
            'fields': (
                'currency', 'enable_notifications', 'enable_email_notifications',
                'items_per_page', 'low_stock_threshold', 'enable_analytics'
            )
        }),
        (_('إعدادات الواجهة'), {
            'fields': (
                'primary_color', 'secondary_color', 'accent_color', 'default_theme'
            )
        }),
        (_('معلومات إضافية'), {
            'fields': (
                'working_hours', 'about_text', 'vision_text', 'mission_text'
            )
        }),
        (_('وسائل التواصل الاجتماعي'), {
            'fields': (
                'facebook_url', 'twitter_url', 'instagram_url', 'linkedin_url'
            )
        }),
        (_('إعدادات متقدمة'), {
            'fields': ('maintenance_mode', 'maintenance_message')
        }),
        (_('حقوق النشر'), {
            'fields': ('copyright_text',)
        }),
        (_('معلومات النظام'), {
            'fields': (
                'system_version', 'system_release_date', 'system_developer',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """
        السماح بإضافة إعدادات جديدة فقط إذا لم تكن موجودة
        """
        return not UnifiedSystemSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """
        منع حذف إعدادات النظام
        """
        return False


class PerformanceOptimizedAdminMixin:
    """
    Mixin لتحسين أداء Admin
    """
    
    def get_queryset(self, request):
        """
        تحسين استعلامات Admin بشكل عام
        """
        queryset = super().get_queryset(request)
        
        # إضافة select_related للحقول المرتبطة
        if hasattr(self.model, 'branch'):
            queryset = queryset.select_related('branch')
        
        if hasattr(self.model, 'created_by'):
            queryset = queryset.select_related('created_by')
        
        if hasattr(self.model, 'updated_by'):
            queryset = queryset.select_related('updated_by')
        
        # إضافة prefetch_related للعلاقات المتعددة
        if hasattr(self.model, 'departments'):
            queryset = queryset.prefetch_related('departments')
        
        if hasattr(self.model, 'permissions'):
            queryset = queryset.prefetch_related('permissions')
        
        return queryset
    
    def get_context_data(self, request, extra_context=None):
        """
        إضافة إحصائيات عامة للسياق
        """
        context = super().get_context_data(request, extra_context)
        
        # إضافة إحصائيات عامة
        context['model_statistics'] = {
            'total_count': self.get_queryset(request).count(),
            'recent_items': self.get_queryset(request).order_by('-created_at')[:5],
            'model_name': self.model._meta.verbose_name_plural
        }
        
        return context


class CacheOptimizedAdminMixin:
    """
    Mixin لتحسين التخزين المؤقت في Admin
    """
    
    def get_cache_key(self, request, action='list'):
        """
        إنشاء مفتاح التخزين المؤقت
        """
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        return f"admin_{self.model._meta.app_label}_{self.model._meta.model_name}_{action}_{user_id}"
    
    def get_cached_queryset(self, request, cache_key):
        """
        الحصول على استعلام من التخزين المؤقت
        """
        from django.core.cache import cache
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        queryset = self.get_queryset(request)
        cache.set(cache_key, queryset, 300)  # تخزين لمدة 5 دقائق
        
        return queryset


# تسجيل النماذج المحسنة
admin.site.unregister(User)
admin.site.register(User, OptimizedUserAdmin)

admin.site.unregister(Department)
admin.site.register(Department, OptimizedDepartmentAdmin)

admin.site.unregister(Notification)
admin.site.register(Notification, OptimizedNotificationAdmin)

# تسجيل إعدادات النظام الموحدة
admin.site.register(UnifiedSystemSettings, OptimizedUnifiedSystemSettingsAdmin) 