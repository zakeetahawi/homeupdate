"""
views لتنظيف المستودعات الفارغة
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from cutting.models import CuttingOrder

from .models import StockTransaction, Warehouse
from .smart_upload_logic import delete_empty_warehouses

logger = logging.getLogger(__name__)


def is_admin_or_manager(user):
    """فحص أن المستخدم admin أو manager"""
    return (
        user.is_superuser or user.groups.filter(name__in=["Admin", "Manager"]).exists()
    )


@login_required
@user_passes_test(is_admin_or_manager)
def warehouse_cleanup_view(request):
    """
    صفحة تنظيف المستودعات الفارغة
    """

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete_all_empty":
            # حذف كل المستودعات الفارغة
            result = delete_empty_warehouses(request.user)

            if result.get("deleted", 0) > 0:
                messages.success(
                    request,
                    _(
                        f"✅ تم حذف {result['deleted']} مستودع فارغ: {', '.join(result['warehouses'])}"
                    ),
                )
            else:
                messages.info(request, _("ℹ️ لا توجد مستودعات فارغة للحذف"))

            return redirect("inventory:warehouse_cleanup")

        elif action == "delete_selected":
            # حذف مستودعات محددة
            warehouse_ids = request.POST.getlist("warehouse_ids")

            if not warehouse_ids:
                messages.warning(request, _("⚠️ لم تختر أي مستودع"))
                return redirect("inventory:warehouse_cleanup")

            deleted_names = []
            for wh_id in warehouse_ids:
                try:
                    warehouse = Warehouse.objects.get(id=wh_id)
                    deleted_names.append(warehouse.name)
                    warehouse.delete()
                except Warehouse.DoesNotExist:
                    pass

            if deleted_names:
                messages.success(
                    request,
                    _(
                        f"✅ تم حذف {len(deleted_names)} مستودع: {', '.join(deleted_names)}"
                    ),
                )

            return redirect("inventory:warehouse_cleanup")

    # عرض المستودعات الفارغة
    empty_warehouses = []

    for warehouse in Warehouse.objects.all():
        # حساب المخزون الحالي
        total_stock = (
            StockTransaction.objects.filter(warehouse=warehouse).aggregate(
                total=Sum("quantity")
            )["total"]
            or 0
        )

        # عد أوامر التقطيع النشطة
        active_cutting = CuttingOrder.objects.filter(
            warehouse=warehouse, status__in=["pending", "in_progress"]
        ).count()

        # عد أوامر التقطيع المنتهية
        completed_cutting = CuttingOrder.objects.filter(
            warehouse=warehouse, status__in=["completed", "rejected"]
        ).count()

        # إذا كان فارغاً
        if total_stock == 0:
            can_delete = (
                active_cutting == 0 and not warehouse.is_official_fabric_warehouse
            )

            empty_warehouses.append(
                {
                    "warehouse": warehouse,
                    "total_stock": total_stock,
                    "active_cutting": active_cutting,
                    "active_orders": 0,  # Order model ليس له warehouse field
                    "completed_cutting": completed_cutting,
                    "completed_orders": 0,
                    "can_delete": can_delete,
                    "is_official": warehouse.is_official_fabric_warehouse,
                    "last_activity": warehouse.updated_at,
                }
            )

    context = {
        "empty_warehouses": empty_warehouses,
        "total_empty": len(empty_warehouses),
        "can_delete_count": sum(1 for w in empty_warehouses if w["can_delete"]),
    }

    return render(request, "inventory/warehouse_cleanup.html", context)
