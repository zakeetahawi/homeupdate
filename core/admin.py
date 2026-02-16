"""
Django Admin للأمان والتدقيق
"""

from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from .audit import AuditLog, SecurityEvent
from .models import RecycleBin


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
        """منع حذف سجلات التدقيق نهائياً — لأغراض الامتثال والأمان"""
        return False

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
        """منع حذف الأحداث الأمنية نهائياً — لأغراض الامتثال والأمان"""
        return False

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


@admin.register(RecycleBin)
class RecycleBinAdmin(admin.ModelAdmin):
    """
    Global Recycle Bin Dashboard - عرض جميع العناصر المحذوفة من جميع الأقسام
    سلة محذوفات مركزية تعرض كل العناصر المحذوفة مع العلاقات المرتبطة بها
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return RecycleBin.objects.none()

    def _get_all_soft_delete_models(self):
        """
        اكتشاف جميع الموديلات التي تستخدم SoftDeleteMixin تلقائياً
        """
        from django.apps import apps
        from core.soft_delete import SoftDeleteMixin

        soft_delete_models = []
        for model in apps.get_models():
            if issubclass(model, SoftDeleteMixin) and not model._meta.abstract:
                soft_delete_models.append(model)
        return soft_delete_models

    def _get_admin_url(self, model):
        """Get admin changelist URL for a model with is_deleted filter."""
        from django.urls import reverse, NoReverseMatch
        try:
            app_label = model._meta.app_label
            model_name = model._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_changelist")
            return url + "?is_deleted__exact=1"
        except NoReverseMatch:
            return None

    def _get_model_display_info(self, model):
        """Get display metadata for a model."""
        APP_LABELS = {
            'orders': 'الطلبات',
            'customers': 'العملاء',
            'inventory': 'المخزون',
            'manufacturing': 'التصنيع',
            'installations': 'التركيبات',
            'cutting': 'القص',
            'inspections': 'المعاينات',
        }
        app_label = model._meta.app_label
        return {
            'app_label': app_label,
            'app_label_ar': APP_LABELS.get(app_label, app_label),
            'model_name': model._meta.model_name,
            'verbose_name': str(model._meta.verbose_name),
            'verbose_name_plural': str(model._meta.verbose_name_plural),
        }

    def _get_deleted_items_detail(self, model, max_items=50):
        """
        Get deleted items with their related deleted children.
        Returns list of dicts with item info + related items.
        """
        from core.soft_delete import SoftDeleteMixin

        deleted_qs = model.all_objects.filter(is_deleted=True).select_related()
        if hasattr(model, 'deleted_by'):
            deleted_qs = deleted_qs.select_related('deleted_by')

        items = []
        for obj in deleted_qs[:max_items]:
            item = {
                'pk': obj.pk,
                'str': str(obj),
                'deleted_at': getattr(obj, 'deleted_at', None),
                'deleted_by': str(getattr(obj, 'deleted_by', None) or ''),
                'related': [],
            }

            # Find related deleted objects
            for related in model._meta.related_objects:
                accessor = related.get_accessor_name()
                if not hasattr(obj, accessor):
                    continue
                try:
                    related_model = related.related_model
                    if not issubclass(related_model, SoftDeleteMixin):
                        continue

                    related_manager = getattr(obj, accessor)
                    if hasattr(related_model, 'all_objects'):
                        related_deleted = related_model.all_objects.filter(
                            **{related.field.name: obj},
                            is_deleted=True,
                        )
                    else:
                        continue

                    count = related_deleted.count()
                    if count > 0:
                        item['related'].append({
                            'verbose_name_plural': str(related_model._meta.verbose_name_plural),
                            'count': count,
                            'items': [
                                {'pk': r.pk, 'str': str(r)}
                                for r in related_deleted[:10]
                            ],
                        })
                except Exception:
                    continue

            items.append(item)
        return items

    def _handle_restore(self, request):
        """Handle restore action from POST."""
        from django.apps import apps
        from django.contrib import messages as msg

        app_label = request.POST.get('app_label')
        model_name = request.POST.get('model_name')
        pk = request.POST.get('pk')
        cascade = request.POST.get('cascade', '') == '1'

        if not all([app_label, model_name, pk]):
            msg.error(request, 'بيانات غير صحيحة')
            return

        try:
            model = apps.get_model(app_label, model_name)
            obj = model.all_objects.get(pk=pk)
            obj.restore(cascade=cascade)
            label = 'متسلسلة ' if cascade else ''
            msg.success(request, f'تمت الاستعادة {label}بنجاح: {obj}')
        except Exception as e:
            msg.error(request, f'خطأ في الاستعادة: {e}')

    def _handle_hard_delete(self, request):
        """Handle permanent delete action from POST.
        يحذف العنصر نهائياً مع معالجة العلاقات المحمية (PROTECT) تلقائياً.
        """
        from django.apps import apps
        from django.contrib import messages as msg
        from django.db import transaction

        if not request.user.is_superuser:
            msg.error(request, 'الحذف النهائي متاح للمدير العام فقط')
            return

        app_label = request.POST.get('app_label')
        model_name = request.POST.get('model_name')
        pk = request.POST.get('pk')

        if not all([app_label, model_name, pk]):
            msg.error(request, 'بيانات غير صحيحة')
            return

        try:
            model = apps.get_model(app_label, model_name)
            obj = model.all_objects.get(pk=pk)
            name = str(obj)

            with transaction.atomic():
                from core.admin_mixins import SoftDeleteAdminMixin
                SoftDeleteAdminMixin._hard_delete_cascade(obj)

            msg.success(request, f'تم الحذف النهائي بنجاح: {name}')
        except Exception as e:
            msg.error(request, f'خطأ في الحذف النهائي: {e}')

    def changelist_view(self, request, extra_context=None):
        """
        سلة المحذوفات المركزية - تعرض كل العناصر المحذوفة من جميع الأقسام
        مع عرض هرمي للعلاقات المرتبطة
        """
        from django.shortcuts import redirect

        # Handle POST actions (restore / hard delete)
        if request.method == 'POST':
            action = request.POST.get('recycle_action')
            if action == 'restore':
                self._handle_restore(request)
            elif action == 'hard_delete':
                self._handle_hard_delete(request)
            return redirect(request.get_full_path())

        extra_context = extra_context or {}

        # Define primary models (top-level entities shown first)
        PRIMARY_MODELS = ['Customer', 'Order', 'Inspection']

        all_models = self._get_all_soft_delete_models()

        # Categorize: primary models vs secondary (related) models
        categories = []  # list of {model_info, count, items, url, is_primary}
        total_deleted = 0

        for model in all_models:
            try:
                count = model.all_objects.filter(is_deleted=True).count()
            except Exception:
                count = 0

            if count == 0:
                continue

            total_deleted += count
            info = self._get_model_display_info(model)
            url = self._get_admin_url(model)
            is_primary = model.__name__ in PRIMARY_MODELS

            # Get detailed items for primary models, summary for secondary
            if is_primary:
                items = self._get_deleted_items_detail(model, max_items=50)
            else:
                items = self._get_deleted_items_detail(model, max_items=20)

            categories.append({
                'model': model,
                'info': info,
                'count': count,
                'items': items,
                'url': url,
                'is_primary': is_primary,
            })

        # Sort: primary first, then by count descending
        categories.sort(key=lambda c: (not c['is_primary'], -c['count']))

        extra_context['categories'] = categories
        extra_context['total_deleted'] = total_deleted
        extra_context['title'] = 'سلة المحذوفات المركزية'

        return super().changelist_view(request, extra_context)


# تخصيص عنوان Admin
admin.site.site_header = "لوحة تحكم النظام - الأمان والتدقيق"
admin.site.site_title = "إدارة الأمان"
admin.site.index_title = "مرحباً بك في لوحة التحكم"
