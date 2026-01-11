"""
Views لتحليل حركات المخزون
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import (
    Product,
    StockTransaction,
    StockTransfer,
    StockTransferItem,
    Warehouse,
)


@login_required
def product_stock_movement(request, product_id):
    """تحليل حركة المخزون لمنتج معين"""
    product = get_object_or_404(Product, pk=product_id)

    # الفترة الزمنية
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    # حركات المخزون
    transactions = (
        StockTransaction.objects.filter(
            product=product, transaction_date__gte=start_date
        )
        .select_related("warehouse", "created_by")
        .order_by("-transaction_date")
    )

    # الإحصائيات
    stats = {
        "total_in": transactions.filter(transaction_type="in").aggregate(
            total=Sum("quantity")
        )["total"]
        or 0,
        "total_out": transactions.filter(transaction_type="out").aggregate(
            total=Sum("quantity")
        )["total"]
        or 0,
        "total_transfer": transactions.filter(transaction_type="transfer").aggregate(
            total=Sum("quantity")
        )["total"]
        or 0,
        "total_adjustment": transactions.filter(
            transaction_type="adjustment"
        ).aggregate(total=Sum("quantity"))["total"]
        or 0,
    }

    # المخزون حسب المستودع
    warehouse_stock = {}
    for warehouse in Warehouse.objects.filter(is_active=True):
        last_transaction = (
            StockTransaction.objects.filter(product=product, warehouse=warehouse)
            .order_by("-transaction_date")
            .first()
        )

        warehouse_stock[warehouse.name] = {
            "current": last_transaction.running_balance if last_transaction else 0,
            "warehouse_id": warehouse.id,
        }

    # التحويلات المرتبطة
    transfers_out = StockTransferItem.objects.filter(
        product=product,
        transfer__from_warehouse__isnull=False,
        transfer__created_at__gte=start_date,
    ).select_related("transfer", "transfer__from_warehouse", "transfer__to_warehouse")

    transfers_in = StockTransferItem.objects.filter(
        product=product,
        transfer__to_warehouse__isnull=False,
        transfer__created_at__gte=start_date,
    ).select_related("transfer", "transfer__from_warehouse", "transfer__to_warehouse")

    context = {
        "product": product,
        "transactions": transactions[:50],  # آخر 50 حركة
        "stats": stats,
        "warehouse_stock": warehouse_stock,
        "transfers_out": transfers_out,
        "transfers_in": transfers_in,
        "days": days,
    }

    return render(request, "inventory/product_stock_movement.html", context)


@login_required
def warehouse_stock_analysis(request, warehouse_id):
    """تحليل المخزون في مستودع معين"""
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

    # الفترة الزمنية
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    # حركات المخزون
    transactions = (
        StockTransaction.objects.filter(
            warehouse=warehouse, transaction_date__gte=start_date
        )
        .select_related("product", "created_by")
        .order_by("-transaction_date")
    )

    # الإحصائيات
    stats = {
        "total_transactions": transactions.count(),
        "total_in": transactions.filter(transaction_type="in").aggregate(
            total=Sum("quantity")
        )["total"]
        or 0,
        "total_out": transactions.filter(transaction_type="out").aggregate(
            total=Sum("quantity")
        )["total"]
        or 0,
        "unique_products": transactions.values("product").distinct().count(),
    }

    # المنتجات في المستودع
    products_in_warehouse = []
    for product in Product.objects.all():
        last_transaction = (
            StockTransaction.objects.filter(product=product, warehouse=warehouse)
            .order_by("-transaction_date")
            .first()
        )

        if last_transaction and last_transaction.running_balance > 0:
            products_in_warehouse.append(
                {
                    "product": product,
                    "quantity": last_transaction.running_balance,
                    "last_transaction_date": last_transaction.transaction_date,
                }
            )

    # ترتيب حسب الكمية
    products_in_warehouse.sort(key=lambda x: x["quantity"], reverse=True)

    # التحويلات الواردة والصادرة
    transfers_in = (
        StockTransfer.objects.filter(to_warehouse=warehouse, created_at__gte=start_date)
        .select_related("from_warehouse")
        .prefetch_related("items__product")
    )

    transfers_out = (
        StockTransfer.objects.filter(
            from_warehouse=warehouse, created_at__gte=start_date
        )
        .select_related("to_warehouse")
        .prefetch_related("items__product")
    )

    context = {
        "warehouse": warehouse,
        "transactions": transactions[:50],
        "stats": stats,
        "products_in_warehouse": products_in_warehouse[:20],  # أعلى 20 منتج
        "transfers_in": transfers_in,
        "transfers_out": transfers_out,
        "days": days,
    }

    return render(request, "inventory/warehouse_stock_analysis.html", context)


@login_required
def stock_movement_summary(request):
    """ملخص حركات المخزون"""
    # الفترة الزمنية
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    # الإحصائيات العامة
    total_transactions = StockTransaction.objects.filter(
        transaction_date__gte=start_date
    ).count()

    total_transfers = StockTransfer.objects.filter(created_at__gte=start_date).count()

    # حركات المخزون حسب النوع
    transaction_by_type = (
        StockTransaction.objects.filter(transaction_date__gte=start_date)
        .values("transaction_type")
        .annotate(count=Count("id"), total_quantity=Sum("quantity"))
    )

    # التحويلات حسب الحالة
    transfers_by_status = (
        StockTransfer.objects.filter(created_at__gte=start_date)
        .values("status")
        .annotate(count=Count("id"))
    )

    # أكثر المنتجات حركة
    top_products = (
        StockTransaction.objects.filter(transaction_date__gte=start_date)
        .values("product__name", "product__id")
        .annotate(transaction_count=Count("id"), total_quantity=Sum("quantity"))
        .order_by("-transaction_count")[:10]
    )

    # أكثر المستودعات نشاطاً
    top_warehouses = (
        StockTransaction.objects.filter(transaction_date__gte=start_date)
        .values("warehouse__name", "warehouse__id")
        .annotate(transaction_count=Count("id"))
        .order_by("-transaction_count")[:10]
    )

    # التحويلات المعلقة
    pending_transfers = (
        StockTransfer.objects.filter(status__in=["pending", "approved", "in_transit"])
        .select_related("from_warehouse", "to_warehouse")
        .order_by("-created_at")
    )

    context = {
        "total_transactions": total_transactions,
        "total_transfers": total_transfers,
        "transaction_by_type": transaction_by_type,
        "transfers_by_status": transfers_by_status,
        "top_products": top_products,
        "top_warehouses": top_warehouses,
        "pending_transfers": pending_transfers,
        "days": days,
    }

    return render(request, "inventory/stock_movement_summary.html", context)


@login_required
def stock_discrepancy_report(request):
    """تقرير التناقضات في المخزون"""
    discrepancies = []

    for product in Product.objects.all():
        # حساب المخزون المتوقع من الحركات
        total_in = (
            StockTransaction.objects.filter(
                product=product, transaction_type="in"
            ).aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        total_out = (
            StockTransaction.objects.filter(
                product=product, transaction_type__in=["out", "transfer"]
            ).aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        expected_stock = total_in - total_out

        # المخزون الفعلي من آخر حركة
        last_transaction = (
            StockTransaction.objects.filter(product=product)
            .order_by("-transaction_date")
            .first()
        )

        actual_stock = last_transaction.running_balance if last_transaction else 0

        # التحقق من التناقض
        if abs(expected_stock - actual_stock) > 0.01:  # تجاهل الفروقات الصغيرة جداً
            discrepancies.append(
                {
                    "product": product,
                    "expected": expected_stock,
                    "actual": actual_stock,
                    "difference": actual_stock - expected_stock,
                    "last_transaction_date": (
                        last_transaction.transaction_date if last_transaction else None
                    ),
                }
            )

    context = {
        "discrepancies": discrepancies,
    }

    return render(request, "inventory/stock_discrepancy_report.html", context)
