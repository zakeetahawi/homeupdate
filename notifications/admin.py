from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Notification, NotificationSettings, NotificationVisibility


class NotificationVisibilityInline(admin.TabularInline):
    """عرض مضمن لرؤية الإشعارات"""

    model = NotificationVisibility
    extra = 0
    readonly_fields = ["read_at", "created_at"]
    fields = ["user", "is_read", "read_at", "created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """إدارة الإشعارات"""

    list_display = [
        "title",
        "notification_type_display",
        "priority_display",
        "created_by_display",
        "recipients_count",
        "unread_count",
        "created_at_display",
        "related_object_link",
    ]

    list_filter = [
        "notification_type",
        "priority",
        "created_at",
        ("created_by", admin.RelatedOnlyFieldListFilter),
        ("content_type", admin.RelatedOnlyFieldListFilter),
    ]

    search_fields = [
        "title",
        "message",
        "created_by__username",
        "created_by__first_name",
        "created_by__last_name",
    ]

    readonly_fields = [
        "created_at",
        "content_type",
        "object_id",
        "related_object_link",
        "recipients_count",
        "unread_count",
    ]

    fieldsets = (
        (
            _("معلومات أساسية"),
            {"fields": ("title", "message", "notification_type", "priority")},
        ),
        (
            _("الكائن المرتبط"),
            {
                "fields": ("content_type", "object_id", "related_object_link"),
                "classes": ("collapse",),
            },
        ),
        (
            _("معلومات إضافية"),
            {
                "fields": ("created_by", "extra_data", "created_at"),
                "classes": ("collapse",),
            },
        ),
        (
            _("إحصائيات"),
            {"fields": ("recipients_count", "unread_count"), "classes": ("collapse",)},
        ),
    )

    inlines = [NotificationVisibilityInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("created_by", "content_type")
            .prefetch_related("visibility_records")
        )

    def notification_type_display(self, obj):
        """عرض نوع الإشعار مع أيقونة"""
        icon = obj.get_icon_class()
        type_display = obj.get_notification_type_display()
        return format_html(
            '<i class="{}" style="margin-left: 5px;"></i> {}', icon, type_display
        )

    notification_type_display.short_description = _("نوع الإشعار")

    def priority_display(self, obj):
        """عرض الأولوية مع لون"""
        color_map = {
            "low": "#6c757d",
            "normal": "#17a2b8",
            "high": "#ffc107",
            "urgent": "#dc3545",
        }
        color = color_map.get(obj.priority, "#17a2b8")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display(),
        )

    priority_display.short_description = _("الأولوية")

    def created_by_display(self, obj):
        """عرض المستخدم المنشئ"""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return _("النظام")

    created_by_display.short_description = _("تم الإنشاء بواسطة")

    def recipients_count(self, obj):
        """عدد المستقبلين"""
        count = obj.visibility_records.count()
        return format_html('<span class="badge badge-info">{}</span>', count)

    recipients_count.short_description = _("عدد المستقبلين")

    def unread_count(self, obj):
        """عدد غير المقروء"""
        count = obj.visibility_records.filter(is_read=False).count()
        if count > 0:
            return format_html('<span class="badge badge-warning">{}</span>', count)
        return format_html('<span class="badge badge-success">0</span>')

    unread_count.short_description = _("غير مقروء")

    def created_at_display(self, obj):
        """عرض تاريخ الإنشاء"""
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    created_at_display.short_description = _("تاريخ الإنشاء")

    def related_object_link(self, obj):
        """رابط الكائن المرتبط"""
        if obj.related_object:
            try:
                if hasattr(obj.related_object, "get_absolute_url"):
                    url = obj.related_object.get_absolute_url()
                    return format_html(
                        '<a href="{}" target="_blank">{}</a>',
                        url,
                        str(obj.related_object),
                    )
                else:
                    # رابط إدارة Django
                    url = reverse(
                        f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                        args=[obj.object_id],
                    )
                    return format_html(
                        '<a href="{}" target="_blank">{}</a>',
                        url,
                        str(obj.related_object),
                    )
            except:
                return str(obj.related_object)
        return _("لا يوجد")

    related_object_link.short_description = _("الكائن المرتبط")

    def has_add_permission(self, request):
        """منع إضافة إشعارات يدوياً"""
        return False


@admin.register(NotificationVisibility)
class NotificationVisibilityAdmin(admin.ModelAdmin):
    """إدارة رؤية الإشعارات"""

    list_display = [
        "notification_title",
        "user_display",
        "is_read_display",
        "read_at_display",
        "created_at_display",
    ]

    list_filter = [
        "is_read",
        "created_at",
        "read_at",
        ("user", admin.RelatedOnlyFieldListFilter),
        ("notification__notification_type", admin.ChoicesFieldListFilter),
    ]

    search_fields = [
        "notification__title",
        "user__username",
        "user__first_name",
        "user__last_name",
    ]

    readonly_fields = ["created_at", "read_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("notification", "user")

    def notification_title(self, obj):
        """عنوان الإشعار"""
        return obj.notification.title

    notification_title.short_description = _("الإشعار")

    def user_display(self, obj):
        """عرض المستخدم"""
        return obj.user.get_full_name() or obj.user.username

    user_display.short_description = _("المستخدم")

    def is_read_display(self, obj):
        """عرض حالة القراءة"""
        if obj.is_read:
            return format_html(
                '<span class="badge badge-success"><i class="fas fa-check"></i> مقروء</span>'
            )
        return format_html(
            '<span class="badge badge-warning"><i class="fas fa-eye-slash"></i> غير مقروء</span>'
        )

    is_read_display.short_description = _("حالة القراءة")

    def read_at_display(self, obj):
        """عرض تاريخ القراءة"""
        if obj.read_at:
            return obj.read_at.strftime("%Y-%m-%d %H:%M")
        return _("لم يُقرأ بعد")

    read_at_display.short_description = _("تاريخ القراءة")

    def created_at_display(self, obj):
        """عرض تاريخ الإنشاء"""
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    created_at_display.short_description = _("تاريخ الإنشاء")


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات الإشعارات"""

    list_display = [
        "user_display",
        "enable_customer_notifications",
        "enable_order_notifications",
        "enable_inspection_notifications",
        "enable_installation_notifications",
        "enable_complaint_notifications",
        "min_priority_level",
    ]

    list_filter = [
        "enable_customer_notifications",
        "enable_order_notifications",
        "enable_inspection_notifications",
        "enable_installation_notifications",
        "enable_complaint_notifications",
        "min_priority_level",
    ]

    search_fields = ["user__username", "user__first_name", "user__last_name"]

    def user_display(self, obj):
        """عرض المستخدم"""
        return obj.user.get_full_name() or obj.user.username

    user_display.short_description = _("المستخدم")
