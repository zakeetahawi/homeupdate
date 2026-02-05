"""
عرض فحص المنتجات المكررة في عدة مستودعات
"""

import logging

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .smart_upload_logic import find_duplicate_products

logger = logging.getLogger(__name__)


@login_required
def check_duplicates(request):
    """
    صفحة فحص المنتجات المكررة
    محسّن مع cache لمدة 5 دقائق
    """
    # محاولة الحصول على النتائج من الـ cache
    cache_key = "inventory_duplicates_check"
    duplicates = cache.get(cache_key)

    if duplicates is None:
        # إذا لم تكن في الـ cache، احصل عليها من قاعدة البيانات
        duplicates = find_duplicate_products()
        # احفظها في الـ cache لمدة 5 دقائق (300 ثانية)
        cache.set(cache_key, duplicates, 300)

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

        # مسح الـ cache بعد الدمج
        cache.delete("inventory_duplicates_check")

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
    دمج جميع المنتجات المكررة تلقائياً - فائق السرعة
    يتم الدمج في المستودع الأخير (الذي حصل فيه آخر تحويل)
    """
    from django.db import connection, transaction
    from django.db.models import signals
    from decimal import Decimal
    from .models import Product, Warehouse, StockTransaction
    from .smart_upload_logic import update_cutting_orders_after_move
    from inventory import signals as inventory_signals

    try:
        duplicates = find_duplicate_products()
        total = len(duplicates)
        merged_count = 0
        errors = []

        print(f"\n{'='*60}")
        print(f"🚀 بدء دمج فائق السرعة لـ {total} منتج مكرر...")
        print(f"{'='*60}\n")
        logger.info(f"🚀 بدء دمج فائق السرعة لـ {total} منتج مكرر...")

        # تعطيل signals أثناء الدمج بالكامل
        signals.post_save.disconnect(inventory_signals.stock_manager_handler, sender=StockTransaction)
        
        try:
            # استخدام transaction واحد للدمج بالكامل
            with transaction.atomic():
                with connection.cursor() as cursor:
                    for idx, dup in enumerate(duplicates, 1):
                        try:
                            product = dup["product"]

                            # طباعة التقدم كل 50 منتج
                            if idx % 50 == 0 or idx == 1 or idx == total:
                                msg = f"⚡ تقدم: {idx}/{total} - {product.code} | {product.name[:40]}"
                                print(msg)
                                logger.info(msg)

                            # استخدام المستودع المقترح (الأخير)
                            if dup.get("suggested_warehouse_id"):
                                target_warehouse_id = dup["suggested_warehouse_id"]
                            else:
                                first_warehouse_name = dup["warehouses"][0]
                                target_warehouse = Warehouse.objects.get(name=first_warehouse_name)
                                target_warehouse_id = target_warehouse.id

                            warehouses_merged = 0
                            total_moved = Decimal('0')
                            
                            # جمع الكميات من جميع المستودعات
                            for warehouse_id in dup.get("warehouse_ids", []):
                                if warehouse_id != target_warehouse_id:
                                    # الحصول على الرصيد الحالي
                                    cursor.execute("""
                                        SELECT running_balance
                                        FROM inventory_stocktransaction
                                        WHERE product_id = %s AND warehouse_id = %s
                                        ORDER BY transaction_date DESC, id DESC
                                        LIMIT 1
                                    """, [product.id, warehouse_id])
                                    
                                    result = cursor.fetchone()
                                    current_balance = Decimal(str(result[0])) if result and result[0] else Decimal('0')
                                    
                                    if current_balance != 0:
                                        # إفراغ المستودع القديم
                                        cursor.execute("""
                                            INSERT INTO inventory_stocktransaction 
                                            (product_id, warehouse_id, transaction_type, reason, 
                                             quantity, reference, notes, created_by_id, 
                                             running_balance, transaction_date, date)
                                            VALUES (%s, %s, 'OUT', 'transfer', %s, 
                                                    'دمج تلقائي', 'إفراغ لدمج المكررات', %s, 0, NOW(), NOW())
                                        """, [product.id, warehouse_id, float(-current_balance), request.user.id])
                                        
                                        # الحصول على رصيد المستودع المستهدف
                                        cursor.execute("""
                                            SELECT running_balance
                                            FROM inventory_stocktransaction
                                            WHERE product_id = %s AND warehouse_id = %s
                                            ORDER BY transaction_date DESC, id DESC
                                            LIMIT 1
                                        """, [product.id, target_warehouse_id])
                                        
                                        result_target = cursor.fetchone()
                                        target_current_balance = Decimal(str(result_target[0])) if result_target and result_target[0] else Decimal('0')
                                        new_target_balance = target_current_balance + current_balance
                                        
                                        # إضافة للمستودع المستهدف
                                        cursor.execute("""
                                            INSERT INTO inventory_stocktransaction 
                                            (product_id, warehouse_id, transaction_type, reason, 
                                             quantity, reference, notes, created_by_id, 
                                             running_balance, transaction_date, date)
                                            VALUES (%s, %s, 'IN', 'transfer', %s, 
                                                    'دمج تلقائي', 'استقبال من دمج المكررات', %s, %s, NOW(), NOW())
                                        """, [product.id, target_warehouse_id, float(current_balance), request.user.id, float(new_target_balance)])
                                        
                                        # تحديث أوامر التقطيع
                                        try:
                                            old_wh = Warehouse.objects.get(id=warehouse_id)
                                            new_wh = Warehouse.objects.get(id=target_warehouse_id)
                                            update_cutting_orders_after_move(product, old_wh, new_wh, request.user)
                                        except Exception:
                                            pass
                                        
                                        warehouses_merged += 1
                                        total_moved += current_balance

                            merged_count += 1
                            
                            # طباعة ملخص
                            if warehouses_merged > 0 and (idx % 50 == 0 or idx == total):
                                print(f"   ✓ دُمج {warehouses_merged} مستودع، نُقل {float(total_moved)} وحدة")

                        except Exception as e:
                            errors.append(f"{product.name}: {str(e)}")
                            print(f"❌ خطأ: {product.name}: {e}")
                            logger.error(f"❌ {product.name}: {e}")

        finally:
            # إعادة تفعيل signals
            signals.post_save.connect(inventory_signals.stock_manager_handler, sender=StockTransaction)

        # مسح الـ cache
        cache.delete("inventory_duplicates_check")

        print(f"\n{'='*60}")
        print(f"🎉 اكتمل! دمج: {merged_count}/{total}, أخطاء: {len(errors)}")
        print(f"{'='*60}\n")
        logger.info(f"🎉 اكتمل! دمج: {merged_count}/{total}, أخطاء: {len(errors)}")

        return JsonResponse(
            {
                "success": True,
                "merged_count": merged_count,
                "total_duplicates": total,
                "errors": errors,
            }
        )

    except Exception as e:
        print(f"\n❌ خطأ حرج في الدمج: {e}")
        logger.error(f"❌ خطأ في الدمج: {e}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)
