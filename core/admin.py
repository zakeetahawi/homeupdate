"""
Django Admin للأمان والتدقيق
"""

from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from .audit import AuditLog, SecurityEvent


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    إدارة سجلات التدقيق
    """

    list_display = [
        "timestamp",
        "severity_badge",
        "action_badge",
        "user_link",
        "model_name",
        "description_short",
        "ip_address",
    ]
    list_filter = [
        "severity",
        "action",
        "model_name",
        ("timestamp", admin.DateFieldListFilter),
    ]
    search_fields = [
        "user__username",
        "user__email",
        "description",
        "ip_address",
        "model_name",
    ]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]
    list_per_page = 50

    fieldsets = (
        ("معلومات العملية", {"fields": ("user", "action", "severity", "description")}),
        (
            "تفاصيل الكائن",
            {
                "fields": ("model_name", "object_id", "old_value", "new_value"),
                "classes": ("collapse",),
            },
        ),
        (
            "معلومات الاتصال",
            {
                "fields": ("ip_address", "user_agent", "session_key"),
                "classes": ("collapse",),
            },
        ),
        (
            "التوقيت",
            {
                "fields": ("timestamp",),
            },
        ),
    )

    readonly_fields = [
        "user",
        "action",
        "severity",
        "model_name",
        "object_id",
        "description",
        "old_value",
        "new_value",
        "ip_address",
        "user_agent",
        "timestamp",
        "session_key",
    ]

    def has_add_permission(self, request):
        """منع الإضافة اليدوية"""
        return False

    def has_change_permission(self, request, obj=None):
        """منع التعديل - للقراءة فقط"""
        return False

    def has_delete_permission(self, request, obj=None):
        """السماح بالحذف فقط للمشرفين"""
        return request.user.is_superuser

    def severity_badge(self, obj):
        """عرض مستوى الخطورة بألوان"""
        colors = {
            "INFO": "#17a2b8",
            "WARNING": "#ffc107",
            "ERROR": "#dc3545",
            "CRITICAL": "#ff0000",
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.severity, "#6c757d"),
            obj.get_severity_display(),
        )

    severity_badge.short_description = "الخطورة"

    def action_badge(self, obj):
        """عرض نوع العملية بألوان"""
        colors = {
            "CREATE": "#28a745",
            "UPDATE": "#17a2b8",
            "DELETE": "#dc3545",
            "LOGIN": "#007bff",
            "LOGOUT": "#6c757d",
            "PERMISSION_CHANGE": "#fd7e14",
            "SECURITY_EVENT": "#e83e8c",
            "DATA_EXPORT": "#20c997",
            "SETTINGS_CHANGE": "#ffc107",
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.action, "#6c757d"),
            obj.get_action_display(),
        )

    action_badge.short_description = "العملية"

    def user_link(self, obj):
        """رابط للمستخدم"""
        if obj.user:
            return format_html(
                '<a href="/admin/accounts/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.username,
            )
        return format_html('<span style="color: #999;">نظام</span>')

    user_link.short_description = "المستخدم"

    def description_short(self, obj):
        """وصف مختصر"""
        if len(obj.description) > 50:
            return obj.description[:50] + "..."
        return obj.description

    description_short.short_description = "الوصف"

    def changelist_view(self, request, extra_context=None):
        """إضافة إحصائيات في أعلى الصفحة"""
        extra_context = extra_context or {}

        # إحصائيات آخر 24 ساعة
        last_24h = timezone.now() - timedelta(hours=24)
        stats = {
            "total": AuditLog.objects.filter(timestamp__gte=last_24h).count(),
            "critical": AuditLog.objects.filter(
                timestamp__gte=last_24h, severity="CRITICAL"
            ).count(),
            "errors": AuditLog.objects.filter(
                timestamp__gte=last_24h, severity="ERROR"
            ).count(),
            "warnings": AuditLog.objects.filter(
                timestamp__gte=last_24h, severity="WARNING"
            ).count(),
        }

        extra_context["audit_stats"] = stats
        return super().changelist_view(request, extra_context)


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """
    إدارة الأحداث الأمنية
    """

    list_display = [
        "timestamp",
        "event_badge",
        "ip_address",
        "user_link",
        "url_short",
        "method",
        "blocked_badge",
    ]
    list_filter = [
        "event_type",
        "blocked",
        ("timestamp", admin.DateFieldListFilter),
        "method",
    ]
    search_fields = ["ip_address", "user__username", "url", "user_agent"]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]
    list_per_page = 50

    fieldsets = (
        ("معلومات الحدث", {"fields": ("event_type", "blocked", "timestamp")}),
        (
            "معلومات المستخدم",
            {
                "fields": ("user", "ip_address", "user_agent"),
            },
        ),
        (
            "تفاصيل الطلب",
            {"fields": ("url", "method", "details"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = [
        "event_type",
        "ip_address",
        "user",
        "details",
        "user_agent",
        "url",
        "method",
        "blocked",
        "timestamp",
    ]

    actions = ["block_ip_addresses", "unblock_ip_addresses"]

    def has_add_permission(self, request):
        """منع الإضافة اليدوية"""
        return False

    def has_change_permission(self, request, obj=None):
        """السماح بالتعديل فقط للحظر/فك الحظر"""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """السماح بالحذف فقط للمشرفين"""
        return request.user.is_superuser

    def event_badge(self, obj):
        """عرض نوع الحدث بألوان"""
        colors = {
            "LOGIN_FAILED": "#dc3545",
            "LOGIN_SUCCESS": "#28a745",
            "BRUTE_FORCE": "#ff0000",
            "SQL_INJECTION": "#ff0000",
            "XSS_ATTEMPT": "#ff0000",
            "CSRF_FAILED": "#dc3545",
            "RATE_LIMIT": "#ffc107",
            "SUSPICIOUS_ACTIVITY": "#fd7e14",
            "PERMISSION_DENIED": "#6c757d",
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.event_type, "#6c757d"),
            obj.get_event_type_display(),
        )

    event_badge.short_description = "نوع الحدث"

    def blocked_badge(self, obj):
        """حالة الحظر"""
        if obj.blocked:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-weight: bold; font-size: 11px;">محظور</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">مسموح</span>'
        )

    blocked_badge.short_description = "الحالة"

    def user_link(self, obj):
        """رابط للمستخدم"""
        if obj.user:
            return format_html(
                '<a href="/admin/accounts/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.username,
            )
        return format_html('<span style="color: #999;">غير معروف</span>')

    user_link.short_description = "المستخدم"

    def url_short(self, obj):
        """URL مختصر"""
        if obj.url and len(obj.url) > 40:
            return obj.url[:40] + "..."
        return obj.url or "-"

    url_short.short_description = "URL"

    def block_ip_addresses(self, request, queryset):
        """حظر عناوين IP المحددة"""
        queryset.update(blocked=True)
        self.message_user(request, f"تم حظر {queryset.count()} عنوان IP")

    block_ip_addresses.short_description = "حظر عناوين IP المحددة"

    def unblock_ip_addresses(self, request, queryset):
        """فك حظر عناوين IP المحددة"""
        queryset.update(blocked=False)
        self.message_user(request, f"تم فك حظر {queryset.count()} عنوان IP")

    unblock_ip_addresses.short_description = "فك حظر عناوين IP المحددة"

    def changelist_view(self, request, extra_context=None):
        """إضافة إحصائيات الأمان"""
        extra_context = extra_context or {}

        # إحصائيات آخر 24 ساعة
        last_24h = timezone.now() - timedelta(hours=24)

        stats = {
            "total_events": SecurityEvent.objects.filter(
                timestamp__gte=last_24h
            ).count(),
            "blocked_attempts": SecurityEvent.objects.filter(
                timestamp__gte=last_24h, blocked=True
            ).count(),
            "brute_force": SecurityEvent.objects.filter(
                timestamp__gte=last_24h, event_type="BRUTE_FORCE"
            ).count(),
            "sql_injection": SecurityEvent.objects.filter(
                timestamp__gte=last_24h, event_type="SQL_INJECTION"
            ).count(),
            "xss_attempts": SecurityEvent.objects.filter(
                timestamp__gte=last_24h, event_type="XSS_ATTEMPT"
            ).count(),
            "failed_logins": SecurityEvent.objects.filter(
                timestamp__gte=last_24h, event_type="LOGIN_FAILED"
            ).count(),
        }

        # أكثر IPs نشاطاً مشبوهاً
        top_ips = (
            SecurityEvent.objects.filter(timestamp__gte=last_24h)
            .values("ip_address")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        extra_context["security_stats"] = stats
        extra_context["top_suspicious_ips"] = top_ips

        return super().changelist_view(request, extra_context)


# تخصيص عنوان Admin
admin.site.site_header = "لوحة تحكم النظام - الأمان والتدقيق"
admin.site.site_title = "إدارة الأمان"
admin.site.index_title = "مرحباً بك في لوحة التحكم"
