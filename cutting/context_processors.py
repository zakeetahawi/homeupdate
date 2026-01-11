from .auto_fix import get_items_needing_fix
from .models import CuttingOrder


def cutting_notifications(request):
    """Add cutting order notification count to context"""
    if not request.user.is_authenticated:
        return {}

    # Check if user has permission to see warehouse actions
    # (Superusers or specific roles)
    if not (request.user.is_superuser or request.user.is_staff):
        return {}

    # Count orders with issues that are pending or in progress using the optimized flag
    pending_fix_count = CuttingOrder.objects.filter(
        status__in=["pending", "in_progress", "partially_completed"], needs_fix=True
    ).count()

    return {"cutting_orders_pending_fix": pending_fix_count}
