from decimal import Decimal

from manufacturing.models import ManufacturingOrderItem
from orders.contract_models import ContractCurtain


def get_material_summary_context(order):
    """
    Generate material summary context for a given order.
    Returns the summary list and grand totals.
    يحسب عمود الخياطة = سعر نوع التفصيل × الكمية (أمتار أو قطع)
    """
    from factory_accounting.models import (
        FactoryAccountingSettings,
        TailoringTypePricing,
    )

    # Load tailoring type pricing map (once, not per fabric)
    pricing_map = {}
    custom_priced_types = set()  # أنواع لها تسعير مخصص
    for p in TailoringTypePricing.objects.filter(is_active=True).select_related(
        "tailoring_type"
    ):
        pricing_map[p.tailoring_type.value] = p
        pricing_map[p.tailoring_type.display_name] = p
        custom_priced_types.add(p.tailoring_type.value)
        custom_priced_types.add(p.tailoring_type.display_name)

    # Default rate fallback
    try:
        acct_settings = FactoryAccountingSettings.get_settings()
        default_rate = float(acct_settings.default_rate_per_meter)
    except Exception:
        default_rate = 1.0

    materials_map = {}

    # 1. Fabrics Logic
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

            # Skip belts
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
                    "tailoring_types_custom": set(),  # أنواع بسعر مخصص (بادج أحمر)
                    "tailoring_types_default": set(),  # أنواع بسعر افتراضي (بادج رمادي)
                    "permits": set(),
                    "bags": set(),
                    "fabric_type": fabric.fabric_type,
                }

            # Quantity
            qty = float(fabric.meters) if fabric.meters > 0 else float(fabric.pieces)
            pieces = int(fabric.pieces) if fabric.pieces else 1
            materials_map[name]["total_quantity"] += qty

            # Tailoring type info
            t_type_display = fabric.get_tailoring_type_display()
            t_type_raw = fabric.tailoring_type

            # Look up pricing for this tailoring type
            pricing = pricing_map.get(t_type_raw) or pricing_map.get(t_type_display)

            if pricing:
                rate = float(pricing.rate)
                method = pricing.calc_method
                if method == "per_piece":
                    sewing_cost = pieces * rate
                else:  # per_meter
                    sewing_cost = qty * rate
                is_custom = True
            else:
                # Fallback: default rate × meters
                rate = default_rate
                sewing_cost = qty * rate
                is_custom = False

            materials_map[name]["sewing_quantity"] += sewing_cost

            # Track tailoring type for badges
            if t_type_display:
                materials_map[name]["tailoring_types"].add(t_type_display)
                if is_custom:
                    materials_map[name]["tailoring_types_custom"].add(t_type_display)
                else:
                    materials_map[name]["tailoring_types_default"].add(t_type_display)

            # Usage
            type_display = fabric.get_fabric_type_display()
            usage_desc = f"{type_display} في {curtain.room_name}"
            materials_map[name]["usages"].append(usage_desc)

            # Manufacturing Data (Permits, Bags)
            try:
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

    # Transform map to list
    materials_summary = []
    grand_total_quantity = 0.0
    grand_total_sewing = 0.0

    for name, data in materials_map.items():
        unique_usages = sorted(list(set(data["usages"])))
        data["smart_description"] = "، ".join(unique_usages)

        data["tailoring_types_list"] = sorted(list(data["tailoring_types"]))
        data["tailoring_types_custom_list"] = sorted(
            list(data["tailoring_types_custom"])
        )
        data["tailoring_types_default_list"] = sorted(
            list(data["tailoring_types_default"])
        )
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
        "custom_priced_types": custom_priced_types,
    }
