from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from .models import BulkUploadError, BulkUploadLog


@login_required
def bulk_upload_log_list(request):
    """
    عرض قائمة سجلات الرفع الجماعي
    """
    logs = BulkUploadLog.objects.all()

    # الفلترة حسب نوع العملية
    upload_type = request.GET.get("type")
    if upload_type in ["products", "stock_update"]:
        logs = logs.filter(upload_type=upload_type)

    # الفلترة حسب الحالة
    status = request.GET.get("status")
    if status in ["completed", "completed_with_errors", "failed", "processing"]:
        logs = logs.filter(status=status)

    # البحث
    search = request.GET.get("q")
    if search:
        logs = logs.filter(
            Q(file_name__icontains=search)
            | Q(summary__icontains=search)
            | Q(created_by__username__icontains=search)
        )

    # الترتيب
    logs = logs.order_by("-created_at")

    # الصفحات
    paginator = Paginator(logs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "upload_type": upload_type,
        "status": status,
        "search": search,
    }

    return render(request, "inventory/bulk_upload_log_list.html", context)


@login_required
def bulk_upload_report(request, log_id):
    """
    عرض تقرير مفصل لعملية رفع محددة
    """
    upload_log = get_object_or_404(BulkUploadLog, id=log_id)

    # الحصول على جميع النتائج (أخطاء + متخطاة)
    results = upload_log.errors.all()

    # الفلترة حسب نوع الخطأ
    error_type = request.GET.get("error_type")
    if error_type:
        results = results.filter(error_type=error_type)

    # الفلترة حسب حالة النتيجة
    result_status = request.GET.get("result_status")
    if result_status:
        results = results.filter(result_status=result_status)

    # الترتيب
    results = results.order_by("row_number")

    # الصفحات
    paginator = Paginator(results, 50)
    page_number = request.GET.get("page")
    results_page = paginator.get_page(page_number)

    # إحصائيات الأخطاء حسب النوع
    error_stats = {}
    for error in upload_log.errors.all():
        error_type_name = error.get_error_type_display()
        error_stats[error_type_name] = error_stats.get(error_type_name, 0) + 1

    # إحصائيات النتائج حسب الحالة (مع حساب لكل حالة)
    failed_count = upload_log.errors.filter(result_status="failed").count()
    skipped_count = upload_log.errors.filter(result_status="skipped").count()
    updated_count = upload_log.errors.filter(result_status="updated").count()
    created_count = upload_log.errors.filter(result_status="created").count()

    # إحصائيات النتائج حسب الحالة للعرض
    status_stats = {}
    for error in upload_log.errors.all():
        status_name = error.get_result_status_display()
        status_stats[status_name] = status_stats.get(status_name, 0) + 1

    # عدد الأخطاء الحقيقية فقط (failed)
    actual_errors_count = failed_count

    context = {
        "upload_log": upload_log,
        "results_page": results_page,
        "error_stats": error_stats,
        "status_stats": status_stats,
        "error_type": error_type,
        "result_status": result_status,
        "actual_errors_count": actual_errors_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "updated_count": updated_count,
        "created_count": created_count,
    }

    return render(request, "inventory/bulk_upload_report.html", context)


@login_required
def latest_bulk_upload_report(request, upload_type=None):
    """
    عرض تقرير آخر عملية رفع
    """
    query = BulkUploadLog.objects.all()

    if upload_type == "products":
        query = query.filter(upload_type="products")
    elif upload_type == "stock_update":
        query = query.filter(upload_type="stock_update")

    # الحصول على آخر عملية رفع للمستخدم الحالي
    upload_log = query.filter(created_by=request.user).first()

    if not upload_log:
        messages.info(request, _("لا توجد عمليات رفع سابقة"))
        return redirect("inventory:product_list")

    return redirect("inventory:bulk_upload_report", log_id=upload_log.id)


@login_required
def bulk_upload_error_detail(request, error_id):
    """
    عرض تفاصيل خطأ محدد
    """
    error = get_object_or_404(BulkUploadError, id=error_id)

    context = {
        "error": error,
        "upload_log": error.upload_log,
    }

    return render(request, "inventory/bulk_upload_error_detail.html", context)
