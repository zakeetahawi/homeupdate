"""
دوال الداشبورد والصفحات المنفصلة لقسم الطلبات
"""

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from accounts.models import SystemSettings

from .permissions import get_user_orders_queryset, get_user_role_permissions


def apply_year_filter(orders, request):
    """لا يطبق أي فلتر - تم إلغاء الفلترة الافتراضية"""
    return orders


def get_available_years():
    """الحصول على قائمة السنوات المتاحة"""
    from .models import Order

    years = Order.objects.dates("order_date", "year", order="DESC")
    return [year.year for year in years]


@login_required
def orders_dashboard(request):
    """داشبورد الطلبات الرئيسي"""
    # التحقق من صلاحيات المستخدم
    user_permissions = get_user_role_permissions(request.user)
    if not user_permissions.get("can_manage_dashboard", False):
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden("ليس لديك صلاحية للوصول إلى هذه الصفحة")

    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)

    # تطبيق فلتر السنة
    orders = apply_year_filter(orders, request)

    # إحصائيات البطاقات الأربع - محسنة للأداء
    from django.db.models import Case, IntegerField, When

    # استخدام annotate لتحسين الأداء بدلاً من استعلامات منفصلة
    orders_with_counts = orders.aggregate(
        inspection_count=Count("id", filter=Q(selected_types__icontains="inspection")),
        installation_count=Count(
            "id", filter=Q(selected_types__icontains="installation")
        ),
        accessory_count=Count("id", filter=Q(selected_types__icontains="accessory")),
        tailoring_count=Count("id", filter=Q(selected_types__icontains="tailoring")),
    )

    inspection_count = orders_with_counts["inspection_count"]
    installation_count = orders_with_counts["installation_count"]
    accessory_count = orders_with_counts["accessory_count"]
    tailoring_count = orders_with_counts["tailoring_count"]

    # إحصائيات عامة - محسنة للأداء باستخدام aggregate
    general_stats = orders.aggregate(
        total_orders=Count("id"),
        pending_orders=Count(
            "id", filter=Q(order_status__in=["pending", "pending_approval"])
        ),  # شمل قيد الموافقة
        in_progress_orders=Count("id", filter=Q(order_status="in_progress")),
        completed_orders=Count(
            "id", filter=Q(order_status__in=["completed", "delivered"])
        ),
        ready_install_orders=Count("id", filter=Q(order_status="ready_install")),
    )

    total_orders = general_stats["total_orders"]
    pending_orders = general_stats["pending_orders"]
    in_progress_orders = general_stats["in_progress_orders"]
    completed_orders = general_stats["completed_orders"]
    ready_install_orders = general_stats["ready_install_orders"]

    # إحصائيات المعاينات (للمطابقة مع جدول المعاينات)
    from inspections.models import Inspection

    pending_inspections_count = Inspection.objects.filter(status="pending").count()
    orders_with_pending_inspections = (
        orders.filter(inspections__status="pending").distinct().count()
    )
    orders_without_inspections = pending_orders - orders_with_pending_inspections

    # إجمالي الإيرادات - مسؤول المصنع فقط لا يرى الإيرادات
    if (
        hasattr(request.user, "is_factory_manager")
        and request.user.is_factory_manager
        and not request.user.is_superuser
    ):
        total_revenue = 0  # مسؤول المصنع لا يرى الإيرادات
    else:
        revenue_stats = orders.aggregate(total_revenue=Sum("total_amount"))
        total_revenue = revenue_stats["total_revenue"] or 0

    # أحدث الطلبات - محسنة مع select_related
    recent_orders = orders.select_related("customer", "salesperson", "branch").order_by(
        "-created_at"
    )[:10]

    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else "ج.م"

    # معلومات فلتر السنة
    available_years = get_available_years()
    selected_year = request.GET.get("year", "")

    # تحديد ما إذا كان يجب إخفاء الإيرادات - مسؤول المصنع فقط (وليس مدير النظام)
    hide_revenue = (
        hasattr(request.user, "is_factory_manager")
        and request.user.is_factory_manager
        and not request.user.is_superuser
    )

    context = {
        "inspection_count": inspection_count,
        "installation_count": installation_count,
        "accessory_count": accessory_count,
        "tailoring_count": tailoring_count,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "in_progress_orders": in_progress_orders,
        "completed_orders": completed_orders,
        "ready_install_orders": ready_install_orders,
        "total_revenue": total_revenue,
        "recent_orders": recent_orders,
        "currency_symbol": currency_symbol,
        "available_years": available_years,
        "selected_year": selected_year,
        "hide_revenue": hide_revenue,
        # إحصائيات المعاينات المطابقة
        "pending_inspections_count": pending_inspections_count,
        "orders_with_pending_inspections": orders_with_pending_inspections,
        "orders_without_inspections": orders_without_inspections,
    }

    return render(request, "orders/orders_dashboard.html", context)


@login_required
def inspection_orders(request):
    """صفحة طلبات المعاينة"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)

    # تصفية طلبات المعاينة فقط
    orders = orders.filter(selected_types__icontains="inspection")

    # تطبيق فلتر السنة
    orders = apply_year_filter(orders, request)

    # معالجة البحث والتصفية
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    page_size = request.GET.get("page_size", "25")

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(customer__phone__icontains=search_query)
        )

    if status_filter:
        orders = orders.filter(inspection_status=status_filter)

    # ترتيب وتقسيم الصفحات
    orders = orders.order_by("-created_at")

    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except Exception:
        page_size = 25

    paginator = Paginator(orders, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # إحصائيات
    total_count = orders.count()
    pending_count = orders.filter(
        inspection_status__in=["not_scheduled", "pending"]
    ).count()
    in_progress_count = orders.filter(inspection_status="in_progress").count()
    completed_count = orders.filter(inspection_status="completed").count()

    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else "ج.م"

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "total_count": total_count,
        "pending_count": pending_count,
        "in_progress_count": in_progress_count,
        "completed_count": completed_count,
        "currency_symbol": currency_symbol,
    }

    return render(request, "orders/inspection_orders.html", context)


@login_required
def installation_orders(request):
    """صفحة طلبات التركيب"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)

    # تصفية طلبات التركيب فقط
    orders = orders.filter(selected_types__icontains="installation")

    # تطبيق فلتر السنة
    orders = apply_year_filter(orders, request)

    # معالجة البحث والتصفية
    search_query = request.GET.get("search", "")
    installation_status_filter = request.GET.get("installation_status", "")
    page_size = request.GET.get("page_size", "25")

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(customer__phone__icontains=search_query)
        )

    if installation_status_filter:
        orders = orders.filter(installation_status=installation_status_filter)

    # ترتيب وتقسيم الصفحات
    orders = orders.order_by("-created_at")

    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except Exception:
        page_size = 25

    paginator = Paginator(orders, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # إحصائيات
    total_count = orders.count()
    needs_scheduling_count = orders.filter(
        installation_status="needs_scheduling"
    ).count()
    in_installation_count = orders.filter(installation_status="in_installation").count()
    completed_count = orders.filter(installation_status="completed").count()

    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else "ج.م"

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "installation_status_filter": installation_status_filter,
        "total_count": total_count,
        "needs_scheduling_count": needs_scheduling_count,
        "in_installation_count": in_installation_count,
        "completed_count": completed_count,
        "currency_symbol": currency_symbol,
    }

    return render(request, "orders/installation_orders.html", context)


@login_required
def accessory_orders(request):
    """صفحة طلبات الإكسسوار"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)

    # تصفية طلبات الإكسسوار فقط
    orders = orders.filter(selected_types__icontains="accessory")

    # تطبيق فلتر السنة
    orders = apply_year_filter(orders, request)

    # معالجة البحث والتصفية
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    page_size = request.GET.get("page_size", "25")

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(customer__phone__icontains=search_query)
        )

    if status_filter:
        orders = orders.filter(order_status=status_filter)

    # ترتيب وتقسيم الصفحات
    orders = orders.order_by("-created_at")

    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except Exception:
        page_size = 25

    paginator = Paginator(orders, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # إحصائيات
    total_count = orders.count()
    pending_count = orders.filter(order_status__in=["pending", "pending_approval"]).count()
    ready_count = orders.filter(order_status__in=["ready_install", "completed"]).count()
    delivered_count = orders.filter(order_status="delivered").count()

    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else "ج.م"

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "total_count": total_count,
        "pending_count": pending_count,
        "ready_count": ready_count,
        "delivered_count": delivered_count,
        "currency_symbol": currency_symbol,
    }

    return render(request, "orders/accessory_orders.html", context)


@login_required
def tailoring_orders(request):
    """صفحة طلبات التسليم"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)

    # تصفية طلبات التسليم فقط
    orders = orders.filter(selected_types__icontains="tailoring")

    # تطبيق فلتر السنة
    orders = apply_year_filter(orders, request)

    # معالجة البحث والتصفية
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    delivery_type_filter = request.GET.get("delivery_type", "")
    contract_filter = request.GET.get("contract", "")
    page_size = request.GET.get("page_size", "25")

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(customer__phone__icontains=search_query)
        )

    if status_filter:
        orders = orders.filter(order_status=status_filter)

    if delivery_type_filter:
        orders = orders.filter(delivery_type=delivery_type_filter)

    if contract_filter:
        orders = orders.filter(contract_number__icontains=contract_filter)

    # ترت��ب وتقسيم الصفحات
    orders = orders.order_by("-created_at")

    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except Exception:
        page_size = 25

    paginator = Paginator(orders, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # إحصائيات
    total_count = orders.count()
    in_progress_count = orders.filter(
        order_status__in=["pending_approval", "pending", "in_progress"]
    ).count()
    ready_count = orders.filter(order_status__in=["ready_install", "completed"]).count()
    delivered_count = orders.filter(order_status="delivered").count()

    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else "ج.م"

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "delivery_type_filter": delivery_type_filter,
        "contract_filter": contract_filter,
        "total_count": total_count,
        "in_progress_count": in_progress_count,
        "ready_count": ready_count,
        "delivered_count": delivered_count,
        "currency_symbol": currency_symbol,
    }

    return render(request, "orders/tailoring_orders.html", context)
