"""
Context Processors للمخزون - لعرض إشعارات التحويلات في جميع الصفحات
Cached per-user for 60 seconds.
"""

from django.core.cache import cache

from .models import StockTransfer, Warehouse

_TRANSFER_CACHE_TTL = 60  # 1 دقيقة


def pending_transfers(request):
    """
    إضافة عدد التحويلات المعلقة للمستخدم الحالي — Cached per user

    مسؤول المخزون: يرى فقط التحويلات الواردة لمخزنه
    مدير النظام: يرى جميع التحويلات
    """
    if not request.user.is_authenticated:
        return {"pending_transfers_count": 0, "pending_transfers": [], "is_warehouse_manager": False}

    user = request.user
    cache_key = f"ctx_pending_transfers_{user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    _STATUSES = ["pending", "approved", "in_transit"]
    _WAREHOUSE_GROUPS = ["مسؤول مخزون", "مسؤول مخازن", "Warehouse Manager", "مسؤول مستودع"]

    # Determine warehouse manager status once (used at bottom + in logic)
    is_manager = user.is_superuser or Warehouse.objects.filter(manager=user).exists()
    in_group = (
        False
        if is_manager
        else user.groups.filter(name__in=_WAREHOUSE_GROUPS).exists()
    )
    is_warehouse_manager = is_manager or in_group

    if user.is_superuser or (not is_manager and in_group):
        # Superuser or group member without specific warehouses → all transfers
        pending_count = StockTransfer.objects.filter(status__in=_STATUSES).count()
        pending_transfers = list(
            StockTransfer.objects.filter(status__in=_STATUSES)
            .select_related("from_warehouse", "to_warehouse", "created_by")
            .order_by("-transfer_date")[:10]
        )
    elif is_manager and not user.is_superuser:
        managed_warehouses = Warehouse.objects.filter(manager=user)
        pending_count = StockTransfer.objects.filter(
            to_warehouse__in=managed_warehouses, status__in=_STATUSES
        ).count()
        pending_transfers = list(
            StockTransfer.objects.filter(
                to_warehouse__in=managed_warehouses, status__in=_STATUSES
            )
            .select_related("from_warehouse", "to_warehouse", "created_by")
            .order_by("-transfer_date")[:10]
        )
    else:
        pending_transfers = []
        pending_count = 0

    result = {
        "pending_transfers_count": pending_count,
        "pending_transfers": pending_transfers,
        "has_pending_transfers": pending_count > 0,
        "is_warehouse_manager": is_warehouse_manager,
    }
    cache.set(cache_key, result, _TRANSFER_CACHE_TTL)
    return result
