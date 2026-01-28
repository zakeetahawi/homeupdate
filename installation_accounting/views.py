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
    نتائج تقارير التركيبات (بناءً على مبدأ تقرير المصنع)
    """
    today = timezone.now().date()

    # تطبيق نفس منطق التاريخ (25 من الشهر)
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
    technician_id = request.GET.get("technician")

    # Base queryset - فقط التركيبات المكتملة
    cards = InstallationCard.objects.select_related(
        "installation_schedule",
        "installation_schedule__order",
        "installation_schedule__order__customer",
    ).prefetch_related("shares__technician")

    # Filter by date
    if date_from:
        cards = cards.filter(completion_date__date__gte=date_from)
    if date_to:
        cards = cards.filter(completion_date__date__lte=date_to)

    # Filter by technician
    if technician_id:
        cards = cards.filter(shares__technician_id=technician_id).distinct()

    # Filter by payment status (card level)
    if payment_status == "paid":
        cards = cards.filter(status="paid")
    elif payment_status == "unpaid":
        cards = cards.exclude(status="paid")

    # Calculate Totals
    total_windows = cards.aggregate(total=Sum("windows_count"))["total"] or 0
    total_cost = cards.aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")

    # Calculate technician specific cost if filtered
    technician_total = Decimal("0.00")
    shares = TechnicianShare.objects.filter(card__in=cards)

    if technician_id:
        shares = shares.filter(technician_id=technician_id)

    if payment_status == "paid":
        shares = shares.filter(is_paid=True)
    elif payment_status == "unpaid":
        shares = shares.filter(is_paid=False)

    for share in shares:
        technician_total += share.amount

    # Dropdowns
    technicians = Technician.objects.filter(
        is_active=True, department="installation"
    ).order_by("name")

    context = {
        "cards": cards.order_by("-completion_date"),
        "total_windows": total_windows,
        "total_cost": total_cost,
        "total_orders_count": cards.count(),
        "technician_total": technician_total,
        "technicians": technicians,
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "payment_status": payment_status,
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
