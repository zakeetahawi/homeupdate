from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Q, Sum

from .models import EngineerContactLog, EngineerMaterialInterest


def compute_engineer_analytics(profile):
    """
    Compute analytics dict for a single DecoratorEngineerProfile.
    Used in EngineerDetailView context and export.
    """
    linked_orders = profile.linked_orders.select_related("order")

    total_linked_customers = profile.linked_customers.filter(is_active=True).count()
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

    return {
        "total_linked_customers": total_linked_customers,
        "total_linked_orders": total_linked_orders,
        "total_orders_value": order_aggregates["total_value"] or Decimal("0"),
        "commission_pending": order_aggregates["pending"] or Decimal("0"),
        "commission_approved": order_aggregates["approved"] or Decimal("0"),
        "commission_paid": order_aggregates["paid"] or Decimal("0"),
        "avg_monthly_orders": avg_monthly,
        "top_materials": top_materials,
        "last_activity": last_activity,
    }
