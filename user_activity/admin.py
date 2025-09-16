"""
إدارة نماذج نشاط المستخدمين
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import UserSession, UserActivityLog, OnlineUser, UserLoginHistory


@admin.register(OnlineUser)
class OnlineUserAdmin(admin.ModelAdmin):
    """إدارة المستخدمين المتصلين"""
    list_display = [
        'user', 'last_seen', 'current_page_title', 'online_duration_display',
        'pages_visited', 'actions_performed', 'ip_address'
    ]
    list_filter = ['last_seen']
    search_fields = ['user__username', 'user__email', 'current_page', 'ip_address']
    readonly_fields = [
        'user', 'last_seen', 'current_page', 'current_page_title',
        'ip_address', 'session_key', 'device_info', 'pages_visited',
        'actions_performed', 'login_time', 'online_duration_display'
    ]
    ordering = ['-last_seen']

    def online_duration_display(self, obj):
        """عرض مدة الاتصال"""
        return obj.online_duration_formatted

    online_duration_display.short_description = 'مدة الاتصال'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """إدارة سجلات نشاط المستخدمين"""
    list_display = [
        'user', 'action_type_display', 'entity_type', 'description_short',
        'timestamp', 'success', 'ip_address'
    ]
    list_filter = [
        'action_type', 'entity_type', 'success', 'timestamp',
        ('user', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'user__username', 'user__email', 'description', 'url_path', 'ip_address'
    ]
    readonly_fields = [
        'user', 'session', 'action_type', 'entity_type', 'entity_id',
        'entity_name', 'description', 'url_path', 'http_method',
        'ip_address', 'user_agent', 'extra_data', 'timestamp',
        'success', 'error_message'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    list_per_page = 50

    def action_type_display(self, obj):
        """عرض نوع العملية مع الأيقونة"""
        return format_html(
            '<span title="{}">{} {}</span>',
            obj.get_action_type_display(),
            obj.get_icon(),
            obj.get_action_type_display()
        )

    action_type_display.short_description = 'نوع العملية'

    def description_short(self, obj):
        """عرض وصف مختصر"""
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description

    description_short.short_description = 'الوصف'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """إدارة جلسات المستخدمين"""
    list_display = [
        'user', 'ip_address', 'device_type', 'browser',
        'login_time', 'last_activity', 'is_active', 'duration_display'
    ]
    list_filter = [
        'is_active', 'device_type', 'login_time', 'last_activity'
    ]
    search_fields = ['user__username', 'user__email', 'ip_address', 'browser']
    readonly_fields = [
        'session_key', 'login_time', 'last_activity', 'duration_display'
    ]
    date_hierarchy = 'login_time'
    ordering = ['-last_activity']

    def duration_display(self, obj):
        """عرض مدة الجلسة"""
        duration = obj.duration
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if duration.days > 0:
            return f"{duration.days} يوم و {hours} ساعة"
        elif hours > 0:
            return f"{hours} ساعة و {minutes} دقيقة"
        else:
            return f"{minutes} دقيقة"

    duration_display.short_description = 'مدة الجلسة'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    """إدارة سجلات تسجيل الدخول"""
    list_display = [
        'user_display', 'login_time', 'logout_time', 'session_duration_display',
        'device_type', 'browser', 'ip_address', 'is_successful_login'
    ]
    list_filter = [
        'is_successful_login', 'device_type', 'logout_reason',
        ('user', admin.RelatedOnlyFieldListFilter),
        'login_time', 'logout_time'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name', 'user__email', 
        'ip_address', 'browser', 'operating_system', 'device_type'
    ]
    readonly_fields = [
        'user', 'login_time', 'logout_time', 'ip_address', 'user_agent',
        'session_key', 'browser', 'operating_system', 'device_type',
        'pages_visited', 'actions_performed', 'is_successful_login',
        'logout_reason', 'session_duration_display'
    ]
    date_hierarchy = 'login_time'
    ordering = ['-login_time']
    list_per_page = 50

    def user_display(self, obj):
        """عرض اسم المستخدم مع رابط"""
        if obj.user:
            full_name = obj.user.get_full_name() or obj.user.username
            return format_html(
                '<a href="{}" target="_blank">{}</a><br/><small style="color: #666;">{}</small>',
                reverse('admin:accounts_user_change', args=[obj.user.pk]),
                full_name,
                obj.user.username
            )
        return '-'
    user_display.short_description = 'المستخدم'
    user_display.admin_order_field = 'user__username'

    def session_duration_display(self, obj):
        """عرض مدة الجلسة"""
        return obj.session_duration_formatted

    session_duration_display.short_description = 'مدة الجلسة'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
