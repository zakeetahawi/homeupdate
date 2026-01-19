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

    # Exclude cards without production date (old/incomplete records)
    cards = cards.exclude(production_date__isnull=True)

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

    # Exclude cards without production date (old/incomplete records)
    cards = cards.exclude(production_date__isnull=True)

    # Apply filters
    if date_from:
        try:
            # Start of day (00:00:00)
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            aware_from = timezone.make_aware(dt_from)
            cards = cards.filter(production_date__gte=aware_from)
        except ValueError:
            pass

    if date_to:
        try:
            # End of day (23:59:59.999999)
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            aware_to = timezone.make_aware(dt_to)
            cards = cards.filter(production_date__lte=aware_to)
        except ValueError:
            pass

    if card_status != "all":
        cards = cards.filter(status=card_status)
    if tailor_id:
        cards = cards.filter(splits__tailor_id=tailor_id).distinct()
    if cutter_id:  # Apply cutter filter
        cards = cards.filter(manufacturing_order__production_line_id=cutter_id)

    # Apply payment status filter (matching production_reports logic)
    if payment_status == "paid":
        cards = cards.filter(status="paid")
    elif payment_status == "unpaid":
        cards = cards.exclude(status="paid")

    # Calculate Totals for the Summary Cards in Excel
    total_meters = cards.aggregate(total=Sum("total_billable_meters"))[
        "total"
    ] or Decimal("0.00")
    total_cutter_cost = cards.aggregate(total=Sum("total_cutter_cost"))[
        "total"
    ] or Decimal("0.00")

    # Get tailor splits for total tailor cost
    splits_totals = CardMeasurementSplit.objects.filter(factory_card__in=cards)
    if payment_status == "paid":
        splits_totals = splits_totals.filter(is_paid=True)
    elif payment_status == "unpaid":
        splits_totals = splits_totals.filter(is_paid=False)

    total_tailor_cost = splits_totals.aggregate(total=Sum("monetary_value"))[
        "total"
    ] or Decimal("0.00")

    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "تقرير الإنتاج"
    ws.sheet_view.rightToLeft = True  # RTL for Excel
    ws.sheet_view.showGridLines = False

    # --- STYLES ---
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    # Main Table Styles
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(
        start_color="2c3e50", end_color="2c3e50", fill_type="solid"
    )  # Dark Blue
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    row_font = Font(size=11)
    row_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    border_style = Side(style="thin", color="aaaaaa")
    thin_border = Border(
        left=border_style, right=border_style, top=border_style, bottom=border_style
    )

    # Total Row Styles
    total_lbl_font = Font(bold=True, size=11, color="FFFFFF")
    total_lbl_fill = PatternFill(
        start_color="34495e", end_color="34495e", fill_type="solid"
    )  # Dark Grey
    total_val_fill = PatternFill(
        start_color="ecf0f1", end_color="ecf0f1", fill_type="solid"
    )  # Light Grey

    # Card Styles
    card_head_font = Font(bold=True, size=12, color="FFFFFF")
    card_val_font = Font(bold=True, size=14, color="2c3e50")

    c1_head_fill = PatternFill(
        start_color="3498db", end_color="3498db", fill_type="solid"
    )
    c1_val_fill = PatternFill(
        start_color="ebf5fb", end_color="ebf5fb", fill_type="solid"
    )
    c2_head_fill = PatternFill(
        start_color="e67e22", end_color="e67e22", fill_type="solid"
    )
    c2_val_fill = PatternFill(
        start_color="fdf2e9", end_color="fdf2e9", fill_type="solid"
    )
    c3_head_fill = PatternFill(
        start_color="27ae60", end_color="27ae60", fill_type="solid"
    )
    c3_val_fill = PatternFill(
        start_color="e9f7ef", end_color="e9f7ef", fill_type="solid"
    )

    # --- LAYOUT ---

    # 1. Main Table Headers
    # Move Table to Row 3 to give breathing room
    start_row = 3
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
        "حالة الطلب",
        "حالة الدفع",
        "تاريخ الدفع",
    ]

    # Specific column widths
    col_widths = {
        1: 18,  # Order Num
        2: 25,  # Customer
        3: 15,  # Date
        4: 15,  # Meters
        5: 12,  # Double
        6: 20,  # Cutter
        7: 15,  # Cutter Cost
        8: 30,  # Tailors (can be long)
        9: 15,  # Tailor Cost
        10: 15,  # Status
        11: 15,  # Pay Status
        12: 18,  # Payment Date
    }

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

        # Set Width
        col_letter = chr(64 + col)
        ws.column_dimensions[col_letter].width = col_widths.get(col, 15)

    # Enable AutoFilter
    ws.auto_filter.ref = f"A{start_row}:L{start_row}"

    # 2. Main Table Data
    sum_meters = Decimal("0.00")
    sum_cutter_cost = Decimal("0.00")
    sum_tailor_cost = Decimal("0.00")

    current_row = start_row + 1
    for card in cards:
        card_splits = card.splits.all()
        tailors_names = ", ".join([s.tailor.name for s in card_splits])
        card_tailor_cost = sum([s.monetary_value for s in card_splits]) or Decimal(
            "0.00"
        )

        # Cutter
        cutter_name = "-"
        if (
            hasattr(card.manufacturing_order, "production_line")
            and card.manufacturing_order.production_line
        ):
            cutter_name = card.manufacturing_order.production_line.name

        vals = [
            card.order_number,
            card.customer_name,
            card.production_date.strftime("%Y-%m-%d") if card.production_date else "-",
            float(card.total_billable_meters),
            float(card.total_double_meters) if card.total_double_meters > 0 else "-",
            cutter_name,
            float(card.total_cutter_cost),
            tailors_names,
            float(card_tailor_cost),
            card.manufacturing_order.get_status_display(),
            "مدفوع" if card.status == "paid" else "غير مدفوع",
            card.payment_date.strftime("%Y-%m-%d") if card.payment_date else "-",
        ]

        for col_idx, val in enumerate(vals, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = row_font
            cell.alignment = row_alignment
            cell.border = thin_border

        sum_meters += card.total_billable_meters
        sum_cutter_cost += card.total_cutter_cost
        sum_tailor_cost += card_tailor_cost

        current_row += 1

    # 3. Totals Row
    # Merge first 3 columns for "Grand Total" label
    ws.merge_cells(
        start_row=current_row, start_column=1, end_row=current_row, end_column=3
    )
    total_label_cell = ws.cell(row=current_row, column=1, value="المجموع الكلي")
    total_label_cell.font = total_lbl_font
    total_label_cell.fill = total_lbl_fill
    total_label_cell.alignment = Alignment(horizontal="center", vertical="center")
    # Apply border to merged cells (simple way: border the first cell)
    total_label_cell.border = thin_border

    # Fill empty cells with light grey and apply border/alignment
    for col in range(4, 12):
        cell = ws.cell(row=current_row, column=col)
        cell.fill = total_val_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.font = Font(bold=True, size=11)

    ws.cell(row=current_row, column=4).value = float(sum_meters)
    ws.cell(row=current_row, column=7).value = float(sum_cutter_cost)
    ws.cell(row=current_row, column=9).value = float(sum_tailor_cost)

    # 4. SIDE CARDS (Vertical Layout)
    # Gap Column: L (12)
    ws.column_dimensions["L"].width = 3

    # Cards Start Column: M(13)
    side_col = 13
    card_width_cols = 4  # M, N, O, P

    # Set width for card columns
    for c in range(side_col, side_col + card_width_cols):
        col_letter = (
            chr(64 + c) if c <= 26 else f"{chr(64 + (c-1)//26)}{chr(64 + (c-1)%26 + 1)}"
        )
        ws.column_dimensions[col_letter].width = 12

    def create_side_card(start_r, title, value, unit, h_fill, v_fill):
        # Header (Merge 4 cols)
        ws.merge_cells(
            start_row=start_r,
            start_column=side_col,
            end_row=start_r,
            end_column=side_col + card_width_cols - 1,
        )
        head_cell = ws.cell(row=start_r, column=side_col, value=title)
        head_cell.font = card_head_font
        head_cell.fill = h_fill
        head_cell.alignment = Alignment(horizontal="center", vertical="center")

        # Value (Merge 4 cols, 2 rows height)
        val_r_start = start_r + 1
        val_r_end = start_r + 2
        ws.merge_cells(
            start_row=val_r_start,
            start_column=side_col,
            end_row=val_r_end,
            end_column=side_col + card_width_cols - 1,
        )

        final_val = f"{value} {unit}" if unit else f"{value}"
        val_cell = ws.cell(row=val_r_start, column=side_col, value=final_val)
        val_cell.font = card_val_font
        val_cell.fill = v_fill
        val_cell.alignment = Alignment(horizontal="center", vertical="center")

        return val_r_end + 2  # gap

    card_row = start_row  # Align with table header

    card_row = create_side_card(
        card_row,
        "📊 إجمالي الأمتار",
        float(total_meters),
        "متر",
        c1_head_fill,
        c1_val_fill,
    )
    card_row = create_side_card(
        card_row,
        "✂️ تكلفة القصاص",
        float(total_cutter_cost),
        "",
        c2_head_fill,
        c2_val_fill,
    )
    card_row = create_side_card(
        card_row,
        "🪡 تكلفة الخياطين",
        float(total_tailor_cost),
        "",
        c3_head_fill,
        c3_val_fill,
    )

    # Save to response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename=production_report_{timezone.now().strftime("%Y%m%d")}.xlsx'
    )
    wb.save(response)

    return response
