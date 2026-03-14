from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from .models import EngineerContactLog, EngineerLinkedOrder, EngineerMaterialInterest


def compute_engineer_analytics(profile):
    """
    Compute analytics dict for a single DecoratorEngineerProfile.
    Used in EngineerDetailView context and export.
    """
    linked_orders = profile.linked_orders.select_related("order", "order__customer")

    # العملاء الفعليون: العملاء الفريدون من الطلبات المربوطة + العملاء المربوطون يدوياً
    unique_order_customers = (
        linked_orders.values("order__customer").distinct().count()
    )
    manual_linked_customers = profile.linked_customers.filter(is_active=True).count()
    total_unique_clients = max(unique_order_customers, manual_linked_customers)

    total_linked_orders = linked_orders.count()

    order_aggregates = linked_orders.aggregate(
        total_value=Sum("order__total_amount"),
        pending=Sum("commission_value", filter=Q(commission_status="pending")),
        approved=Sum("commission_value", filter=Q(commission_status="approved")),
        paid=Sum("commission_value", filter=Q(commission_status="paid")),
    )

    # Average monthly orders (last 6 months)
    six_months_ago = date.today() - timedelta(days=180)
    orders_last_6m = linked_orders.filter(linked_at__date__gte=six_months_ago).count()
    avg_monthly = round(orders_last_6m / 6, 1)

    # Top materials
    top_materials = list(
        EngineerMaterialInterest.objects.filter(engineer=profile)
        .order_by("-request_count")
        .values("material_name", "request_count")[:5]
    )

    # Last activity
    last_contact = (
        EngineerContactLog.objects.filter(engineer=profile)
        .order_by("-contact_date")
        .values_list("contact_date", flat=True)
        .first()
    )
    last_order = (
        linked_orders.order_by("-linked_at")
        .values_list("linked_at", flat=True)
        .first()
    )
    last_activity = max(filter(None, [last_contact, last_order]), default=None)

    # Per-engineer monthly data for charts (last 6 months)
    # Build complete 6-month labels even if no data
    today = date.today()
    all_months = []
    for i in range(5, -1, -1):
        m = today.replace(day=1) - timedelta(days=i * 30)
        all_months.append(m.strftime("%Y-%m"))
    # Deduplicate preserving order
    seen = set()
    month_labels = []
    for m in all_months:
        if m not in seen:
            seen.add(m)
            month_labels.append(m)

    contacts_by_month_qs = list(
        EngineerContactLog.objects.filter(
            engineer=profile, contact_date__date__gte=six_months_ago
        )
        .annotate(month=TruncMonth("contact_date"))
        .values("month")
        .annotate(cnt=Count("id"))
        .order_by("month")
    )
    orders_by_month_qs = list(
        EngineerLinkedOrder.objects.filter(
            engineer=profile, linked_at__date__gte=six_months_ago
        )
        .annotate(month=TruncMonth("linked_at"))
        .values("month")
        .annotate(cnt=Count("id"))
        .order_by("month")
    )

    contact_map = {str(r["month"])[:7]: r["cnt"] for r in contacts_by_month_qs}
    order_map = {str(r["month"])[:7]: r["cnt"] for r in orders_by_month_qs}

    monthly_contacts = [contact_map.get(m, 0) for m in month_labels]
    monthly_orders = [order_map.get(m, 0) for m in month_labels]

    return {
        "total_linked_customers": manual_linked_customers,
        "total_linked_orders": total_linked_orders,
        "total_orders_value": order_aggregates["total_value"] or Decimal("0"),
        "commission_pending": order_aggregates["pending"] or Decimal("0"),
        "commission_approved": order_aggregates["approved"] or Decimal("0"),
        "commission_paid": order_aggregates["paid"] or Decimal("0"),
        "avg_monthly_orders": avg_monthly,
        "top_materials": top_materials,
        "last_activity": last_activity,
        # Aliases used in templates
        "total_clients": total_unique_clients,
        "total_orders": total_linked_orders,
        "total_value": order_aggregates["total_value"] or Decimal("0"),
        "pending_commission": order_aggregates["pending"] or Decimal("0"),
        "approved_commission": order_aggregates["approved"] or Decimal("0"),
        "paid_commission": order_aggregates["paid"] or Decimal("0"),
        # Monthly chart data (always 6 months)
        "monthly_months": month_labels,
        "monthly_contacts": monthly_contacts,
        "monthly_orders": monthly_orders,
    }
