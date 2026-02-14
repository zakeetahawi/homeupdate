"""
واجهات سجل التدقيق — Audit Log Views
عرض وتصفية وتصدير سجلات التدقيق للنظام
"""

import csv
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .audit import AuditLog

User = get_user_model()


def is_admin_or_manager(user):
    """التحقق من صلاحيات الوصول لسجل التدقيق"""
    if user.is_superuser:
        return True
    role = getattr(user, "role", None)
    return role in ("system_admin", "branch_manager", "sales_manager")


@login_required
@user_passes_test(is_admin_or_manager, login_url="/accounts/login/")
def audit_log_list(request):
    """
    عرض سجلات التدقيق مع إمكانية التصفية والبحث
    """
    queryset = AuditLog.objects.select_related("user").order_by("-timestamp")

    # --- الفلاتر ---
    action = request.GET.get("action", "")
    severity = request.GET.get("severity", "")
    user_id = request.GET.get("user", "")
    model_name = request.GET.get("model", "")
    search = request.GET.get("q", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if action:
        queryset = queryset.filter(action=action)
    if severity:
        queryset = queryset.filter(severity=severity)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if model_name:
        queryset = queryset.filter(model_name=model_name)
    if search:
        queryset = queryset.filter(
            Q(description__icontains=search)
            | Q(username__icontains=search)
            | Q(object_repr__icontains=search)
            | Q(url_path__icontains=search)
        )
    if date_from:
        queryset = queryset.filter(timestamp__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(timestamp__date__lte=date_to)

    # --- إحصائيات سريعة ---
    last_24h = timezone.now() - timedelta(hours=24)
    stats = {
        "total_24h": AuditLog.objects.filter(timestamp__gte=last_24h).count(),
        "creates_24h": AuditLog.objects.filter(
            timestamp__gte=last_24h, action="CREATE"
        ).count(),
        "updates_24h": AuditLog.objects.filter(
            timestamp__gte=last_24h, action="UPDATE"
        ).count(),
        "deletes_24h": AuditLog.objects.filter(
            timestamp__gte=last_24h, action="DELETE"
        ).count(),
        "critical_24h": AuditLog.objects.filter(
            timestamp__gte=last_24h, severity="CRITICAL"
        ).count(),
    }

    # --- خيارات الفلاتر ---
    model_choices = (
        AuditLog.objects.exclude(model_name="")
        .values_list("model_name", flat=True)
        .distinct()
        .order_by("model_name")
    )
    user_choices = User.objects.filter(
        audit_logs__isnull=False
    ).distinct().order_by("username")

    # --- التصفح ---
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "stats": stats,
        "action_choices": AuditLog.ACTION_TYPES,
        "severity_choices": AuditLog.SEVERITY_LEVELS,
        "model_choices": model_choices,
        "user_choices": user_choices,
        # الفلاتر الحالية
        "current_action": action,
        "current_severity": severity,
        "current_user": user_id,
        "current_model": model_name,
        "current_search": search,
        "current_date_from": date_from,
        "current_date_to": date_to,
        "total_results": paginator.count,
    }

    return render(request, "core/audit_log_list.html", context)


@login_required
@user_passes_test(is_admin_or_manager, login_url="/accounts/login/")
def audit_log_detail(request, pk):
    """
    عرض تفاصيل سجل تدقيق واحد بالكامل مع التغييرات
    """
    log = get_object_or_404(AuditLog.objects.select_related("user"), pk=pk)
    context = {"log": log}
    return render(request, "core/audit_log_detail.html", context)


@login_required
@user_passes_test(is_admin_or_manager, login_url="/accounts/login/")
def audit_log_export(request):
    """
    تصدير سجلات التدقيق إلى CSV
    """
    queryset = AuditLog.objects.select_related("user").order_by("-timestamp")

    # تطبيق نفس الفلاتر
    action = request.GET.get("action", "")
    severity = request.GET.get("severity", "")
    user_id = request.GET.get("user", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if action:
        queryset = queryset.filter(action=action)
    if severity:
        queryset = queryset.filter(severity=severity)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if date_from:
        queryset = queryset.filter(timestamp__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(timestamp__date__lte=date_to)

    # حد أقصى 10000 سجل
    queryset = queryset[:10000]

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
    response.write("\ufeff")  # UTF-8 BOM for Excel Arabic

    writer = csv.writer(response)
    writer.writerow([
        "التاريخ", "المستخدم", "العملية", "الخطورة",
        "النموذج", "المعرف", "الوصف", "IP", "المسار",
    ])

    for log in queryset:
        writer.writerow([
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.username or (log.user.username if log.user else "نظام"),
            log.get_action_display(),
            log.get_severity_display(),
            log.model_name,
            log.object_id,
            log.description[:200],
            log.ip_address or "",
            log.url_path,
        ])

    return response


@login_required
@user_passes_test(is_admin_or_manager, login_url="/accounts/login/")
def audit_log_stats(request):
    """
    إحصائيات سجل التدقيق — JSON API لتحديث الرسوم البيانية
    """
    days = int(request.GET.get("days", 7))
    since = timezone.now() - timedelta(days=days)

    # عمليات حسب النوع
    by_action = list(
        AuditLog.objects.filter(timestamp__gte=since)
        .values("action")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # عمليات حسب اليوم
    from django.db.models.functions import TruncDate

    by_date = list(
        AuditLog.objects.filter(timestamp__gte=since)
        .annotate(date=TruncDate("timestamp"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    # تحويل التاريخ إلى نص
    for item in by_date:
        item["date"] = item["date"].isoformat()

    # أكثر المستخدمين نشاطاً
    by_user = list(
        AuditLog.objects.filter(timestamp__gte=since, user__isnull=False)
        .values("user__username")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # أكثر النماذج تعديلاً
    by_model = list(
        AuditLog.objects.filter(timestamp__gte=since)
        .exclude(model_name="")
        .values("model_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    return JsonResponse({
        "by_action": by_action,
        "by_date": by_date,
        "by_user": by_user,
        "by_model": by_model,
    })
