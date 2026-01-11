"""
دوال مساعدة محسنة لداشبورد الإدارة - مصححة
"""

from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    F,
    IntegerField,
    Max,
    Q,
    Sum,
    When,
)
from django.db.models.functions import ExtractMonth, ExtractYear, TruncDate
from django.utils import timezone

from accounts.models import Branch, DashboardYearSettings
from complaints.models import Complaint, ComplaintType
from customers.models import Customer
from inspections.models import Inspection
from installations.models import InstallationSchedule
from inventory.models import Product
from manufacturing.models import ManufacturingOrder
from orders.models import Order


def get_customers_statistics(
    branch_filter, start_date=None, end_date=None, show_all_years=False
):
    """إحصائيات العملاء المحسنة"""
    customers = Customer.objects.all()

    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        customers = customers.filter(created_at__range=(start_date, end_date))

    # فلترة حسب الفرع
    if branch_filter != "all":
        customers = customers.filter(branch_id=branch_filter)

    # إحصائيات متقدمة
    stats = customers.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status="active")),
        inactive=Count("id", filter=Q(status="inactive")),
        individual=Count("id", filter=Q(customer_type="individual")),
        company=Count("id", filter=Q(customer_type="company")),
    )

    # العملاء الجدد هذا الشهر
    current_month_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    new_this_month = customers.filter(created_at__gte=current_month_start).count()

    # توزيع العملاء حسب الفرع والفئة
    by_branch = (
        customers.values("branch__name").annotate(count=Count("id")).order_by("-count")
    )
    by_category = (
        customers.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return {
        **stats,
        "new_this_month": new_this_month,
        "by_branch": list(by_branch),
        "by_category": list(by_category),
        "growth_rate": calculate_growth_rate(customers, "created_at"),
    }


def get_orders_statistics(branch_filter, start_date, end_date, show_all_years=False):
    """إحصائيات الطلبات المحسنة"""
    orders = Order.objects.all()

    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        orders = orders.filter(order_date__range=(start_date, end_date))

    # فلترة حسب الفرع
    if branch_filter != "all":
        orders = orders.filter(branch_id=branch_filter)

    # إحصائيات متقدمة
    stats = orders.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(order_status="pending")),
        pending_approval=Count("id", filter=Q(order_status="pending_approval")),
        in_progress=Count("id", filter=Q(order_status="in_progress")),
        ready_install=Count("id", filter=Q(order_status="ready_install")),
        completed=Count("id", filter=Q(order_status="completed")),
        delivered=Count("id", filter=Q(order_status="delivered")),
        cancelled=Count("id", filter=Q(order_status="cancelled")),
        rejected=Count("id", filter=Q(order_status="rejected")),
        total_amount=Sum("total_amount"),
    )

    # حساب المتوسط يدوياً لتجنب خطأ Avg على Sum
    avg_amount = 0
    if stats["total"] > 0 and stats["total_amount"]:
        avg_amount = stats["total_amount"] / stats["total"]

    # إحصائيات حسب النوع
    by_type = (
        orders.values("selected_types").annotate(count=Count("id")).order_by("-count")
    )

    # معدل الإتمام
    completion_rate = 0
    if stats["total"] > 0:
        completed_count = (stats["completed"] or 0) + (stats["delivered"] or 0)
        completion_rate = (completed_count / stats["total"]) * 100

    return {
        **stats,
        "avg_amount": round(avg_amount, 2),
        "by_type": list(by_type),
        "completion_rate": round(completion_rate, 1),
    }


def get_manufacturing_statistics(
    branch_filter, start_date, end_date, show_all_years=False
):
    """إحصائيات التصنيع المحسنة"""
    manufacturing_orders = ManufacturingOrder.objects.select_related("order")

    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        manufacturing_orders = manufacturing_orders.filter(
            order__order_date__range=(start_date, end_date)
        )

    # فلترة حسب الفرع
    if branch_filter != "all":
        manufacturing_orders = manufacturing_orders.filter(
            order__branch_id=branch_filter
        )

    # إحصائيات متقدمة
    stats = manufacturing_orders.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        completed=Count("id", filter=Q(status="completed")),
        delivered=Count("id", filter=Q(status="delivered")),
        cancelled=Count("id", filter=Q(status="cancelled")),
        total_amount=Sum("order__total_amount"),
    )

    # إحصائيات حسب النوع
    by_type = (
        manufacturing_orders.values("order_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return {
        **stats,
        "by_type": list(by_type),
    }


def get_inspections_statistics(
    branch_filter, start_date, end_date, show_all_years=False
):
    """إحصائيات المعاينات المحسنة"""
    inspections = Inspection.objects.all()

    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        inspections = inspections.filter(created_at__range=(start_date, end_date))

    # فلترة حسب الفرع
    if branch_filter != "all":
        inspections = inspections.filter(branch_id=branch_filter)

    # إحصائيات متقدمة
    stats = inspections.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        scheduled=Count("id", filter=Q(status="scheduled")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        completed=Count("id", filter=Q(status="completed")),
        cancelled=Count("id", filter=Q(status="cancelled")),
        successful=Count("id", filter=Q(result="passed")),
        failed=Count("id", filter=Q(result="failed")),
    )

    # معدل النجاح
    success_rate = 0
    if stats["total"] > 0:
        success_rate = ((stats["successful"] or 0) / stats["total"]) * 100

    return {
        **stats,
        "success_rate": round(success_rate, 1),
    }


def get_installation_orders_statistics(
    branch_filter, start_date, end_date, show_all_years=False
):
    """إحصائيات طلبات التركيب المحسنة"""
    # البحث في الطلبات التي تحتوي على تركيب - محسن
    orders = Order.objects.filter(selected_types__icontains="installation")

    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        orders = orders.filter(order_date__range=(start_date, end_date))

    # فلترة حسب الفرع
    if branch_filter != "all":
        orders = orders.filter(branch_id=branch_filter)

    # إحصائيات متقدمة
    stats = orders.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(order_status="pending")),
        in_progress=Count("id", filter=Q(order_status="in_progress")),
        ready_install=Count("id", filter=Q(order_status="ready_install")),
        completed=Count("id", filter=Q(order_status="completed")),
        delivered=Count("id", filter=Q(order_status="delivered")),
        cancelled=Count("id", filter=Q(order_status="cancelled")),
        total_amount=Sum("total_amount"),
    )

    return stats


def get_installations_statistics(
    branch_filter, start_date, end_date, show_all_years=False
):
    """إحصائيات التركيبات الفعلية المحسنة"""
    try:
        installations = InstallationSchedule.objects.all()

        # تطبيق فلتر التاريخ
        if not show_all_years and start_date and end_date:
            installations = installations.filter(
                created_at__range=(start_date, end_date)
            )

        # فلترة حسب الفرع
        if branch_filter != "all":
            installations = installations.filter(order__branch_id=branch_filter)

        # إحصائيات متقدمة
        stats = installations.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="pending")),
            scheduled=Count("id", filter=Q(status="scheduled")),
            in_installation=Count("id", filter=Q(status="in_installation")),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
        )

        return stats
    except Exception:
        # في حالة عدم وجود نموذج التركيبات
        return {
            "total": 0,
            "pending": 0,
            "scheduled": 0,
            "in_installation": 0,
            "completed": 0,
            "cancelled": 0,
        }


def get_inventory_statistics(branch_filter):
    """إحصائيات المخزون المحسنة - سريعة جداً"""
    # فلترة المنتجات
    products_filter = {}
    if branch_filter != "all" and hasattr(Product, "branch"):
        products_filter["branch_id"] = branch_filter

    # إحصائيات مبسطة - بدون استخدام current_stock (property)
    total_products = Product.objects.filter(**products_filter).count()

    # حساب المخزون المنخفض والمنتهي بطريقة مبسطة
    # يمكن تحسينها لاحقاً عند الحاجة
    low_stock_products = 0
    out_of_stock_products = 0

    # حساب المخزون للمنتجات (يمكن تحسينها لاحقاً)
    for product in Product.objects.filter(**products_filter)[:100]:  # عينة من 100 منتج
        try:
            current_stock = product.current_stock
            if current_stock <= 0:
                out_of_stock_products += 1
            elif current_stock <= product.minimum_stock:
                low_stock_products += 1
        except:
            pass

    return {
        "total_products": total_products,
        "active_products": total_products,  # جميع المنتجات تعتبر نشطة
        "inactive_products": 0,  # لا يوجد منتجات غير نشطة
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
    }


def get_enhanced_chart_data(branch_filter, selected_year, show_all_years=False):
    """البيانات المحسنة للرسوم البيانية"""
    if show_all_years or selected_year == "all":
        # عرض البيانات لجميع السنوات
        return get_multi_year_chart_data(branch_filter)
    else:
        # عرض البيانات لسنة محددة
        return get_single_year_chart_data(branch_filter, selected_year)


def get_single_year_chart_data(branch_filter, year):
    """بيانات الرسوم البيانية لسنة واحدة - محسّن بدون SQL injection"""
    # بيانات شهرية للطلبات
    orders_monthly = Order.objects.filter(order_date__year=year)
    if branch_filter != "all":
        orders_monthly = orders_monthly.filter(branch_id=branch_filter)

    orders_by_month = (
        orders_monthly.annotate(month=ExtractMonth("order_date"))
        .values("month")
        .annotate(count=Count("id"), amount=Sum("total_amount"))
        .order_by("month")
    )

    # بيانات شهرية للعملاء
    customers_monthly = Customer.objects.filter(created_at__year=year)
    if branch_filter != "all":
        customers_monthly = customers_monthly.filter(branch_id=branch_filter)

    customers_by_month = (
        customers_monthly.annotate(month=ExtractMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # بيانات شهرية للمعاينات
    inspections_monthly = Inspection.objects.filter(created_at__year=year)
    if branch_filter != "all":
        inspections_monthly = inspections_monthly.filter(branch_id=branch_filter)

    inspections_by_month = (
        inspections_monthly.annotate(month=ExtractMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    return {
        "orders_by_month": list(orders_by_month),
        "customers_by_month": list(customers_by_month),
        "inspections_by_month": list(inspections_by_month),
        "type": "monthly",
        "year": year,
    }


def get_multi_year_chart_data(branch_filter):
    """بيانات الرسوم البيانية لعدة سنوات - محسّن بدون SQL injection"""
    # بيانات سنوية للطلبات
    orders_yearly = Order.objects.all()
    if branch_filter != "all":
        orders_yearly = orders_yearly.filter(branch_id=branch_filter)

    orders_by_year = (
        orders_yearly.annotate(year=ExtractYear("order_date"))
        .values("year")
        .annotate(count=Count("id"), amount=Sum("total_amount"))
        .order_by("year")
    )

    # بيانات سنوية للعملاء
    customers_yearly = Customer.objects.all()
    if branch_filter != "all":
        customers_yearly = customers_yearly.filter(branch_id=branch_filter)

    customers_by_year = (
        customers_yearly.annotate(year=ExtractYear("created_at"))
        .values("year")
        .annotate(count=Count("id"))
        .order_by("year")
    )

    # بيانات سنوية للمعاينات
    inspections_yearly = Inspection.objects.all()
    if branch_filter != "all":
        inspections_yearly = inspections_yearly.filter(branch_id=branch_filter)

    inspections_by_year = (
        inspections_yearly.annotate(year=ExtractYear("created_at"))
        .values("year")
        .annotate(count=Count("id"))
        .order_by("year")
    )

    return {
        "orders_by_year": list(orders_by_year),
        "customers_by_year": list(customers_by_year),
        "inspections_by_year": list(inspections_by_year),
        "type": "yearly",
    }


def calculate_growth_rate(queryset, date_field):
    """حساب معدل النمو"""
    try:
        current_month = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        last_month = (current_month - timedelta(days=1)).replace(day=1)

        current_count = queryset.filter(**{f"{date_field}__gte": current_month}).count()
        last_count = queryset.filter(
            **{f"{date_field}__gte": last_month, f"{date_field}__lt": current_month}
        ).count()

        if last_count > 0:
            growth_rate = ((current_count - last_count) / last_count) * 100
            return round(growth_rate, 1)
        return 0
    except Exception:
        return 0


def get_dashboard_summary(stats):
    """ملخص الداشبورد"""
    try:
        total_revenue = stats["orders_stats"]["total_amount"] or 0
        total_orders = stats["orders_stats"]["total"] or 0
        total_customers = stats["customers_stats"]["total"] or 0

        avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_customers": total_customers,
            "avg_order_value": round(avg_order_value, 2),
        }
    except Exception:
        return {
            "total_revenue": 0,
            "total_orders": 0,
            "total_customers": 0,
            "avg_order_value": 0,
        }


def get_complaints_statistics(
    branch_filter, start_date=None, end_date=None, show_all_years=False
):
    """إحصائيات الشكاوى"""
    complaints = Complaint.objects.all()

    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        complaints = complaints.filter(created_at__range=(start_date, end_date))

    # فلترة حسب الفرع
    if branch_filter != "all":
        complaints = complaints.filter(branch_id=branch_filter)

    # إحصائيات متقدمة
    stats = complaints.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        resolved=Count("id", filter=Q(status="resolved")),
        closed=Count("id", filter=Q(status="closed")),
        urgent=Count("id", filter=Q(priority="urgent")),
        high=Count("id", filter=Q(priority="high")),
        medium=Count("id", filter=Q(priority="medium")),
        low=Count("id", filter=Q(priority="low")),
    )

    # الشكاوى الجديدة هذا الشهر
    current_month_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    new_this_month = complaints.filter(created_at__gte=current_month_start).count()

    # الشكاوى المتأخرة
    overdue = complaints.filter(
        deadline__lt=timezone.now(), status__in=["pending", "in_progress"]
    ).count()

    # توزيع الشكاوى حسب النوع
    by_type = (
        complaints.values("complaint_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # الشكاوى حسب الأسبوع (آخر 4 أسابيع)
    weekly_stats = []
    for i in range(4):
        week_start = timezone.now() - timedelta(weeks=i + 1)
        week_end = timezone.now() - timedelta(weeks=i)
        week_count = complaints.filter(created_at__range=(week_start, week_end)).count()
        weekly_stats.append({"week": f"الأسبوع {i+1}", "count": week_count})

    return {
        **stats,
        "new_this_month": new_this_month,
        "overdue": overdue,
        "by_type": list(by_type),
        "weekly_stats": weekly_stats,
        "resolution_rate": calculate_resolution_rate(complaints),
        "growth_rate": calculate_growth_rate(complaints, "created_at"),
    }


def calculate_resolution_rate(complaints):
    """حساب معدل حل الشكاوى"""
    try:
        total = complaints.count()
        resolved = complaints.filter(status__in=["resolved", "closed"]).count()

        if total > 0:
            return round((resolved / total) * 100, 1)
        return 0
    except Exception:
        return 0


def get_manufacturing_approval_analytics(branch_filter, start_date=None, end_date=None):
    """تحليلات متقدمة لأوقات الموافقة على طلبات التصنيع"""
    manufacturing_orders = ManufacturingOrder.objects.select_related(
        "order", "created_by"
    )

    # تطبيق فلاتر التاريخ والفرع
    if start_date and end_date:
        manufacturing_orders = manufacturing_orders.filter(
            created_at__range=(start_date, end_date)
        )

    if branch_filter != "all":
        manufacturing_orders = manufacturing_orders.filter(
            order__branch_id=branch_filter
        )

    # حساب الأوقات المستغرقة للموافقة (استخدام completion_date كبديل لـ approved_at)
    # الأوامر التي تم الانتهاء منها أو التي تم إكمالها
    completed_orders = manufacturing_orders.filter(
        Q(status__in=["completed", "ready_install", "delivered"])
        | Q(completion_date__isnull=False)
    )

    approval_times = []
    detailed_approvals = []

    for order in completed_orders:
        # استخدام completion_date أو updated_at كبديل لـ approved_at
        approval_date = order.completion_date or order.updated_at
        if approval_date and order.created_at:
            time_diff = approval_date - order.created_at
            hours = time_diff.total_seconds() / 3600
            approval_times.append(hours)

            detailed_approvals.append(
                {
                    "order_id": order.id,
                    "order_number": getattr(
                        order.order, "order_number", f"ORD-{order.order.id}"
                    ),
                    "created_at": order.created_at,
                    "approved_at": approval_date,
                    "approval_time_hours": round(hours, 2),
                    "created_by": (
                        order.created_by.get_full_name()
                        if order.created_by
                        else "غير محدد"
                    ),
                    "approved_by": "النظام",  # بما أنه لا يوجد حقل approved_by
                    "status": order.status,
                    "priority": "عادي",  # بما أنه لا يوجد حقل priority
                }
            )

    # حساب الإحصائيات
    avg_approval_time = (
        sum(approval_times) / len(approval_times) if approval_times else 0
    )
    min_approval_time = min(approval_times) if approval_times else 0
    max_approval_time = max(approval_times) if approval_times else 0

    # توزيع الأوقات
    quick_approvals = len([t for t in approval_times if t <= 24])  # أقل من 24 ساعة
    medium_approvals = len([t for t in approval_times if 24 < t <= 72])  # 1-3 أيام
    slow_approvals = len([t for t in approval_times if t > 72])  # أكثر من 3 أيام

    # إحصائيات حسب المستخدم (استخدام created_by)
    approval_by_user = {}
    for order in completed_orders:
        if order.created_by:
            user_name = order.created_by.get_full_name()
            if user_name not in approval_by_user:
                approval_by_user[user_name] = {
                    "count": 0,
                    "total_time": 0,
                    "orders": [],
                }

            approval_date = order.completion_date or order.updated_at
            if approval_date and order.created_at:
                time_diff = (approval_date - order.created_at).total_seconds() / 3600
                approval_by_user[user_name]["count"] += 1
                approval_by_user[user_name]["total_time"] += time_diff
                approval_by_user[user_name]["orders"].append(
                    {"order_id": order.id, "approval_time": round(time_diff, 2)}
                )

    # حساب متوسط الوقت لكل مستخدم
    for user_data in approval_by_user.values():
        user_data["avg_time"] = (
            round(user_data["total_time"] / user_data["count"], 2)
            if user_data["count"] > 0
            else 0
        )

    return {
        "total_orders": manufacturing_orders.count(),
        "approved_orders": completed_orders.count(),
        "pending_approval": manufacturing_orders.filter(
            status="pending_approval"
        ).count(),
        "avg_approval_time_hours": round(avg_approval_time, 2),
        "min_approval_time_hours": round(min_approval_time, 2),
        "max_approval_time_hours": round(max_approval_time, 2),
        "quick_approvals": quick_approvals,
        "medium_approvals": medium_approvals,
        "slow_approvals": slow_approvals,
        "approval_by_user": approval_by_user,
        "detailed_approvals": detailed_approvals[:20],  # أحدث 20 موافقة
    }


def get_inspection_scheduling_analytics(branch_filter, start_date=None, end_date=None):
    """تحليلات متقدمة لأوقات جدولة المعاينات"""
    inspections = Inspection.objects.select_related(
        "customer", "inspector", "created_by"
    )

    # تطبيق فلاتر التاريخ والفرع
    if start_date and end_date:
        inspections = inspections.filter(created_at__range=(start_date, end_date))

    if branch_filter != "all":
        inspections = inspections.filter(branch_id=branch_filter)

    # حساب الأوقات المستغرقة للجدولة
    scheduled_inspections = inspections.exclude(scheduled_date__isnull=True)

    scheduling_times = []
    detailed_scheduling = []

    for inspection in scheduled_inspections:
        if inspection.scheduled_date and inspection.created_at:
            # حساب الوقت بين إنشاء المعاينة وجدولتها
            # تحويل scheduled_date من DateField إلى datetime للمقارنة
            scheduled_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    inspection.scheduled_date, timezone.datetime.min.time()
                )
            )

            time_diff = scheduled_datetime - inspection.created_at
            hours = time_diff.total_seconds() / 3600
            scheduling_times.append(hours)

            detailed_scheduling.append(
                {
                    "inspection_id": inspection.id,
                    "customer_name": (
                        inspection.customer.name if inspection.customer else "غير محدد"
                    ),
                    "created_at": inspection.created_at,
                    "scheduled_date": inspection.scheduled_date,
                    "scheduling_time_hours": round(hours, 2),
                    "created_by": (
                        inspection.created_by.get_full_name()
                        if inspection.created_by
                        else "غير محدد"
                    ),
                    "assigned_to": (
                        inspection.inspector.get_full_name()
                        if inspection.inspector
                        else "غير مخصص"
                    ),
                    "status": inspection.status,
                    "priority": "عادي",  # بما أنه لا يوجد حقل priority
                }
            )

    # حساب الإحصائيات
    avg_scheduling_time = (
        sum(scheduling_times) / len(scheduling_times) if scheduling_times else 0
    )
    min_scheduling_time = min(scheduling_times) if scheduling_times else 0
    max_scheduling_time = max(scheduling_times) if scheduling_times else 0

    # توزيع الأوقات
    quick_scheduling = len([t for t in scheduling_times if t <= 24])  # أقل من 24 ساعة
    medium_scheduling = len([t for t in scheduling_times if 24 < t <= 72])  # 1-3 أيام
    slow_scheduling = len([t for t in scheduling_times if t > 72])  # أكثر من 3 أيام

    # إحصائيات حسب المستخدم المسؤول
    scheduling_by_user = {}
    for inspection in scheduled_inspections:
        responsible_user = inspection.inspector or inspection.created_by
        if responsible_user:
            user_name = responsible_user.get_full_name()
            if user_name not in scheduling_by_user:
                scheduling_by_user[user_name] = {
                    "count": 0,
                    "total_time": 0,
                    "inspections": [],
                }

            if inspection.scheduled_date and inspection.created_at:
                scheduled_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        inspection.scheduled_date, timezone.datetime.min.time()
                    )
                )

                time_diff = (
                    scheduled_datetime - inspection.created_at
                ).total_seconds() / 3600
                scheduling_by_user[user_name]["count"] += 1
                scheduling_by_user[user_name]["total_time"] += time_diff
                scheduling_by_user[user_name]["inspections"].append(
                    {
                        "inspection_id": inspection.id,
                        "scheduling_time": round(time_diff, 2),
                    }
                )

    # حساب متوسط الوقت لكل مستخدم
    for user_data in scheduling_by_user.values():
        user_data["avg_time"] = (
            round(user_data["total_time"] / user_data["count"], 2)
            if user_data["count"] > 0
            else 0
        )

    return {
        "total_inspections": inspections.count(),
        "scheduled_inspections": scheduled_inspections.count(),
        "pending_scheduling": inspections.filter(scheduled_date__isnull=True).count(),
        "avg_scheduling_time_hours": round(avg_scheduling_time, 2),
        "min_scheduling_time_hours": round(min_scheduling_time, 2),
        "max_scheduling_time_hours": round(max_scheduling_time, 2),
        "quick_scheduling": quick_scheduling,
        "medium_scheduling": medium_scheduling,
        "slow_scheduling": slow_scheduling,
        "scheduling_by_user": scheduling_by_user,
        "detailed_scheduling": detailed_scheduling[:20],  # أحدث 20 جدولة
    }

    # تطبيق فلاتر التاريخ والفرع
    if start_date and end_date:
        inspections = inspections.filter(created_at__range=(start_date, end_date))

    if branch_filter != "all":
        inspections = inspections.filter(branch_id=branch_filter)

    # حساب الأوقات المستغرقة للجدولة
    scheduled_inspections = inspections.exclude(scheduled_date__isnull=True)

    scheduling_times = []
    detailed_scheduling = []

    for inspection in scheduled_inspections:
        if inspection.scheduled_date and inspection.created_at:
            # حساب الوقت بين إنشاء المعاينة وجدولتها
            if hasattr(inspection.scheduled_date, "date"):
                scheduled_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        inspection.scheduled_date, timezone.datetime.min.time()
                    )
                )
            else:
                scheduled_datetime = inspection.scheduled_date

            time_diff = scheduled_datetime - inspection.created_at
            hours = time_diff.total_seconds() / 3600
            scheduling_times.append(hours)

            detailed_scheduling.append(
                {
                    "inspection_id": inspection.id,
                    "customer_name": (
                        inspection.customer.name if inspection.customer else "غير محدد"
                    ),
                    "created_at": inspection.created_at,
                    "scheduled_date": inspection.scheduled_date,
                    "scheduling_time_hours": round(hours, 2),
                    "created_by": (
                        inspection.created_by.get_full_name()
                        if inspection.created_by
                        else "غير محدد"
                    ),
                    "assigned_to": (
                        inspection.assigned_to.get_full_name()
                        if inspection.assigned_to
                        else "غير مخصص"
                    ),
                    "status": inspection.status,
                    "priority": getattr(inspection, "priority", "عادي"),
                }
            )

    # حساب الإحصائيات
    avg_scheduling_time = (
        sum(scheduling_times) / len(scheduling_times) if scheduling_times else 0
    )
    min_scheduling_time = min(scheduling_times) if scheduling_times else 0
    max_scheduling_time = max(scheduling_times) if scheduling_times else 0

    # توزيع الأوقات
    quick_scheduling = len([t for t in scheduling_times if t <= 24])  # أقل من 24 ساعة
    medium_scheduling = len([t for t in scheduling_times if 24 < t <= 72])  # 1-3 أيام
    slow_scheduling = len([t for t in scheduling_times if t > 72])  # أكثر من 3 أيام

    # إحصائيات حسب المستخدم المسؤول
    scheduling_by_user = {}
    for inspection in scheduled_inspections:
        responsible_user = inspection.assigned_to or inspection.created_by
        if responsible_user:
            user_name = responsible_user.get_full_name()
            if user_name not in scheduling_by_user:
                scheduling_by_user[user_name] = {
                    "count": 0,
                    "total_time": 0,
                    "inspections": [],
                }

            if inspection.scheduled_date and inspection.created_at:
                if hasattr(inspection.scheduled_date, "date"):
                    scheduled_datetime = timezone.make_aware(
                        timezone.datetime.combine(
                            inspection.scheduled_date, timezone.datetime.min.time()
                        )
                    )
                else:
                    scheduled_datetime = inspection.scheduled_date

                time_diff = (
                    scheduled_datetime - inspection.created_at
                ).total_seconds() / 3600
                scheduling_by_user[user_name]["count"] += 1
                scheduling_by_user[user_name]["total_time"] += time_diff
                scheduling_by_user[user_name]["inspections"].append(
                    {
                        "inspection_id": inspection.id,
                        "scheduling_time": round(time_diff, 2),
                    }
                )

    # حساب متوسط الوقت لكل مستخدم
    for user_data in scheduling_by_user.values():
        user_data["avg_time"] = (
            round(user_data["total_time"] / user_data["count"], 2)
            if user_data["count"] > 0
            else 0
        )

    return {
        "total_inspections": inspections.count(),
        "scheduled_inspections": scheduled_inspections.count(),
        "pending_scheduling": inspections.filter(scheduled_date__isnull=True).count(),
        "avg_scheduling_time_hours": round(avg_scheduling_time, 2),
        "min_scheduling_time_hours": round(min_scheduling_time, 2),
        "max_scheduling_time_hours": round(max_scheduling_time, 2),
        "quick_scheduling": quick_scheduling,
        "medium_scheduling": medium_scheduling,
        "slow_scheduling": slow_scheduling,
        "scheduling_by_user": scheduling_by_user,
        "detailed_scheduling": detailed_scheduling[:20],  # أحدث 20 جدولة
    }


def get_user_performance_analytics(branch_filter, start_date=None, end_date=None):
    """تحليلات أداء المستخدمين بالتفصيل"""
    users_performance = {}

    # أداء المستخدمين في الموافقة على أوامر التصنيع
    manufacturing_analytics = get_manufacturing_approval_analytics(
        branch_filter, start_date, end_date
    )

    # أداء المستخدمين في جدولة المعاينات
    inspection_analytics = get_inspection_scheduling_analytics(
        branch_filter, start_date, end_date
    )

    # دمج بيانات الأداء
    all_users = set(manufacturing_analytics["approval_by_user"].keys()) | set(
        inspection_analytics["scheduling_by_user"].keys()
    )

    for user_name in all_users:
        users_performance[user_name] = {
            "manufacturing_approvals": manufacturing_analytics["approval_by_user"].get(
                user_name, {"count": 0, "avg_time": 0, "total_time": 0}
            ),
            "inspection_scheduling": inspection_analytics["scheduling_by_user"].get(
                user_name, {"count": 0, "avg_time": 0, "total_time": 0}
            ),
        }

        # حساب إجمالي للأداء
        total_tasks = (
            users_performance[user_name]["manufacturing_approvals"]["count"]
            + users_performance[user_name]["inspection_scheduling"]["count"]
        )
        total_time = (
            users_performance[user_name]["manufacturing_approvals"]["total_time"]
            + users_performance[user_name]["inspection_scheduling"]["total_time"]
        )

        users_performance[user_name]["total_tasks"] = total_tasks
        users_performance[user_name]["overall_avg_time"] = (
            round(total_time / total_tasks, 2) if total_tasks > 0 else 0
        )

    return {
        "users_performance": users_performance,
        "manufacturing_analytics": manufacturing_analytics,
        "inspection_analytics": inspection_analytics,
    }


def get_user_activity_analytics(days=7):
    """تحليل نشاط المستخدمين خلال الأيام الماضية"""
    from datetime import timedelta

    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from customers.models import Customer
    from orders.models import Order

    User = get_user_model()
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # الحصول على جميع المستخدمين
    all_users = User.objects.filter(is_active=True, is_staff=True)

    # المستخدمون النشطون (قاموا بإنشاء عملاء أو طلبات)
    active_users = []
    inactive_users = []

    user_activities = {}

    for user in all_users:
        # عدد العملاء الجدد
        customers_created = Customer.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()

        # عدد الطلبات الجديدة
        orders_created = Order.objects.filter(
            created_by=user, order_date__range=(start_date.date(), end_date.date())
        ).count()

        # عدد المعاينات المنشأة
        inspections_created = Inspection.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()

        total_activity = customers_created + orders_created + inspections_created

        user_data = {
            "user": user,
            "customers_created": customers_created,
            "orders_created": orders_created,
            "inspections_created": inspections_created,
            "total_activity": total_activity,
            "last_login": user.last_login,
            "is_active_period": total_activity > 0,
        }

        user_activities[user.id] = user_data

        if total_activity > 0:
            active_users.append(user_data)
        else:
            inactive_users.append(user_data)

    # ترتيب المستخدمين النشطين حسب النشاط
    active_users.sort(key=lambda x: x["total_activity"], reverse=True)

    # إحصائيات إجمالية
    total_customers_by_active = sum(user["customers_created"] for user in active_users)
    total_orders_by_active = sum(user["orders_created"] for user in active_users)
    total_inspections_by_active = sum(
        user["inspections_created"] for user in active_users
    )

    return {
        "period_days": days,
        "start_date": start_date,
        "end_date": end_date,
        "active_users": active_users[:10],  # أعلى 10 مستخدمين نشاطاً
        "inactive_users": inactive_users,
        "active_users_count": len(active_users),
        "inactive_users_count": len(inactive_users),
        "total_users": len(all_users),
        "total_customers_by_active": total_customers_by_active,
        "total_orders_by_active": total_orders_by_active,
        "total_inspections_by_active": total_inspections_by_active,
        "activity_rate": (
            round((len(active_users) / len(all_users)) * 100, 1) if all_users else 0
        ),
    }


def get_installation_order_scheduling_analytics(
    branch_filter, start_date=None, end_date=None
):
    """تحليل أوقات جدولة طلبات التركيب"""
    from orders.models import Order

    # طلبات التركيب
    installation_orders = Order.objects.filter(
        Q(selected_types__icontains="installation")
        | Q(service_types__contains=["installation"])
        | Q(service_types__icontains="installation")
    ).select_related("customer", "created_by")

    # تطبيق الفلاتر
    if start_date and end_date:
        installation_orders = installation_orders.filter(
            order_date__range=(start_date.date(), end_date.date())
        )

    if branch_filter != "all":
        installation_orders = installation_orders.filter(branch_id=branch_filter)

    scheduling_times = []
    detailed_scheduling = []

    for order in installation_orders:
        try:
            # استخدام حقل installation_date إذا كان متاحاً في الطلب
            if hasattr(order, "installation_date") and order.installation_date:
                # حساب الوقت بين إنشاء الطلب وجدولته
                order_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        order.order_date, timezone.datetime.min.time()
                    )
                )

                if hasattr(order.installation_date, "date"):
                    scheduled_datetime = order.installation_date
                else:
                    scheduled_datetime = timezone.make_aware(
                        timezone.datetime.combine(
                            order.installation_date, timezone.datetime.min.time()
                        )
                    )

                time_diff = scheduled_datetime - order_datetime
                hours = time_diff.total_seconds() / 3600

                if hours >= 0:  # تجاهل القيم السالبة
                    scheduling_times.append(hours)

                    detailed_scheduling.append(
                        {
                            "order_id": order.id,
                            "order_number": getattr(
                                order, "order_number", f"ORD-{order.id}"
                            ),
                            "customer_name": (
                                order.customer.name if order.customer else "غير محدد"
                            ),
                            "order_date": order.order_date,
                            "scheduled_date": order.installation_date,
                            "scheduling_time_hours": round(hours, 2),
                            "created_by": (
                                order.created_by.get_full_name()
                                if order.created_by
                                else "غير محدد"
                            ),
                            "status": order.order_status,
                            "total_amount": order.total_amount,
                        }
                    )
        except Exception:
            continue

    # حساب الإحصائيات
    avg_scheduling_time = (
        sum(scheduling_times) / len(scheduling_times) if scheduling_times else 0
    )
    min_scheduling_time = min(scheduling_times) if scheduling_times else 0
    max_scheduling_time = max(scheduling_times) if scheduling_times else 0

    # توزيع الأوقات
    quick_scheduling = len([t for t in scheduling_times if t <= 24])  # أقل من 24 ساعة
    medium_scheduling = len([t for t in scheduling_times if 24 < t <= 168])  # 1-7 أيام
    slow_scheduling = len([t for t in scheduling_times if t > 168])  # أكثر من أسبوع

    return {
        "total_installation_orders": installation_orders.count(),
        "scheduled_orders": len(detailed_scheduling),
        "pending_scheduling": installation_orders.count() - len(detailed_scheduling),
        "avg_scheduling_time_hours": round(avg_scheduling_time, 2),
        "avg_scheduling_time_days": round(avg_scheduling_time / 24, 1),
        "min_scheduling_time_hours": round(min_scheduling_time, 2),
        "max_scheduling_time_hours": round(max_scheduling_time, 2),
        "quick_scheduling": quick_scheduling,
        "medium_scheduling": medium_scheduling,
        "slow_scheduling": slow_scheduling,
        "detailed_scheduling": detailed_scheduling[:15],  # أحدث 15 جدولة
    }
