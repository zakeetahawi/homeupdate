"""
Factory Accounting Views
عرض واجهات حسابات المصنع
"""

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from manufacturing.models import ManufacturingOrder

from .models import CardMeasurementSplit, FactoryAccountingSettings, FactoryCard, Tailor


@login_required
@require_http_methods(["POST"])
def save_factory_card_splits(request, factory_card_id):
    """
    Save factory card split distribution
    حفظ توزيع الخياطين لبطاقة المصنع
    """
    import json

    print(f"DEBUG: Saving Splits for Card {factory_card_id}")  # Confirm code update

    try:
        factory_card = get_object_or_404(FactoryCard, id=factory_card_id)
        data = json.loads(request.body)
        splits_data = data.get("splits", [])

        # Validation
        if not splits_data:
            return JsonResponse(
                {"success": False, "error": "يجب إضافة خياط واحد على الأقل"}, status=400
            )

        with transaction.atomic():
            # Get target meters (double meters if available)
            total_double = factory_card.total_double_meters or 0

            # Use Decimal for precision
            total_double = Decimal(str(total_double))
            billable = Decimal(str(factory_card.total_billable_meters or 0))

            target_meters = total_double if total_double > 0 else billable

            print(f"DEBUG: Target Meters: {target_meters}")

            total_assigned = sum(
                Decimal(str(s.get("share_amount", 0))) for s in splits_data
            )

            # Allow small tolerance
            if abs(total_assigned - target_meters) > Decimal("0.05"):
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"إجمالي الأمتار الموزعة ({total_assigned}) لا يساوي الإجمالي المطلوب ({target_meters})",
                    },
                    status=400,
                )

            # Delete old splits
            factory_card.splits.all().delete()

            # Get default rate
            settings = FactoryAccountingSettings.get_settings()
            default_rate_setting = settings.default_rate_per_meter or Decimal("5.00")

            for split_item in splits_data:
                tailor_id = split_item.get("tailor_id")
                amount = Decimal(str(split_item.get("share_amount", 0)))

                tailor = get_object_or_404(Tailor, id=tailor_id)

                # Determine rate
                tailor_rate = tailor.default_rate
                if tailor_rate is None:
                    tailor_rate = Decimal("0.00")

                print(f"DEBUG: Tailor {tailor.name} rate: {tailor_rate}")

                if tailor_rate > 0:
                    rate = tailor_rate
                else:
                    rate = default_rate_setting

                CardMeasurementSplit.objects.create(
                    factory_card=factory_card,
                    tailor_id=tailor.id,
                    share_amount=amount,
                    unit_rate=rate,
                    monetary_value=amount * rate,
                )

            # Status sync is handled by signals now

        return JsonResponse({"success": True, "message": "تم حفظ التوزيع بنجاح"})

    except Exception as e:
        import traceback

        traceback.print_exc()  # Print full stack trace to console
        return JsonResponse(
            {"success": False, "error": f"System Error: {str(e)}"}, status=400
        )


def get_production_details(manufacturing_order):
    """
    Get detailed production info for the API
    """
    from .models import ProductionStatusLog

    log = (
        ProductionStatusLog.objects.filter(
            manufacturing_order=manufacturing_order,
            status__in=["ready_install", "completed"],
        )
        .order_by("timestamp")
        .first()
    )

    if log:
        # Manual mapping since log.status doesn't have choices in this model
        status_map = {
            "ready_install": "جاهز للتركيب",
            "completed": "مكتمل",
        }
        return {
            "time": log.timestamp.strftime("%I:%M %p")
            .replace("AM", "ص")
            .replace("PM", "م"),
            "status_text": status_map.get(log.status, log.status),
            "status_code": log.status,
            "is_completed": log.status == "completed",
        }
    return None


@login_required
@require_http_methods(["GET"])
def get_factory_card_data(request, manufacturing_order_id):
    """
    Get factory card data for a manufacturing order
    جلب بيانات بطاقة المصنع لأمر تصنيع
    """
    manufacturing_order = get_object_or_404(
        ManufacturingOrder.objects.select_related("order", "order__customer"),
        id=manufacturing_order_id,
    )

    # Get or create factory card
    factory_card, created = FactoryCard.objects.get_or_create(
        manufacturing_order=manufacturing_order, defaults={"created_by": request.user}
    )

    if created:
        factory_card.update_production_date()

    # Auto-calculate total meters
    factory_card.calculate_total_meters()

    # Get all active tailors
    tailors = Tailor.objects.filter(is_active=True).order_by("name")

    # Get existing splits
    splits = CardMeasurementSplit.objects.filter(
        factory_card=factory_card
    ).select_related("tailor")

    # Get production user info
    production_info = factory_card.get_production_user_info()

    # Get production line (cutter)
    production_line = None
    if manufacturing_order.production_line:
        production_line = {
            "id": manufacturing_order.production_line.id,
            "name": manufacturing_order.production_line.name,
        }

    # Prepare response data
    data = {
        "factory_card": {
            "id": factory_card.id,
            "status": factory_card.status,
            "total_billable_meters": float(factory_card.total_billable_meters),
            "total_double_meters": float(factory_card.total_double_meters),
            "production_date": (
                factory_card.production_date.isoformat()
                if factory_card.production_date
                else None
            ),
            "production_details": get_production_details(manufacturing_order),
            "production_info": (
                {
                    **production_info,
                    "timestamp": (
                        production_info["timestamp"].isoformat()
                        if production_info.get("timestamp")
                        else None
                    ),
                }
                if production_info
                else None
            ),
            "manufacturing_order_status_display": manufacturing_order.get_status_display(),
        },
        "production_line": production_line,
        "tailors": [
            {
                "id": t.id,
                "name": t.name,
                "role": t.get_role_display(),
                "default_rate": float(t.get_rate()),  # Use get_rate() for actual rate
            }
            for t in tailors
        ],
        "splits": [
            {
                "id": s.id,
                "tailor_id": s.tailor.id,
                "tailor_name": s.tailor.name,
                "share_amount": float(s.share_amount),
                "unit_rate": float(s.unit_rate),
                "monetary_value": float(s.monetary_value),
                "is_paid": s.is_paid,
            }
            for s in splits
        ],
    }

    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def get_tailors_list(request):
    """
    Get list of all active tailors
    جلب قائمة الخياطين النشطين
    """
    tailors = Tailor.objects.filter(is_active=True).order_by("name")

    data = {
        "tailors": [
            {
                "id": t.id,
                "name": t.name,
                "role": t.get_role_display(),
                "phone": t.phone,
            }
            for t in tailors
        ]
    }

    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
def api_bulk_pay_cards(request):
    """
    Bulk pay factory cards
    دفع جماعي لبطاقات المصنع
    """
    import json

    try:
        data = json.loads(request.body)
        card_ids = data.get("card_ids", [])

        if not card_ids:
            return JsonResponse(
                {"success": False, "error": "لم يتم تحديد أي بطاقات"}, status=400
            )

        with transaction.atomic():
            cards = FactoryCard.objects.filter(id__in=card_ids).exclude(status="paid")
            count = cards.count()

            if count == 0:
                return JsonResponse(
                    {"success": False, "error": "جميع البطاقات المحددة مدفوعة مسبقاً"},
                    status=400,
                )

            # Update cards status
            now = timezone.now()
            for card in cards:
                card.status = "paid"
                card.payment_date = now
                card.save()

                # Mark all splits as paid
                card.splits.update(is_paid=True)

        return JsonResponse(
            {"success": True, "message": f"تم إتمام الدفع لـ {count} بطاقة بنجاح"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
