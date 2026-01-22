from typing import Dict, List, Any, Tuple

from manufacturing.models import ManufacturingOrderItem
from orders.contract_models import ContractCurtain


def get_material_summary_context(order: Any) -> Dict[str, Any]:
    """
    Generate material summary context for a given order.
    
    Args:
        order: Order instance containing contract curtains
        
    Returns:
        Dict containing:
            - materials_summary: List of material dictionaries
            - grand_total_quantity: Total quantity across all materials
            - grand_total_price: Total price across all materials
    
    ✅ تحسين الأداء: تم إصلاح استعلام N+1
    """
    materials_map = {}

    # ✅ إصلاح N+1: جلب الإعدادات مرة واحدة قبل الحلقة
    from factory_accounting.models import FactoryAccountingSettings

    try:
        settings = FactoryAccountingSettings.objects.first()
        if settings:
            double_types = list(
                settings.double_meter_tailoring_types.values_list("value", flat=True)
            ) + list(
                settings.double_meter_tailoring_types.values_list(
                    "display_name", flat=True
                )
            )
        else:
            double_types = []
    except Exception:
        double_types = []

    # 1. Fabrics Logic
    # Use related_name 'contract_curtains' from Order to ContractCurtain
    curtains = (
        order.contract_curtains.all()
        .order_by("sequence")
        .prefetch_related("fabrics", "accessories")
    )

    for curtain in curtains:
        for fabric in curtain.fabrics.all():
            name = fabric.display_name
            if not name:
                continue

            # Skip belts if needed, or keep them if they are tracked
            # Contract logic skips belts:
            if "حزام" in name:
                continue

            if name not in materials_map:
                materials_map[name] = {
                    "name": name,
                    "type": "fabric",
                    "total_quantity": 0.0,
                    "sewing_quantity": 0.0,
                    "unit": "متر" if fabric.meters > 0 else "قطعة",
                    "usages": [],
                    "tailoring_types": set(),
                    "permits": set(),
                    "bags": set(),
                    "fabric_type": fabric.fabric_type,
                }

            # Quantity
            qty = float(fabric.meters) if fabric.meters > 0 else float(fabric.pieces)
            materials_map[name]["total_quantity"] += qty

            # Sewing Quantity (Multiplier) - Based on Factory Accounting Settings
            # ✅ استخدام double_types المحفوظة مسبقاً (تم جلبها قبل الحلقة)

            t_type_display = fabric.get_tailoring_type_display()
            # Also check the raw value as it might be stored in English
            t_type_raw = fabric.tailoring_type

            multiplier = 1
            # Check matching
            is_double = False
            if (t_type_display and t_type_display in double_types) or (
                t_type_raw and t_type_raw in double_types
            ):
                # Check against display or value
                multiplier = 2
                is_double = True

            materials_map[name]["sewing_quantity"] += qty * multiplier

            # Store if this tailoring type is double for this item
            if t_type_display:
                materials_map[name]["tailoring_types"].add(t_type_display)
                # We need to know WHICH type provided double,
                # but for simplicity in template, we can check against the list passed in context

            if is_double:
                materials_map[name]["has_double_meter"] = True

            # Usage
            type_display = fabric.get_fabric_type_display()
            usage_desc = f"{type_display} في {curtain.room_name}"
            materials_map[name]["usages"].append(usage_desc)

            # Manufacturing Data (Permits, Bags)
            # Try to get linked manufacturing item
            # Since fabric links to OrderItem, and ManufacturingOrderItem links to OrderItem
            try:
                # We need to find the ManufacturingOrderItem corresponding to this fabric's OrderItem
                # fabric.order_item is the OrderItem
                if fabric.order_item:
                    m_item = ManufacturingOrderItem.objects.filter(
                        order_item=fabric.order_item
                    ).last()
                    if m_item:
                        if m_item.cutting_permit_number:
                            materials_map[name]["permits"].add(
                                m_item.cutting_permit_number
                            )
                        if m_item.bag_number:
                            materials_map[name]["bags"].add(m_item.bag_number)
            except Exception:
                pass

    # 2. Accessories Logic - REMOVED per user request
    # for curtain in curtains:
    #     for acc in curtain.accessories.all():
    #         pass

    # Transform map to list
    materials_summary = []
    grand_total_quantity = 0.0
    grand_total_sewing = 0.0

    for name, data in materials_map.items():
        # Consolidate usages
        # "Light in Room1, Light in Room2" -> "Light in Room1, Room2" improvement
        # Converting set back to sorted list

        # Simple consolidation:
        # data["smart_description"] = ", ".join(data["usages"])
        # Better: Group by fabric type

        # Generate Smart Description similar to contract service
        from collections import defaultdict

        usage_groups = defaultdict(list)
        for usage in data["usages"]:
            # Splitting "Type in Room" logic might be brittle if replicated strictly
            # Let's just join unique usages for now to be safe
            pass

        unique_usages = sorted(list(set(data["usages"])))
        data["smart_description"] = "، ".join(unique_usages)

        data["tailoring_types_list"] = sorted(list(data["tailoring_types"]))
        data["permits_str"] = ", ".join(sorted(list(data["permits"])))
        data["bags_str"] = ", ".join(sorted(list(data["bags"])))

        grand_total_quantity += data["total_quantity"]
        grand_total_sewing += data["sewing_quantity"]

        materials_summary.append(data)

    # Sort: Fabrics first, then Accessories
    materials_summary.sort(key=lambda x: (x["type"] != "fabric", x["name"]))

    return {
        "materials_summary": materials_summary,
        "grand_total_quantity": grand_total_quantity,
        "grand_total_sewing": grand_total_sewing,
        "double_meter_types": double_types,  # Pass double types to context
    }
