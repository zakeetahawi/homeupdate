#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-fix module for cutting orders
Automatically corrects warehouse assignments when items are received
"""

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from inventory.models import Product, StockTransaction, Warehouse

from .models import CuttingOrder, CuttingOrderItem


def is_service_product(product):
    """
    Check if product is a service (installation, tailoring, etc.)
    These should not be in cutting orders
    """
    if not product:
        return False

    service_product_codes = ["005", "006", "007", "008", "0001", "0002", "0003", "0004"]
    service_keywords = ["تركيب", "تفصيل", "نقل", "معاينة", "مسمار"]

    is_service = product.code in service_product_codes or any(
        keyword in product.name for keyword in service_keywords
    )

    return is_service


def get_product_warehouse(product):
    """
    Get the warehouse with the highest stock for this product
    """
    best_warehouse = None
    best_stock = 0

    for warehouse in Warehouse.objects.filter(is_active=True):
        last_trans = (
            StockTransaction.objects.filter(product=product, warehouse=warehouse)
            .order_by("-transaction_date", "-id")
            .first()
        )

        if last_trans and last_trans.running_balance > best_stock:
            best_stock = last_trans.running_balance
            best_warehouse = warehouse

    return best_warehouse, best_stock


def get_product_stock_in_warehouse(product, warehouse):
    """
    Get stock balance for product in specific warehouse
    """
    last_trans = (
        StockTransaction.objects.filter(product=product, warehouse=warehouse)
        .order_by("-transaction_date", "-id")
        .first()
    )

    return last_trans.running_balance if last_trans else 0


def get_items_needing_fix(cutting_order):
    """
    Analyze cutting order items and categorize issues

    Returns:
        dict: {
            'needs_fix': bool,
            'items_by_warehouse': dict,
            'service_items': list,
            'duplicate_items': dict,
            'items_without_stock': list
        }
    """
    items_by_warehouse = defaultdict(list)
    items_without_stock = []
    service_items = []
    duplicate_items = {}

    # Check for duplicates first
    items_by_order_item = defaultdict(list)
    for item in cutting_order.items.all():
        items_by_order_item[item.order_item_id].append(item)

    for order_item_id, items in items_by_order_item.items():
        if len(items) > 1:
            duplicate_items[order_item_id] = items

    # Analyze each item
    for item in cutting_order.items.all():
        if not item.order_item or not item.order_item.product:
            continue

        product = item.order_item.product

        # Check for service products
        if is_service_product(product):
            service_items.append(
                {
                    "item": item,
                    "product": product,
                }
            )
            continue

        current_warehouse = cutting_order.warehouse

        # Get correct warehouse for product
        best_warehouse, best_stock = get_product_warehouse(product)
        current_stock = get_product_stock_in_warehouse(product, current_warehouse)

        # If product is in different warehouse
        if best_warehouse and best_warehouse.id != current_warehouse.id:
            items_by_warehouse[best_warehouse.id].append(
                {
                    "item": item,
                    "product": product,
                    "warehouse": best_warehouse,
                    "stock": best_stock,
                    "current_stock": current_stock,
                    "severity": "critical" if current_stock == 0 else "warning",
                }
            )
        elif best_warehouse is None and current_stock == 0:
            items_without_stock.append(
                {
                    "item": item,
                    "product": product,
                    "current_warehouse": current_warehouse,
                }
            )

    needs_fix = bool(
        items_by_warehouse or service_items or duplicate_items or items_without_stock
    )

    return {
        "needs_fix": needs_fix,
        "items_by_warehouse": dict(items_by_warehouse),
        "service_items": service_items,
        "duplicate_items": duplicate_items,
        "items_without_stock": items_without_stock,
    }


def delete_service_items(service_items):
    """
    Delete service items from cutting order

    Returns:
        list: Deleted items info
    """
    deleted = []

    for item_data in service_items:
        item = item_data["item"]
        product = item_data["product"]

        try:
            item.delete()
            deleted.append(
                {
                    "product": product.name,
                    "code": product.code or "N/A",
                    "reason": "منتج خدمي - لا يجب أن يكون في أوامر التقطيع",
                }
            )
        except Exception as e:
            # Log error but continue
            pass

    return deleted


def delete_duplicate_items(duplicate_items):
    """
    Delete duplicate items, keeping the best one

    Returns:
        list: Deleted duplicates info
    """
    deleted = []

    for order_item_id, items in duplicate_items.items():
        # Priority: completed > in_progress > pending
        priority = {"completed": 3, "in_progress": 2, "pending": 1, "rejected": 0}
        items_sorted = sorted(
            items, key=lambda x: (priority.get(x.status, 0), x.id), reverse=True
        )

        # Keep first (highest priority)
        keep_item = items_sorted[0]
        delete_items = items_sorted[1:]

        product_name = keep_item.order_item.product.name

        for item in delete_items:
            try:
                status_display = item.get_status_display()
                item.delete()
                deleted.append(
                    {
                        "product": product_name,
                        "status": status_display,
                        "kept_status": keep_item.get_status_display(),
                    }
                )
            except Exception as e:
                pass

    return deleted


def move_items_to_correct_warehouse(items_by_warehouse, cutting_order):
    """
    Move items to correct warehouses, creating new cutting orders if needed

    Returns:
        dict: {
            'moved_items': list,
            'new_orders_created': list,
            'moved_to_existing': list,
        }
    """
    moved_items = []
    new_orders_created = []
    moved_to_existing = []

    for warehouse_id, items in items_by_warehouse.items():
        warehouse = items[0]["warehouse"]

        # Look for existing cutting order for this warehouse
        existing_order = (
            CuttingOrder.objects.filter(order=cutting_order.order, warehouse=warehouse)
            .exclude(id=cutting_order.id)
            .first()
        )

        if existing_order:
            # Move to existing order
            target_order = existing_order
            action = "moved_to_existing"

            moved_to_existing.append(
                {
                    "code": target_order.cutting_code,
                    "warehouse": warehouse.name,
                    "items_count": len(items),
                }
            )
        else:
            # Create new cutting order - let the model generate the code
            target_order = CuttingOrder.objects.create(
                order=cutting_order.order,
                warehouse=warehouse,
                status=cutting_order.status,
                notes=f"تم إنشاؤه تلقائياً من {cutting_order.cutting_code} لنقل الأصناف للمستودع الصحيح",
            )
            action = "moved_to_new"

            new_orders_created.append(
                {
                    "code": target_order.cutting_code,
                    "warehouse": warehouse.name,
                    "items_count": len(items),
                }
            )

        # Move items
        for item_data in items:
            item = item_data["item"]
            try:
                item.cutting_order = target_order
                item.save()

                moved_items.append(
                    {
                        "product": item_data["product"].name,
                        "from_warehouse": cutting_order.warehouse.name,
                        "to_warehouse": warehouse.name,
                        "to_order": target_order.cutting_code,
                        "action": action,
                        "stock_in_target": item_data["stock"],
                    }
                )
            except Exception as e:
                pass

    # تحديث حالة أمر التقطيع الأصلي بعد نقل العناصر
    cutting_order.update_status()
    # تحديث حالة أوامر التقطيع الجديدة أيضاً
    for order_data in new_orders_created + moved_to_existing:
        try:
            target = CuttingOrder.objects.get(cutting_code=order_data["code"])
            target.update_status()
        except CuttingOrder.DoesNotExist:
            pass

    return {
        "moved_items": moved_items,
        "new_orders_created": new_orders_created,
        "moved_to_existing": moved_to_existing,
    }


@transaction.atomic
def auto_fix_cutting_order_items(cutting_order, trigger_source="auto"):
    """
    Main auto-fix function - automatically correct cutting order items

    Args:
        cutting_order: CuttingOrder instance
        trigger_source: 'auto' (signal) or 'manual' (admin action)

    Returns:
        dict: Results with counts and details
    """
    # التحقق مما إذا كان الإصلاح مطلوباً
    issues = get_items_needing_fix(cutting_order)

    # تحديث حقل needs_fix للأداء
    if cutting_order.needs_fix != issues["needs_fix"]:
        cutting_order.needs_fix = issues["needs_fix"]
        # استخدام update_fields لتجنب استدعاء signals التكرارية إذا أمكن
        # لكن هنا نريد التأكد من حفظ الحالة
        cutting_order.save(update_fields=["needs_fix"])

    if not issues["needs_fix"]:
        return {
            "success": True,
            "needs_fix": False,
            "moved_items": [],
            "deleted_service_items": [],
            "deleted_duplicates": [],
            "new_orders_created": [],
            "moved_to_existing": [],
            "original_deleted": False,
        }

    results = {
        "success": True,
        "needs_fix": True,
        "moved_items": [],
        "deleted_service_items": [],
        "deleted_duplicates": [],
        "new_orders_created": [],
        "moved_to_existing": [],
        "original_deleted": False,
    }

    try:
        # Step 1: Delete service items
        if issues["service_items"]:
            results["deleted_service_items"] = delete_service_items(
                issues["service_items"]
            )

        # Step 2: Delete duplicates
        if issues["duplicate_items"]:
            results["deleted_duplicates"] = delete_duplicate_items(
                issues["duplicate_items"]
            )

        # Step 3: Move items to correct warehouses
        if issues["items_by_warehouse"]:
            move_results = move_items_to_correct_warehouse(
                issues["items_by_warehouse"], cutting_order
            )
            results["moved_items"] = move_results["moved_items"]
            results["new_orders_created"] = move_results["new_orders_created"]
            results["moved_to_existing"] = move_results["moved_to_existing"]

        # Step 4: Check if original order is now empty
        remaining_items = cutting_order.items.count()
        if remaining_items == 0:
            cutting_order.delete()
            results["original_deleted"] = True

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

    return results
