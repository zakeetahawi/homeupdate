from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.mixins import PaginationFixMixin

from .models import Notification, NotificationSettings, NotificationVisibility
from .serializers import NotificationSerializer, NotificationVisibilitySerializer
from .utils import (
    get_user_notification_count,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


class NotificationListView(PaginationFixMixin, LoginRequiredMixin, ListView):
    """صفحة قائمة الإشعارات"""

    model = Notification
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 20
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def get_queryset(self):
        """الحصول على الإشعارات المرئية للمستخدم الحالي"""
        from notifications.models import NotificationVisibility

        queryset = (
            Notification.objects.for_user(self.request.user)
            .select_related("created_by", "content_type")
            .prefetch_related(
                models.Prefetch(
                    "visibility_records",
                    queryset=NotificationVisibility.objects.filter(
                        user=self.request.user
                    ),
                    to_attr="user_vis_list",
                )
            )
        )

        # فلترة حسب النوع
        notification_type = self.request.GET.get("type")
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        # فلترة حسب الأولوية
        priority = self.request.GET.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)

        # فلترة حسب حالة القراءة
        read_status = self.request.GET.get("read")
        if read_status == "unread":
            queryset = queryset.filter(
                visibility_records__user=self.request.user,
                visibility_records__is_read=False,
            )
        elif read_status == "read":
            queryset = queryset.filter(
                visibility_records__user=self.request.user,
                visibility_records__is_read=True,
            )

        # فلترة حسب التاريخ
        date_from = self.request.GET.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.GET.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        # فلترة حسب المستخدم المنشئ
        created_by = self.request.GET.get("created_by")
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        # البحث
        search = self.request.GET.get("search")
        if search:
            # البحث في العنوان والرسالة
            search_query = Q(title__icontains=search) | Q(message__icontains=search)

            # البحث في extra_data (JSON)
            search_query |= Q(extra_data__icontains=search)

            queryset = queryset.filter(search_query)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إضافة معلومات إضافية للسياق
        unread_count = get_user_notification_count(self.request.user)
        total_count = context["paginator"].count if context.get("paginator") else 0
        context.update(
            {
                "notification_types": Notification.NOTIFICATION_TYPES,
                "priority_levels": Notification.PRIORITY_LEVELS,
                "current_type": self.request.GET.get("type", ""),
                "current_priority": self.request.GET.get("priority", ""),
                "current_read": self.request.GET.get("read", ""),
                "current_search": self.request.GET.get("search", ""),
                "filter_created_by": self.request.GET.get("created_by", ""),
                "filter_date_from": self.request.GET.get("date_from", ""),
                "filter_date_to": self.request.GET.get("date_to", ""),
                "unread_count": unread_count,
                "read_count": max(0, total_count - unread_count),
                "total_count": total_count,
            }
        )

        # إضافة المستخدمين الذين لديهم إشعارات (cached subquery)
        User = get_user_model()
        users_with_notifications = (
            User.objects.filter(
                id__in=Notification.objects.for_user(self.request.user)
                .values("created_by")
                .distinct()
            )
            .only("id", "first_name", "last_name", "username")
            .order_by("first_name", "last_name", "username")
        )
        context["users_with_notifications"] = users_with_notifications

        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """صفحة تفاصيل الإشعار"""

    model = Notification
    template_name = "notifications/detail.html"
    context_object_name = "notification"

    def get_queryset(self):
        """التأكد من أن المستخدم مصرح له برؤية الإشعار"""
        return Notification.objects.for_user(self.request.user)

    def get_object(self, queryset=None):
        """الحصول على الإشعار وتحديده كمقروء"""
        obj = super().get_object(queryset)

        # تحديد الإشعار كمقروء
        mark_notification_as_read(obj, self.request.user)

        return obj


@login_required
def mark_notification_read(request, pk):
    """تحديد إشعار كمقروء"""
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"🔔 محاولة تحديد الإشعار {pk} كمقروء للمستخدم {request.user.username}")

    notification = get_object_or_404(Notification.objects.for_user(request.user), pk=pk)

    success = mark_notification_as_read(notification, request.user)
    logger.info(f"📖 نتيجة تحديد الإشعار {pk}: {success}")

    # إذا كان AJAX request، إرجاع JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if success:
            return JsonResponse(
                {
                    "success": True,
                    "message": "تم تحديد الإشعار كمقروء",
                    "notification_id": notification.pk,
                    "user": request.user.get_full_name() or request.user.username,
                }
            )
        else:
            return JsonResponse(
                {"success": False, "message": "حدث خطأ أثناء تحديث الإشعار"}, status=400
            )

    # للطلبات العادية
    if request.method == "POST":
        if success:
            messages.success(request, _("تم تحديد الإشعار كمقروء"))
        else:
            messages.error(request, _("حدث خطأ أثناء تحديث الإشعار"))

        return redirect("notifications:list")
    else:
        # GET request - redirect to notification detail
        if success:
            messages.success(request, _("تم تحديد الإشعار كمقروء"))

        return redirect(notification.get_absolute_url())


@login_required
def mark_all_notifications_read(request):
    """تحديد جميع الإشعارات كمقروءة"""

    # إذا كان GET request، اعرض صفحة تأكيد
    if request.method == "GET":
        # عدد الإشعارات غير المقروءة
        from .utils import get_user_notification_count

        unread_count = get_user_notification_count(request.user)

        if unread_count == 0:
            messages.info(request, _("لا توجد إشعارات غير مقروءة"))
            return redirect("notifications:list")

        # عرض صفحة تأكيد
        context = {
            "unread_count": unread_count,
            "title": _("تحديد جميع الإشعارات كمقروءة"),
        }
        return render(request, "notifications/confirm_mark_all_read.html", context)

    # إذا كان POST request، قم بالتحديث
    elif request.method == "POST":
        try:
            count = mark_all_notifications_as_read(request.user)

            message = _("تم تحديد {} إشعار كمقروء").format(count)

            # إذا كان الطلب AJAX، أرجع JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": True, "count": count, "message": message}
                )

            # إذا كان طلب عادي، أضف رسالة وأعد التوجيه
            messages.success(request, message)
            return redirect("notifications:list")

        except Exception as e:
            error_message = _("حدث خطأ أثناء تحديث الإشعارات: {}").format(str(e))

            # إذا كان الطلب AJAX، أرجع JSON للخطأ
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": error_message}, status=500
                )

            # إذا كان طلب عادي، أضف رسالة خطأ وأعد التوجيه
            messages.error(request, error_message)
            return redirect("notifications:list")

    # إذا كان method آخر، أرجع خطأ
    else:
        return JsonResponse(
            {"success": False, "message": _("طريقة الطلب غير مدعومة")}, status=405
        )


@login_required
def notification_count_ajax(request):
    """الحصول على عدد الإشعارات غير المقروءة عبر AJAX"""
    count = get_user_notification_count(request.user)

    return JsonResponse({"success": True, "count": count})


@login_required
def transfer_notifications_api(request):
    """
    API للتحقق من إشعارات التحويلات المخزنية (الملغية/المرفوضة) والطلبات المرفوضة غير المقروءة
    تُستخدم لإظهار popup مركزي في وسط الشاشة
    """
    try:
        from .models import NotificationVisibility
        notifications_qs = (
            Notification.objects.filter(
                notification_type__in=[
                    "transfer_cancelled", "transfer_rejected", "order_rejected"
                ],
                visibility_records__user=request.user,
                visibility_records__is_read=False,
            )
            .select_related("created_by")
            .order_by("-created_at")[:10]
        )

        notifications_data = []
        for notification in notifications_qs:
            extra = notification.extra_data or {}
            n_type = notification.notification_type

            if n_type in ("transfer_cancelled", "transfer_rejected"):
                url = (
                    f"/inventory/stock-transfer/{extra.get('transfer_id', '')}/"
                    if extra.get("transfer_id")
                    else "/inventory/stock-transfers/"
                )
                notifications_data.append({
                    "id": notification.pk,
                    "category": "transfer",
                    "title": notification.title,
                    "message": notification.message,
                    "type": n_type,
                    "transfer_number": extra.get("transfer_number", ""),
                    "from_warehouse": extra.get("from_warehouse", ""),
                    "to_warehouse": extra.get("to_warehouse", ""),
                    "reason": extra.get("reason", ""),
                    "transfer_id": extra.get("transfer_id", ""),
                    "created_at": notification.created_at.isoformat(),
                    "created_by": (
                        notification.created_by.get_full_name() or notification.created_by.username
                    ) if notification.created_by else "",
                    "url": url,
                })
            elif n_type == "order_rejected":
                order_id = extra.get("order_id", "")
                url = f"/orders/{order_id}/" if order_id else "/orders/"
                notifications_data.append({
                    "id": notification.pk,
                    "category": "order",
                    "title": notification.title,
                    "message": notification.message,
                    "type": n_type,
                    "order_number": extra.get("order_number", ""),
                    "customer_name": extra.get("customer_name", ""),
                    "reason": extra.get("rejection_reason", ""),
                    "order_id": order_id,
                    "created_at": notification.created_at.isoformat(),
                    "created_by": (
                        notification.created_by.get_full_name() or notification.created_by.username
                    ) if notification.created_by else "",
                    "url": url,
                })

        return JsonResponse({
            "success": True,
            "notifications": notifications_data,
            "count": len(notifications_data),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def popup_notifications_api(request):
    """
    API endpoint للإشعارات المنبثقة - يعرض فقط الإشعارات العاجلة والعالية الأولوية
    """
    try:
        # الحصول على آخر 5 إشعارات غير مقروءة عاجلة أو عالية الأولوية فقط
        unread_notifications = (
            Notification.objects.for_user(request.user)
            .filter(
                visibility_records__user=request.user,
                visibility_records__is_read=False,
                priority__in=["urgent", "high"],
            )
            .select_related("created_by", "content_type")
            .order_by("-created_at")[:5]
        )

        notifications_data = []
        for notification in unread_notifications:
            icon_data = notification.get_icon_and_color()

            # تحديد الأولوية كنص
            priority_map = {
                "urgent": "عاجلة",
                "high": "عالية",
                "normal": "عادية",
                "low": "منخفضة",
            }

            # تحديد لون الأولوية (badge)
            # يعتمد على نوع الإشعار أولاً لإعطاء لون صحيح بصرياً
            type_priority_color = {
                "order_rejected": "danger", "transfer_cancelled": "danger",
                "transfer_rejected": "danger", "cutting_item_rejected": "danger",
                "complaint_escalated": "danger", "complaint_overdue": "danger",
                "order_status_changed": "warning", "manufacturing_status_changed": "warning",
                "inspection_status_changed": "warning", "complaint_status_changed": "warning",
                "order_completed": "success", "order_delivered": "success",
                "installation_completed": "success", "manufacturing_completed": "success",
                "inspection_completed": "success", "cutting_completed": "success",
                "complaint_resolved": "success",
            }
            priority_color_map = {
                "urgent": "danger",
                "high": "warning",
                "normal": "secondary",
                "low": "success",
            }

            # تحديد لون header حسب نوع الإشعار (يتجاوز الأولوية)
            # green = اكتمال/تسليم، orange = تبديل حالة، red = رفض، None = يعتمد على الأولوية
            header_color_by_type = {
                # أخضر: إتمام وتسليم
                "order_completed": "green",
                "order_delivered": "green",
                "installation_completed": "green",
                "manufacturing_completed": "green",
                "inspection_completed": "green",
                "cutting_completed": "green",
                "complaint_resolved": "green",
                # برتقالي: تبديل حالة
                "order_status_changed": "orange",
                "manufacturing_status_changed": "orange",
                "inspection_status_changed": "orange",
                "complaint_status_changed": "orange",
                # أحمر: رفض وإلغاء
                "order_rejected": "red",
                "transfer_cancelled": "red",
                "transfer_rejected": "red",
                "cutting_item_rejected": "red",
                "complaint_escalated": "red",
                "complaint_overdue": "red",
            }
            header_color = header_color_by_type.get(
                notification.notification_type,
                icon_data.get("header", None)  # fallback من icon_map
            )

            # الحصول على اسم المستخدم المنشئ
            created_by_name = None
            if notification.created_by:
                created_by_name = notification.created_by.get_full_name() or notification.created_by.username
            elif notification.extra_data and notification.extra_data.get("changed_by"):
                created_by_name = notification.extra_data["changed_by"]

            notifications_data.append(
                {
                    "id": notification.pk,
                    "title": notification.title,
                    "message": notification.message[:150] + "..." if len(notification.message) > 150 else notification.message,
                    "type": notification.notification_type,
                    "type_display": notification.get_notification_type_display(),
                    "priority": notification.priority,
                    "priority_text": priority_map.get(notification.priority, "عادية"),
                    "priority_color": type_priority_color.get(
                        notification.notification_type,
                        priority_color_map.get(notification.priority, "secondary")
                    ),
                    "header_color": header_color,
                    "icon_class": icon_data.get("icon", "fas fa-bell"),
                    "icon_color": icon_data.get("color", "#6c757d"),
                    "icon_bg": icon_data.get("bg", "#f8f9fa"),
                    "created_at": notification.created_at.isoformat(),
                    "created_by": created_by_name,
                    "url": notification.get_absolute_url(),
                }
            )

        return JsonResponse(
            {
                "success": True,
                "notifications": notifications_data,
                "count": len(notifications_data),
            }
        )

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in popup_notifications_api: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def recent_notifications_ajax(request):
    """الحصول على آخر الإشعارات عبر AJAX"""
    limit = int(request.GET.get("limit", 10))

    notifications = (
        Notification.objects.recent_for_user(request.user, limit=limit)
        .select_related("created_by", "content_type")
        .prefetch_related("visibility_records")
    )

    notifications_data = []
    for notification in notifications:
        # الحصول على حالة القراءة من الـ prefetch
        visibility_records = [
            v for v in notification.visibility_records.all() if v.user == request.user
        ]
        is_read = visibility_records[0].is_read if visibility_records else False

        # الحصول على بيانات الأيقونة واللون
        icon_data = notification.get_icon_and_color()

        notifications_data.append(
            {
                "id": notification.pk,
                "title": notification.title,
                "message": notification.message,
                "type": notification.notification_type,
                "notification_type_display": notification.get_notification_type_display(),
                "priority": notification.priority,
                "priority_display": notification.get_priority_display(),
                "icon_class": icon_data["icon"],
                "color_class": icon_data["color"],
                "bg_color": icon_data["bg"],
                "is_read": is_read,
                "created_at": notification.created_at.isoformat(),
                "url": notification.get_absolute_url(),
                "created_by_name": (
                    notification.created_by.get_full_name()
                    if notification.created_by
                    else None
                ),
                "extra_data": notification.extra_data,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "notifications": notifications_data,
            "count": len(notifications_data),
        }
    )


# ===== Activity Summary API =====


@login_required
def activity_summary_api(request):
    """
    ملخص النشاط منذ آخر تسجيل دخول — حسب صلاحيات المستخدم
    يظهر مرة واحدة فقط عند الدخول ثم لا يظهر ثانية.
    """
    import logging
    from datetime import timedelta
    from dateutil.parser import parse as parse_date

    logger = logging.getLogger(__name__)

    try:
        user = request.user

        # --- تحديد "منذ متى" ---
        previous_login_iso = request.session.get("previous_last_login")
        if previous_login_iso:
            try:
                since = parse_date(previous_login_iso)
            except Exception:
                since = timezone.now() - timedelta(hours=24)
        else:
            # أول دخول أو لا يوجد سجل — عرض آخر 24 ساعة
            since = timezone.now() - timedelta(hours=24)

        # تحميل النماذج ديناميكياً لتجنب الاستيراد الدائري
        from orders.models import Order
        from manufacturing.models import ManufacturingOrder
        from installations.models import InstallationSchedule

        items = []  # [{icon, label, count, color, url}]
        role = user.get_user_role() if hasattr(user, "get_user_role") else ""

        # --- 1. طلبات جديدة ---
        new_orders_qs = Order.objects.filter(created_at__gte=since)
        if user.branch and not user.is_superuser:
            new_orders_qs = new_orders_qs.filter(branch=user.branch)
        new_orders = new_orders_qs.count()
        if new_orders:
            items.append({
                "icon": "fas fa-plus-circle",
                "label": "طلبات جديدة",
                "count": new_orders,
                "color": "#3b82f6",
                "url": "/orders/",
            })

        # --- 2. طلبات مكتملة ---
        completed_qs = Order.objects.filter(
            order_status="completed", updated_at__gte=since
        )
        if user.branch and not user.is_superuser:
            completed_qs = completed_qs.filter(branch=user.branch)
        completed = completed_qs.count()
        if completed:
            items.append({
                "icon": "fas fa-check-circle",
                "label": "طلبات مكتملة",
                "count": completed,
                "color": "#10b981",
                "url": "/orders/?status=completed",
            })

        # --- 3. تصنيع ---
        if role in (
            "admin", "factory_manager", "factory_accountant",
            "factory_receiver", "branch_manager", "sales_manager", ""
        ) or user.is_superuser:
            mfg_completed = ManufacturingOrder.objects.filter(
                status__in=["ready_install", "completed"],
                updated_at__gte=since,
            ).count()
            if mfg_completed:
                items.append({
                    "icon": "fas fa-industry",
                    "label": "أوامر تصنيع مكتملة",
                    "count": mfg_completed,
                    "color": "#8b5cf6",
                    "url": "/manufacturing/",
                })

            mfg_new = ManufacturingOrder.objects.filter(
                status="pending", created_at__gte=since
            ).count()
            if mfg_new:
                items.append({
                    "icon": "fas fa-cogs",
                    "label": "أوامر تصنيع جديدة",
                    "count": mfg_new,
                    "color": "#6366f1",
                    "url": "/manufacturing/",
                })

        # --- 4. تركيبات ---
        if role in (
            "admin", "installation_manager", "traffic_manager",
            "branch_manager", "sales_manager", ""
        ) or user.is_superuser:
            install_completed = InstallationSchedule.objects.filter(
                status="completed", updated_at__gte=since
            ).count()
            if install_completed:
                items.append({
                    "icon": "fas fa-tools",
                    "label": "تركيبات مكتملة",
                    "count": install_completed,
                    "color": "#f59e0b",
                    "url": "/installations/",
                })

            install_scheduled = InstallationSchedule.objects.filter(
                status="scheduled", created_at__gte=since
            ).count()
            if install_scheduled:
                items.append({
                    "icon": "fas fa-calendar-check",
                    "label": "تركيبات مجدولة جديدة",
                    "count": install_scheduled,
                    "color": "#06b6d4",
                    "url": "/installations/",
                })

        # --- 5. إشعارات غير مقروءة ---
        unread = NotificationVisibility.objects.filter(
            user=user, is_read=False,
            notification__created_at__gte=since,
        ).count()
        if unread:
            items.append({
                "icon": "fas fa-bell",
                "label": "إشعارات جديدة",
                "count": unread,
                "color": "#ef4444",
                "url": "/notifications/",
            })

        # --- حساب المدة بالنص ---
        diff = timezone.now() - since
        hours = int(diff.total_seconds() // 3600)
        if hours < 1:
            since_text = "أقل من ساعة"
        elif hours < 24:
            since_text = f"{hours} ساعة"
        else:
            days = hours // 24
            since_text = f"{days} يوم" if days < 11 else f"{days} يوماً"

        return JsonResponse({
            "success": True,
            "items": items,
            "since_text": since_text,
            "total": sum(i["count"] for i in items),
        })

    except Exception as e:
        logger.error(f"Error in activity_summary_api: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ===== API Views =====


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API للإشعارات"""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get_queryset(self):
        """الحصول على الإشعارات المرئية للمستخدم الحالي"""
        return (
            Notification.objects.for_user(self.request.user)
            .select_related("created_by", "content_type")
            .prefetch_related("visibility_records")
        )

    @action(detail=False, methods=["get"])
    def unread(self, request):
        """الحصول على الإشعارات غير المقروءة"""
        notifications = Notification.objects.unread_for_user(request.user)
        serializer = self.get_serializer(notifications, many=True)

        return Response({"count": notifications.count(), "results": serializer.data})

    @action(detail=False, methods=["get"])
    def count(self, request):
        """الحصول على عدد الإشعارات غير المقروءة"""
        count = get_user_notification_count(request.user)

        return Response({"unread_count": count})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """تحديد إشعار كمقروء"""
        notification = self.get_object()
        success = mark_notification_as_read(notification, request.user)

        return Response(
            {
                "success": success,
                "message": _("تم تحديد الإشعار كمقروء") if success else _("حدث خطأ"),
            }
        )

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """تحديد جميع الإشعارات كمقروءة"""
        count = mark_all_notifications_as_read(request.user)

        return Response(
            {
                "success": True,
                "count": count,
                "message": _("تم تحديد {} إشعار كمقروء").format(count),
            }
        )
