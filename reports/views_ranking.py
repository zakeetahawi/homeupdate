"""
تقرير الترتيب — Ranking Report
يعرض ترتيب الفنيين/الخياطين/البائعين بناءً على الأداء خلال الفترة المحددة
"""

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone


def _get_default_period():
    """حساب المدية الشهرية (25 من الشهر السابق حتى اليوم)"""
    today = timezone.now().date()
    if today.day >= 25:
        date_from = today.replace(day=25).strftime("%Y-%m-%d")
    else:
        if today.month == 1:
            date_from = today.replace(
                year=today.year - 1, month=12, day=25
            ).strftime("%Y-%m-%d")
        else:
            date_from = today.replace(
                month=today.month - 1, day=25
            ).strftime("%Y-%m-%d")
    return date_from


def _get_installation_ranking(date_from, date_to, exclude_modifications):
    """ترتيب الفنيين حسب عدد الشبابيك المركبة"""
    from installation_accounting.models import TechnicianShare
    from installations.models import InstallationSchedule, Technician

    # الحالات المقبولة
    valid_statuses = ["completed", "modification_completed"]
    if exclude_modifications:
        valid_statuses = ["completed"]

    schedules = (
        InstallationSchedule.objects.select_related(
            "order", "order__customer", "accounting_card"
        )
        .prefetch_related(
            "technicians",
            "accounting_card__shares",
            "accounting_card__shares__technician",
        )
        .exclude(status="cancelled")
        .filter(status__in=valid_statuses)
    )

    if date_from:
        schedules = schedules.filter(scheduled_date__gte=date_from)
    if date_to:
        schedules = schedules.filter(scheduled_date__lte=date_to)

    # تجميع البيانات لكل فني
    tech_data = defaultdict(lambda: {
        "name": "",
        "windows": Decimal("0"),
        "orders": 0,
        "amount": Decimal("0.00"),
        "paid": Decimal("0.00"),
        "unpaid": Decimal("0.00"),
    })

    for schedule in schedules:
        if not hasattr(schedule, "accounting_card"):
            continue
        card = schedule.accounting_card
        for share in card.shares.all():
            tid = share.technician_id
            tech_data[tid]["name"] = share.technician.name
            tech_data[tid]["windows"] += share.assigned_windows
            tech_data[tid]["orders"] += 1
            tech_data[tid]["amount"] += share.amount
            if share.is_paid:
                tech_data[tid]["paid"] += share.amount
            else:
                tech_data[tid]["unpaid"] += share.amount

    # ترتيب تنازلي حسب عدد الشبابيك
    ranking = sorted(tech_data.values(), key=lambda x: x["windows"], reverse=True)

    # إجماليات
    totals = {
        "windows": sum(r["windows"] for r in ranking),
        "orders": sum(r["orders"] for r in ranking),
        "amount": sum(r["amount"] for r in ranking),
        "paid": sum(r["paid"] for r in ranking),
        "unpaid": sum(r["unpaid"] for r in ranking),
    }

    return ranking, totals


def _get_production_ranking(date_from, date_to, exclude_modifications):
    """ترتيب الخياطين حسب الأمتار المنتجة"""
    from factory_accounting.models import CardMeasurementSplit, FactoryCard

    cards = (
        FactoryCard.objects.select_related(
            "manufacturing_order",
            "manufacturing_order__production_line",
            "manufacturing_order__order",
        )
        .prefetch_related("splits__tailor")
        .exclude(production_date__isnull=True)
        .exclude(manufacturing_order__production_line_id=4)  # استبعاد الاكسسوارات
    )

    # دائماً استبعاد التعديلات لتتوافق مع تقرير الإنتاج
    cards = cards.exclude(manufacturing_order__order_type="modification")

    if date_from:
        cards = cards.filter(production_date__gte=date_from)
    if date_to:
        cards = cards.filter(production_date__lte=date_to)

    # تجميع البيانات لكل خياط
    tailor_data = defaultdict(lambda: {
        "name": "",
        "meters": Decimal("0"),
        "orders": 0,
        "amount": Decimal("0.00"),
        "paid": Decimal("0.00"),
        "unpaid": Decimal("0.00"),
    })

    for card in cards:
        all_splits = list(card.splits.all())
        if not all_splits:
            continue

        # حساب نصيب كل خياط من الأمتار القابلة للفوترة (بدلاً من الأمتار المزدوجة)
        # لتتطابق مع إجمالي تقرير الإنتاج (total_billable_meters)
        total_share = sum(s.share_amount for s in all_splits)
        billable = card.total_billable_meters or Decimal("0")

        for split in all_splits:
            tid = split.tailor_id
            tailor_data[tid]["name"] = split.tailor.name

            # توزيع الأمتار القابلة للفوترة نسبياً على كل خياط
            if total_share > 0:
                tailor_billable = (split.share_amount / total_share) * billable
            else:
                tailor_billable = Decimal("0")
            tailor_data[tid]["meters"] += tailor_billable

            tailor_data[tid]["orders"] += 1
            current_value = split.get_current_monetary_value()
            tailor_data[tid]["amount"] += current_value
            if split.is_paid:
                tailor_data[tid]["paid"] += current_value
            else:
                tailor_data[tid]["unpaid"] += current_value

    # ترتيب تنازلي حسب الأمتار
    ranking = sorted(tailor_data.values(), key=lambda x: x["meters"], reverse=True)

    totals = {
        "meters": sum(r["meters"] for r in ranking),
        "orders": sum(r["orders"] for r in ranking),
        "amount": sum(r["amount"] for r in ranking),
        "paid": sum(r["paid"] for r in ranking),
        "unpaid": sum(r["unpaid"] for r in ranking),
    }

    return ranking, totals


def _get_sales_ranking(date_from, date_to, exclude_modifications):
    """ترتيب البائعين حسب عدد الطلبات والمبيعات"""
    from orders.models import Order

    orders_qs = Order.objects.select_related("salesperson", "customer").exclude(
        order_status__in=["cancelled", "rejected", "manufacturing_deleted"]
    )

    if exclude_modifications:
        # استبعاد الطلبات التي حالة تركيبها تعديل
        orders_qs = orders_qs.exclude(
            installation_status__in=[
                "modification_required",
                "modification_in_progress",
                "modification_completed",
            ]
        )

    if date_from:
        orders_qs = orders_qs.filter(created_at__date__gte=date_from)
    if date_to:
        orders_qs = orders_qs.filter(created_at__date__lte=date_to)

    # تجميع حسب البائع
    sales_data = defaultdict(lambda: {
        "name": "",
        "orders": 0,
        "total_amount": Decimal("0.00"),
        "paid": Decimal("0.00"),
        "remaining": Decimal("0.00"),
    })

    for order in orders_qs:
        if order.salesperson_id:
            sid = order.salesperson_id
            sales_data[sid]["name"] = (
                order.salesperson.name if order.salesperson else "غير محدد"
            )
        elif order.salesperson_name_raw:
            sid = f"raw_{order.salesperson_name_raw}"
            sales_data[sid]["name"] = order.salesperson_name_raw
        else:
            sid = "unknown"
            sales_data[sid]["name"] = "غير محدد"

        final = order.final_price or order.total_amount or Decimal("0.00")
        paid = order.paid_amount or Decimal("0.00")

        sales_data[sid]["orders"] += 1
        sales_data[sid]["total_amount"] += final
        sales_data[sid]["paid"] += paid
        sales_data[sid]["remaining"] += max(final - paid, Decimal("0.00"))

    # ترتيب تنازلي حسب عدد الطلبات
    ranking = sorted(sales_data.values(), key=lambda x: x["orders"], reverse=True)

    totals = {
        "orders": sum(r["orders"] for r in ranking),
        "total_amount": sum(r["total_amount"] for r in ranking),
        "paid": sum(r["paid"] for r in ranking),
        "remaining": sum(r["remaining"] for r in ranking),
    }

    return ranking, totals


def _get_cutting_ranking(date_from, date_to, exclude_modifications):
    """ترتيب المستودعات حسب عدد طلبات التقطيع المكتملة"""
    from cutting.models import CuttingOrder

    orders_qs = CuttingOrder.objects.select_related(
        "warehouse", "order", "assigned_to"
    ).filter(status="completed")

    if exclude_modifications:
        orders_qs = orders_qs.exclude(
            order__installation_status__in=[
                "modification_required",
                "modification_in_progress",
                "modification_completed",
            ]
        )

    if date_from:
        orders_qs = orders_qs.filter(completed_at__date__gte=date_from)
    if date_to:
        orders_qs = orders_qs.filter(completed_at__date__lte=date_to)

    # تجميع حسب المستودع
    warehouse_data = defaultdict(lambda: {
        "name": "",
        "completed_orders": 0,
        "total_items": 0,
        "total_quantity": Decimal("0"),
        "avg_days": Decimal("0"),
        "_total_days": Decimal("0"),
    })

    for co in orders_qs:
        wid = co.warehouse_id
        warehouse_data[wid]["name"] = co.warehouse.name if co.warehouse else "غير محدد"
        warehouse_data[wid]["completed_orders"] += 1
        # حساب مدة الإنجاز
        if co.started_at and co.completed_at:
            days = (co.completed_at - co.started_at).total_seconds() / 86400
            warehouse_data[wid]["_total_days"] += Decimal(str(round(days, 1)))

    # حساب عدد الأصناف والكميات لكل طلب تقطيع
    from cutting.models import CuttingOrderItem

    completed_order_ids = list(orders_qs.values_list("id", flat=True))
    if completed_order_ids:
        items_qs = (
            CuttingOrderItem.objects.filter(
                cutting_order_id__in=completed_order_ids, status="completed"
            )
            .values("cutting_order__warehouse_id")
            .annotate(
                item_count=Count("id"),
                total_qty=Sum("quantity"),
            )
        )
        for row in items_qs:
            wid = row["cutting_order__warehouse_id"]
            if wid in warehouse_data:
                warehouse_data[wid]["total_items"] += row["item_count"]
                warehouse_data[wid]["total_quantity"] += row["total_qty"] or Decimal("0")

    # حساب متوسط أيام الإنجاز
    for wid, data in warehouse_data.items():
        if data["completed_orders"] > 0:
            data["avg_days"] = round(
                data["_total_days"] / data["completed_orders"], 1
            )
        del data["_total_days"]

    # ترتيب تنازلي حسب عدد الطلبات المكتملة
    ranking = sorted(
        warehouse_data.values(), key=lambda x: x["completed_orders"], reverse=True
    )

    totals = {
        "completed_orders": sum(r["completed_orders"] for r in ranking),
        "total_items": sum(r["total_items"] for r in ranking),
        "total_quantity": sum(r["total_quantity"] for r in ranking),
    }

    return ranking, totals


def _get_inventory_ranking(date_from, date_to, exclude_modifications):
    """ترتيب الخامات حسب عدد مرات التقطيع المكتمل"""
    from cutting.models import CuttingOrder, CuttingOrderItem
    from inventory.models import Product

    # الأصناف المكتملة من طلبات التقطيع
    items_qs = CuttingOrderItem.objects.select_related(
        "cutting_order", "order_item", "order_item__product"
    ).filter(
        cutting_order__status="completed",
        status="completed",
    ).exclude(order_item__isnull=True)

    if exclude_modifications:
        items_qs = items_qs.exclude(
            cutting_order__order__installation_status__in=[
                "modification_required",
                "modification_in_progress",
                "modification_completed",
            ]
        )

    if date_from:
        items_qs = items_qs.filter(cutting_order__completed_at__date__gte=date_from)
    if date_to:
        items_qs = items_qs.filter(cutting_order__completed_at__date__lte=date_to)

    # تجميع حسب المنتج/الخامة
    product_data = defaultdict(lambda: {
        "name": "",
        "code": "",
        "unit": "",
        "times_cut": 0,
        "total_quantity": Decimal("0"),
        "orders_count": 0,
        "_order_ids": set(),
    })

    for item in items_qs:
        if item.order_item and item.order_item.product:
            pid = item.order_item.product_id
            product = item.order_item.product
            product_data[pid]["name"] = product.name
            product_data[pid]["code"] = product.code or ""
            product_data[pid]["unit"] = product.get_unit_display() if hasattr(product, "get_unit_display") else product.unit
            product_data[pid]["times_cut"] += 1
            # الكمية من OrderItem (كمية الطلب الأصلي) أو CuttingOrderItem
            qty = item.order_item.quantity if item.order_item.quantity else (item.quantity or Decimal("0"))
            product_data[pid]["total_quantity"] += qty
            product_data[pid]["_order_ids"].add(item.cutting_order.order_id)
        elif item.is_external and item.external_fabric_name:
            pid = f"ext_{item.external_fabric_name}"
            product_data[pid]["name"] = item.external_fabric_name
            product_data[pid]["code"] = "خارجي"
            product_data[pid]["unit"] = "متر"
            product_data[pid]["times_cut"] += 1
            product_data[pid]["total_quantity"] += item.quantity or Decimal("0")
            product_data[pid]["_order_ids"].add(item.cutting_order.order_id)

    # حساب عدد الطلبات الفريدة
    for pid, data in product_data.items():
        data["orders_count"] = len(data["_order_ids"])
        del data["_order_ids"]

    # ترتيب تنازلي حسب عدد مرات التقطيع
    ranking = sorted(
        product_data.values(), key=lambda x: x["times_cut"], reverse=True
    )

    totals = {
        "times_cut": sum(r["times_cut"] for r in ranking),
        "total_quantity": sum(r["total_quantity"] for r in ranking),
        "orders_count": sum(r["orders_count"] for r in ranking),
        "products_count": len(ranking),
    }

    return ranking, totals


@login_required
def ranking_report(request):
    """عرض تقرير الترتيب الموحد"""
    report_type = request.GET.get("type", "installations")
    date_from = request.GET.get("date_from", _get_default_period())
    date_to = request.GET.get("date_to", "")
    exclude_modifications = request.GET.get("exclude_modifications") == "1"

    # تنظيف القيم الفارغة
    if date_to in ("", "None", None):
        date_to = ""
    if date_from in ("", "None", None):
        date_from = _get_default_period()

    ranking = []
    totals = {}

    if report_type == "installations":
        ranking, totals = _get_installation_ranking(
            date_from, date_to or None, exclude_modifications
        )
    elif report_type == "production":
        ranking, totals = _get_production_ranking(
            date_from, date_to or None, exclude_modifications
        )
    elif report_type == "sales":
        ranking, totals = _get_sales_ranking(
            date_from, date_to or None, exclude_modifications
        )
    elif report_type == "cutting":
        ranking, totals = _get_cutting_ranking(
            date_from, date_to or None, exclude_modifications
        )
    elif report_type == "inventory":
        ranking, totals = _get_inventory_ranking(
            date_from, date_to or None, exclude_modifications
        )

    # إضافة الترتيب
    for i, item in enumerate(ranking, 1):
        item["rank"] = i

    context = {
        "ranking": ranking,
        "totals": totals,
        "report_type": report_type,
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "exclude_modifications": exclude_modifications,
        },
    }

    return render(request, "reports/ranking.html", context)
