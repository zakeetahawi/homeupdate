import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from installations.models import Technician

from .models import InstallationAccountingSettings, InstallationCard, TechnicianShare


@login_required
def installation_reports(request):
    """
    نتائج تقارير التركيبات (بناءً على الجدول الزمني)
    يعرض جميع التركيبات المجدولة في يوم معين بغض النظر عن حالة الإكمال
    """
    today = timezone.now().date()

    # تحديد التاريخ الافتراضي
    if today.day >= 25:
        default_date_from = today.replace(day=25).strftime("%Y-%m-%d")
    else:
        if today.month == 1:
            default_date_from = today.replace(
                year=today.year - 1, month=12, day=25
            ).strftime("%Y-%m-%d")
        else:
            default_date_from = today.replace(month=today.month - 1, day=25).strftime(
                "%Y-%m-%d"
            )

    date_from = request.GET.get("date_from", default_date_from)
    date_to = request.GET.get("date_to")
    payment_status = request.GET.get("payment_status", "all")
    completion_status = request.GET.get("completion_status", "all")
    technician_id = request.GET.get("technician")

    # Base queryset - Schedule based
    from installations.models import InstallationSchedule

    schedules = (
        InstallationSchedule.objects.select_related(
            "order",
            "order__customer",
            "accounting_card",  # Left join with accounting card
        )
        .prefetch_related(
            "technicians",
            "accounting_card__shares",
            "accounting_card__shares__technician",
        )
        .exclude(status="cancelled")
    )  # Exclude cancelled (optional based on user request "full schedule", but usually cancelled means removed)

    # Filter by SCHEDULED DATE
    if date_from:
        schedules = schedules.filter(scheduled_date__gte=date_from)
    if date_to:
        schedules = schedules.filter(scheduled_date__lte=date_to)

    # Filter by TECHNICIAN (if assigned in schedule)
    if technician_id:
        schedules = schedules.filter(technicians__id=technician_id).distinct()

    # Filter by COMPLETION STATUS (Strictly Completed Only as per user request)
    schedules = schedules.filter(status__in=["completed", "modification_completed"])

    # Filter by PAYMENT STATUS (requires accounting card)
    if payment_status == "paid":
        schedules = schedules.filter(accounting_card__status="paid")
    elif payment_status == "unpaid":
        schedules = schedules.exclude(accounting_card__status="paid")

    # Calculate Totals
    # Note: Totals should account for filtered list
    total_windows = 0
    total_cost = Decimal("0.00")
    total_orders_count = schedules.count()
    technician_total = Decimal("0.00")

    # We iterate to sum values because some might not have cards yet
    # Or use aggregation if possible, but cleaner logic here:

    # For technician total, we need to be careful if filtering by technician

    for schedule in schedules:
        # Windows count (from schedule or card)
        # Use card's windows count if exists (final), else schedule's
        if hasattr(schedule, "accounting_card"):
            wins = schedule.accounting_card.windows_count
            cost = schedule.accounting_card.total_cost

            # Tech shares
            shares = schedule.accounting_card.shares.all()
            if technician_id:
                shares = shares.filter(technician_id=technician_id)

            # Payment status logic for tech total
            if payment_status == "paid":
                shares = shares.filter(is_paid=True)
            elif payment_status == "unpaid":
                shares = shares.filter(is_paid=False)

            tech_sum = sum(share.amount for share in shares)
        else:
            wins = schedule.windows_count or 0
            cost = Decimal("0.00")  # No accounting yet
            tech_sum = Decimal("0.00")

        total_windows += wins
        total_cost += cost
        technician_total += tech_sum

    # Dropdowns
    technicians = Technician.objects.filter(
        is_active=True, department="installation"
    ).order_by("name")

    context = {
        "schedules": schedules.order_by("scheduled_date"),  # Sort by scheduled date
        "total_windows": total_windows,
        "total_cost": total_cost,
        "total_orders_count": total_orders_count,
        "technician_total": technician_total,
        "technicians": technicians,
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "payment_status": payment_status,
            "completion_status": completion_status,
            "technician": technician_id,
        },
    }

    return render(request, "installation_accounting/reports.html", context)


@login_required
def api_bulk_pay_installations(request):
    """
    إتمام الدفع لمجموعة من التركيبات (حصص الفنيين)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed"})

    try:
        data = json.loads(request.body)
        card_ids = data.get("card_ids", [])
        technician_id = data.get("technician_id")

        shares_query = TechnicianShare.objects.filter(
            card_id__in=card_ids, is_paid=False
        )
        if technician_id:
            shares_query = shares_query.filter(technician_id=technician_id)

        count = shares_query.count()
        shares_query.update(is_paid=True, paid_date=timezone.now())

        # Check if all shares for a card are paid to update card status
        for card_id in card_ids:
            card = InstallationCard.objects.get(id=card_id)
            if not card.shares.filter(is_paid=False).exists():
                card.status = "paid"
                card.payment_date = timezone.now()
                card.save(update_fields=["status", "payment_date"])

        return JsonResponse(
            {"success": True, "message": f"تم إتمام الدفع لـ {count} حصة بنجاح"}
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})
