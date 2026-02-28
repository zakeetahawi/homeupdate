"""
صفحات العقد التفاعلي - Interactive Contract Views
يتيح لمسؤول خط الإنتاج التفاعل مع العقد مباشرة
"""

import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from orders.contract_models import (
    ContractCurtain,
    CurtainAccessory,
    CurtainFabric,
    FabricManufacturingStatus,
    AccessoryManufacturingStatus,
)
from orders.models import Order
from .models import ManufacturingOrder

logger = logging.getLogger(__name__)


@login_required
def interactive_contract_view(request, manufacturing_order_id):
    """
    عرض العقد التفاعلي لأمر التصنيع
    """
    mfg_order = get_object_or_404(
        ManufacturingOrder.objects.select_related(
            "order",
            "order__customer",
            "order__branch",
            "order__created_by",
            "order__salesperson",
            "production_line",
        ),
        id=manufacturing_order_id,
    )

    order = mfg_order.order

    # تحضير ترتيب الأقمشة
    fabric_priority = {
        "heavy": 1,
        "light": 2,
        "blackout": 3,
        "additional": 4,
        "extra": 4,
        "belt": 5,
    }

    # الحصول على ستائر العقد مع الأقمشة والإكسسوارات
    curtains = (
        ContractCurtain.objects.filter(order=order)
        .prefetch_related(
            Prefetch(
                "fabrics",
                queryset=CurtainFabric.objects.select_related(
                    "manufacturing_status",
                    "manufacturing_status__cut_by",
                    "manufacturing_status__height_filtered_by",
                    "manufacturing_status__quality_checked_by",
                    "manufacturing_status__stopped_by",
                ).order_by("sequence"),
            ),
            Prefetch(
                "accessories",
                queryset=CurtainAccessory.objects.select_related(
                    "manufacturing_status",
                    "manufacturing_status__cut_by",
                    "manufacturing_status__height_filtered_by",
                    "manufacturing_status__quality_checked_by",
                    "manufacturing_status__stopped_by",
                ).order_by("id"),
            ),
        )
        .order_by("sequence")
    )

    # إنشاء حالات تصنيع للأقمشة التي ليس لها حالة بعد
    for curtain in curtains:
        for fabric in curtain.fabrics.all():
            if not hasattr(fabric, "manufacturing_status") or fabric.manufacturing_status is None:
                try:
                    FabricManufacturingStatus.objects.get_or_create(fabric=fabric)
                except Exception:
                    pass

        for accessory in curtain.accessories.all():
            if not hasattr(accessory, "manufacturing_status") or accessory.manufacturing_status is None:
                try:
                    AccessoryManufacturingStatus.objects.get_or_create(accessory=accessory)
                except Exception:
                    pass

    # إعادة جلب البيانات بعد إنشاء الحالات
    curtains = (
        ContractCurtain.objects.filter(order=order)
        .prefetch_related(
            Prefetch(
                "fabrics",
                queryset=CurtainFabric.objects.select_related(
                    "manufacturing_status",
                    "manufacturing_status__cut_by",
                    "manufacturing_status__height_filtered_by",
                    "manufacturing_status__quality_checked_by",
                    "manufacturing_status__stopped_by",
                ).order_by("sequence"),
            ),
            Prefetch(
                "accessories",
                queryset=CurtainAccessory.objects.select_related(
                    "manufacturing_status",
                    "manufacturing_status__cut_by",
                    "manufacturing_status__height_filtered_by",
                    "manufacturing_status__quality_checked_by",
                    "manufacturing_status__stopped_by",
                ).order_by("id"),
            ),
        )
        .order_by("sequence")
    )

    # ترتيب الأقمشة وحساب الإحصائيات
    total_fabrics = 0
    completed_fabrics = 0
    stopped_fabrics = 0

    for curtain in curtains:
        fabrics_list = list(curtain.fabrics.all())
        curtain.sorted_fabrics = sorted(
            fabrics_list,
            key=lambda f: fabric_priority.get(f.fabric_type, 99),
        )

        for fabric in fabrics_list:
            total_fabrics += 1
            status = getattr(fabric, "manufacturing_status", None)
            if status:
                if status.is_complete:
                    completed_fabrics += 1
                elif status.item_status == "stopped":
                    stopped_fabrics += 1

    # الإحصائيات تشمل الأقمشة فقط (الإكسسوارات لها تفاعل مختلف)
    total_items = total_fabrics
    completed_items = completed_fabrics
    stopped_items = stopped_fabrics

    # حساب عدد أيام التشغيل
    working_days = None
    if order.expected_delivery_date and order.created_at:
        created_date = (
            order.created_at.date()
            if hasattr(order.created_at, "date")
            else order.created_at
        )
        delivery_date = order.expected_delivery_date
        if hasattr(delivery_date, "date"):
            delivery_date = delivery_date.date()
        delta = delivery_date - created_date
        working_days = delta.days

    context = {
        "manufacturing_order": mfg_order,
        "order": order,
        "curtains": curtains,
        "working_days": working_days,
        "total_fabrics": total_fabrics,
        "completed_fabrics": completed_fabrics,
        "stopped_fabrics": stopped_fabrics,
        "total_items": total_items,
        "completed_items": completed_items,
        "stopped_items": stopped_items,
        "completion_percentage": (
            int((completed_items / total_items) * 100) if total_items > 0 else 0
        ),
    }

    return render(
        request,
        "manufacturing/interactive_contract.html",
        context,
    )


@login_required
@require_POST
def update_fabric_status(request):
    """
    تحديث حالة قماش عبر AJAX
    """
    import json

    try:
        data = json.loads(request.body)
        fabric_id = data.get("fabric_id")
        field = data.get("field")  # is_cut, is_height_filtered, is_quality_checked
        value = data.get("value")  # True/False

        if not fabric_id or not field:
            return JsonResponse(
                {"success": False, "message": "بيانات ناقصة"}, status=400
            )

        valid_fields = ["is_cut", "is_height_filtered", "is_quality_checked"]
        if field not in valid_fields:
            return JsonResponse(
                {"success": False, "message": "حقل غير صالح"}, status=400
            )

        fabric = get_object_or_404(CurtainFabric, id=fabric_id)
        status_obj, created = FabricManufacturingStatus.objects.get_or_create(
            fabric=fabric
        )

        # تحديث الحقل
        setattr(status_obj, field, bool(value))

        # تحديث بيانات من قام بالعملية والتاريخ
        now = timezone.now()
        if field == "is_cut":
            if value:
                status_obj.cut_at = now
                status_obj.cut_by = request.user
            else:
                status_obj.cut_at = None
                status_obj.cut_by = None
        elif field == "is_height_filtered":
            if value:
                status_obj.height_filtered_at = now
                status_obj.height_filtered_by = request.user
            else:
                status_obj.height_filtered_at = None
                status_obj.height_filtered_by = None
        elif field == "is_quality_checked":
            if value:
                status_obj.quality_checked_at = now
                status_obj.quality_checked_by = request.user
            else:
                status_obj.quality_checked_at = None
                status_obj.quality_checked_by = None

        status_obj.save()

        # حساب حالة الستارة
        curtain = fabric.curtain
        curtain_stats = _get_curtain_stats(curtain)

        return JsonResponse(
            {
                "success": True,
                "is_complete": status_obj.is_complete,
                "completion_percentage": status_obj.completion_percentage,
                "completed_steps": status_obj.completed_steps,
                "curtain_stats": curtain_stats,
                "user_name": request.user.get_full_name() or request.user.username,
                "timestamp": now.strftime("%Y/%m/%d %H:%M"),
            }
        )

    except Exception as e:
        logger.error(f"Error updating fabric status: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": str(e)}, status=500
        )


@login_required
@require_POST
def update_accessory_status(request):
    """
    تحديث حالة إكسسوار عبر AJAX - 3 مراحل مثل الأقمشة
    """
    import json

    try:
        data = json.loads(request.body)
        accessory_id = data.get("accessory_id")
        field = data.get("field")  # is_cut, is_height_filtered, is_quality_checked
        value = data.get("value")  # True/False

        if not accessory_id or not field:
            return JsonResponse(
                {"success": False, "message": "بيانات ناقصة"}, status=400
            )

        valid_fields = ["is_cut", "is_height_filtered", "is_quality_checked"]
        if field not in valid_fields:
            return JsonResponse(
                {"success": False, "message": "حقل غير صالح"}, status=400
            )

        accessory = get_object_or_404(CurtainAccessory, id=accessory_id)
        status_obj, created = AccessoryManufacturingStatus.objects.get_or_create(
            accessory=accessory
        )

        # تحديث الحقل
        setattr(status_obj, field, bool(value))

        # تحديث بيانات من قام بالعملية والتاريخ
        now = timezone.now()
        if field == "is_cut":
            if value:
                status_obj.cut_at = now
                status_obj.cut_by = request.user
            else:
                status_obj.cut_at = None
                status_obj.cut_by = None
        elif field == "is_height_filtered":
            if value:
                status_obj.height_filtered_at = now
                status_obj.height_filtered_by = request.user
            else:
                status_obj.height_filtered_at = None
                status_obj.height_filtered_by = None
        elif field == "is_quality_checked":
            if value:
                status_obj.quality_checked_at = now
                status_obj.quality_checked_by = request.user
            else:
                status_obj.quality_checked_at = None
                status_obj.quality_checked_by = None

        status_obj.save()

        curtain = accessory.curtain
        curtain_stats = _get_curtain_stats(curtain)

        return JsonResponse(
            {
                "success": True,
                "is_complete": status_obj.is_complete,
                "completion_percentage": status_obj.completion_percentage,
                "completed_steps": status_obj.completed_steps,
                "curtain_stats": curtain_stats,
                "user_name": request.user.get_full_name() or request.user.username,
                "timestamp": now.strftime("%Y/%m/%d %H:%M"),
            }
        )

    except Exception as e:
        logger.error(f"Error updating accessory status: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": str(e)}, status=500
        )


@login_required
@require_POST
def stop_fabric_item(request):
    """
    إيقاف صنف (قماش أو إكسسوار) وتبليغه بأنه ناقص
    """
    import json

    try:
        data = json.loads(request.body)
        item_type = data.get("item_type")  # "fabric" or "accessory"
        item_id = data.get("item_id")
        reason = data.get("reason", "")
        action = data.get("action", "stop")  # "stop" or "resume"

        if not item_type or not item_id:
            return JsonResponse(
                {"success": False, "message": "بيانات ناقصة"}, status=400
            )

        now = timezone.now()

        if item_type == "fabric":
            fabric = get_object_or_404(CurtainFabric, id=item_id)
            status_obj, _ = FabricManufacturingStatus.objects.get_or_create(
                fabric=fabric
            )
            curtain = fabric.curtain
        elif item_type == "accessory":
            accessory = get_object_or_404(CurtainAccessory, id=item_id)
            status_obj, _ = AccessoryManufacturingStatus.objects.get_or_create(
                accessory=accessory
            )
            curtain = accessory.curtain
        else:
            return JsonResponse(
                {"success": False, "message": "نوع غير صالح"}, status=400
            )

        if action == "stop":
            status_obj.item_status = "stopped"
            status_obj.stop_reason = reason
            status_obj.stopped_at = now
            status_obj.stopped_by = request.user
        else:
            status_obj.item_status = "active"
            # لا نمسح سبب التوقف للاحتفاظ بالتاريخ

        status_obj.save()

        curtain_stats = _get_curtain_stats(curtain)

        return JsonResponse(
            {
                "success": True,
                "item_status": status_obj.item_status,
                "curtain_stats": curtain_stats,
                "user_name": request.user.get_full_name() or request.user.username,
                "timestamp": now.strftime("%Y/%m/%d %H:%M"),
            }
        )

    except Exception as e:
        logger.error(f"Error stopping item: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": str(e)}, status=500
        )


@login_required
@require_POST
def add_item_note(request):
    """
    إضافة ملاحظة لصنف (قماش أو إكسسوار)
    """
    import json

    try:
        data = json.loads(request.body)
        item_type = data.get("item_type")
        item_id = data.get("item_id")
        note = data.get("note", "").strip()

        if not item_type or not item_id:
            return JsonResponse(
                {"success": False, "message": "بيانات ناقصة"}, status=400
            )

        if item_type == "fabric":
            fabric = get_object_or_404(CurtainFabric, id=item_id)
            status_obj, _ = FabricManufacturingStatus.objects.get_or_create(
                fabric=fabric
            )
        elif item_type == "accessory":
            accessory = get_object_or_404(CurtainAccessory, id=item_id)
            status_obj, _ = AccessoryManufacturingStatus.objects.get_or_create(
                accessory=accessory
            )
        else:
            return JsonResponse(
                {"success": False, "message": "نوع غير صالح"}, status=400
            )

        # إضافة الملاحظة مع التاريخ والمستخدم
        user_name = request.user.get_full_name() or request.user.username
        timestamp = timezone.now().strftime("%Y/%m/%d %H:%M")
        formatted_note = f"[{timestamp} - {user_name}]: {note}"

        if status_obj.notes:
            status_obj.notes = status_obj.notes + "\n" + formatted_note
        else:
            status_obj.notes = formatted_note

        status_obj.save()

        return JsonResponse(
            {
                "success": True,
                "notes": status_obj.notes,
            }
        )

    except Exception as e:
        logger.error(f"Error adding note: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "message": str(e)}, status=500
        )


def _get_curtain_stats(curtain):
    """
    حساب إحصائيات ستارة واحدة
    """
    fabrics = curtain.fabrics.all()
    accessories = curtain.accessories.all()

    total = 0
    completed = 0
    stopped = 0

    for fabric in fabrics:
        total += 1
        try:
            status = fabric.manufacturing_status
            if status.is_complete:
                completed += 1
            elif status.item_status == "stopped":
                stopped += 1
        except (FabricManufacturingStatus.DoesNotExist, AttributeError):
            pass

    for accessory in accessories:
        total += 1
        try:
            status = accessory.manufacturing_status
            if status.is_complete:
                completed += 1
            elif status.item_status == "stopped":
                stopped += 1
        except (AccessoryManufacturingStatus.DoesNotExist, AttributeError):
            pass

    return {
        "total": total,
        "completed": completed,
        "stopped": stopped,
        "in_progress": total - completed - stopped,
        "percentage": int((completed / total) * 100) if total > 0 else 0,
        "curtain_id": curtain.id,
    }
