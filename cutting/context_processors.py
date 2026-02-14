from django.core.cache import cache

from .models import CuttingOrder

_CUTTING_CACHE_TTL = 120  # 2 دقائق


def cutting_notifications(request):
    """Add cutting order notification count to context — Cached 2 min"""
    if not request.user.is_authenticated:
        return {}

    if not (request.user.is_superuser or request.user.is_staff):
        return {}

    cached = cache.get("ctx_cutting_pending_fix")
    if cached is not None:
        return cached

    pending_fix_count = CuttingOrder.objects.filter(
        status__in=["pending", "in_progress", "partially_completed"], needs_fix=True
    ).count()

    result = {"cutting_orders_pending_fix": pending_fix_count}
    cache.set("ctx_cutting_pending_fix", result, _CUTTING_CACHE_TTL)
    return result
