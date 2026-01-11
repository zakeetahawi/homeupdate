"""
عرض فحص المنتجات المكررة في عدة مستودعات
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .smart_upload_logic import find_duplicate_products

logger = logging.getLogger(__name__)


@login_required
def check_duplicates(request):
    """
    صفحة فحص المنتجات المكررة
    """
    duplicates = find_duplicate_products()

    # إحصائيات
    total_duplicates = len(duplicates)
    total_warehouses_affected = sum(d["warehouses_count"] for d in duplicates)

    context = {
        "duplicates": duplicates,
        "total_duplicates": total_duplicates,
        "total_warehouses_affected": total_warehouses_affected,
    }

    return render(request, "inventory/check_duplicates.html", context)


@login_required
@require_http_methods(["POST"])
def merge_duplicate(request, product_id):
    """
    دمج منتج مكرر في مستودع واحد
    """
    from .models import Product
    from .smart_upload_logic import move_product_to_correct_warehouse

    try:
        product = Product.objects.get(id=product_id)
        target_warehouse_id = request.POST.get("target_warehouse")

        if not target_warehouse_id:
            return JsonResponse(
                {"success": False, "message": "يجب تحديد المستودع المستهدف"}, status=400
            )

        from .models import Warehouse

        target_warehouse = Warehouse.objects.get(id=target_warehouse_id)

        # دمج في المستودع المستهدف
        result = move_product_to_correct_warehouse(
            product,
            target_warehouse,
            0,  # لا توجد كمية جديدة
            request.user,
            merge_all=True,
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"تم الدمج بنجاح",
                "moved": result["moved"],
                "merged_warehouses": result["merged_warehouses"],
                "total_quantity": result.get("total_merged_quantity", 0),
            }
        )

    except Product.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "المنتج غير موجود"}, status=404
        )
    except Exception as e:
        logger.error(f"خطأ في دمج المنتج: {e}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def merge_all_duplicates(request):
    """
    دمج جميع المنتجات المكررة تلقائياً
    """
    from .models import Product
    from .smart_upload_logic import move_product_to_correct_warehouse

    try:
        duplicates = find_duplicate_products()
        merged_count = 0
        errors = []

        for dup in duplicates:
            try:
                product = dup["product"]
                # اختيار أول مستودع كمستهدف (أو يمكن تحسين هذا)
                first_warehouse_name = dup["warehouses"][0]

                from .models import Warehouse

                target_warehouse = Warehouse.objects.get(name=first_warehouse_name)

                result = move_product_to_correct_warehouse(
                    product, target_warehouse, 0, request.user, merge_all=True
                )

                if result["moved"]:
                    merged_count += 1

            except Exception as e:
                errors.append(f"{product.name}: {str(e)}")
                logger.error(f"خطأ في دمج {product.name}: {e}")

        return JsonResponse(
            {
                "success": True,
                "merged_count": merged_count,
                "total_duplicates": len(duplicates),
                "errors": errors,
            }
        )

    except Exception as e:
        logger.error(f"خطأ في الدمج الشامل: {e}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)
