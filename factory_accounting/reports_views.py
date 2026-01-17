"""
Factory Accounting Reports Views
عرض تقارير حسابات المصنع
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .models import CardMeasurementSplit, FactoryCard, Tailor


@login_required
def production_reports(request):
    """
    Production reports with filtering
    تقارير الإنتاج مع الفلترة
    """
    # Get filter parameters
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    payment_status = request.GET.get("payment_status", "all")
    card_status = request.GET.get("card_status", "all")
    tailor_id = request.GET.get("tailor")
    cutter_id = request.GET.get("cutter")

    # Base queryset
    cards = FactoryCard.objects.select_related(
        "manufacturing_order",
        "manufacturing_order__production_line",  # Optimization for cutter name
        "manufacturing_order__order",
        "manufacturing_order__order__customer",
    ).prefetch_related("splits__tailor")

    # Apply filters
    if date_from:
        cards = cards.filter(production_date__gte=date_from)
    if date_to:
        cards = cards.filter(production_date__lte=date_to)
    if card_status != "all":
        cards = cards.filter(status=card_status)

    # Filter by tailor
    if tailor_id:
        cards = cards.filter(splits__tailor_id=tailor_id).distinct()

    # Filter by cutter (production line)
    if cutter_id:
        cards = cards.filter(manufacturing_order__production_line_id=cutter_id)

    # Calculate totals
    total_meters = cards.aggregate(total=Sum("total_billable_meters"))[
        "total"
    ] or Decimal("0.00")

    total_cutter_cost = cards.aggregate(total=Sum("total_cutter_cost"))[
        "total"
    ] or Decimal("0.00")

    # Get splits for payment status filtering
    splits = CardMeasurementSplit.objects.filter(factory_card__in=cards)

    if payment_status == "paid":
        splits = splits.filter(is_paid=True)
        # Also filter cards that are 'paid' for cutter calculation context
        # Note: If filtering solely by payment_status, cutter cost logic might need adjustment if separate
        # But per user request, we show totals based on current filter.
        cards = cards.filter(status="paid")
    elif payment_status == "unpaid":
        splits = splits.filter(is_paid=False)
        cards = cards.exclude(status="paid")

    total_amount = splits.aggregate(total=Sum("monetary_value"))["total"] or Decimal(
        "0.00"
    )
    # total_amount here represents TOTAL TAILOR COST because splits are tailor payments

    paid_amount = splits.filter(is_paid=True).aggregate(total=Sum("monetary_value"))[
        "total"
    ] or Decimal("0.00")
    unpaid_amount = total_amount - paid_amount

    # Get filter lists
    tailors = Tailor.objects.filter(is_active=True).order_by("name")

    # Import ProductionLine here to avoid circular import if placed at top
    from manufacturing.models import ProductionLine

    cutters = ProductionLine.objects.filter(is_active=True).order_by("name")

    context = {
        "cards": cards.order_by("-production_date")[
            :100
        ],  # Limit to 100 for performance
        "total_meters": total_meters,
        "total_amount": total_amount,
        "total_tailor_cost": total_amount,  # Alias for template compatibility
        "total_cutter_cost": total_cutter_cost,
        "paid_amount": paid_amount,
        "unpaid_amount": unpaid_amount,
        "tailors": tailors,
        "cutters": cutters,
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "payment_status": payment_status,
            "card_status": card_status,
            "tailor": tailor_id,
            "cutter": cutter_id,
        },
    }

    return render(request, "factory_accounting/reports.html", context)


@login_required
def export_production_report(request):
    """
    Export production report to Excel
    تصدير تقرير الإنتاج إلى Excel
    """
    # Get same filters as reports view
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    payment_status = request.GET.get("payment_status", "all")
    card_status = request.GET.get("card_status", "all")
    tailor_id = request.GET.get("tailor")
    cutter_id = request.GET.get("cutter")  # Added cutter filter

    # Build queryset with same filters
    cards = FactoryCard.objects.select_related(
        "manufacturing_order",
        "manufacturing_order__production_line",
        "manufacturing_order__order",
        "manufacturing_order__order__customer",
    ).prefetch_related("splits__tailor")

    if date_from:
        cards = cards.filter(production_date__gte=date_from)
    if date_to:
        cards = cards.filter(production_date__lte=date_to)
    if card_status != "all":
        cards = cards.filter(status=card_status)
    if tailor_id:
        cards = cards.filter(splits__tailor_id=tailor_id).distinct()
    if cutter_id:  # Apply cutter filter
        cards = cards.filter(manufacturing_order__production_line_id=cutter_id)

    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "تقرير الإنتاج"
    ws.sheet_view.rightToLeft = True  # RTL for Excel

    # Styles
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center", vertical="center")

    # Headers
    headers = [
        "رقم الأمر",
        "العميل",
        "تاريخ الإنتاج",
        "إجمالي الأمتار",
        "مضاعف",
        "القصاص",
        "تكلفة القصاص",
        "الخياطين",
        "تكلفة الخياطين",
        "الحالة",
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # Data rows
    row = 2
    for card in cards:
        splits = card.splits.all()
        tailors_names = ", ".join([s.tailor.name for s in splits])
        total_tailor_cost = sum([s.monetary_value for s in splits])

        # Cutter info
        cutter_name = "-"
        if (
            hasattr(card.manufacturing_order, "production_line")
            and card.manufacturing_order.production_line
        ):
            cutter_name = card.manufacturing_order.production_line.name

        ws.cell(row=row, column=1, value=card.order_number)
        ws.cell(row=row, column=2, value=card.customer_name)
        ws.cell(
            row=row,
            column=3,
            value=(
                card.production_date.strftime("%Y-%m-%d")
                if card.production_date
                else "-"
            ),
        )
        ws.cell(row=row, column=4, value=float(card.total_billable_meters))
        ws.cell(
            row=row,
            column=5,
            value=(
                float(card.total_double_meters) if card.total_double_meters > 0 else "-"
            ),
        )
        ws.cell(row=row, column=6, value=cutter_name)
        ws.cell(row=row, column=7, value=float(card.total_cutter_cost))
        ws.cell(row=row, column=8, value=tailors_names)
        ws.cell(row=row, column=9, value=float(total_tailor_cost))
        ws.cell(row=row, column=10, value=card.manufacturing_order.get_status_display())

        # Center align cells
        for col in range(1, 11):
            ws.cell(row=row, column=col).alignment = Alignment(
                horizontal="center", vertical="center"
            )

        row += 1

    # Adjust column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[chr(64 + col)].width = 15

    # Save to response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename=production_report_{timezone.now().strftime("%Y%m%d")}.xlsx'
    )
    wb.save(response)

    return response
