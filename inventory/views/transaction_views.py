"""
Inventory Transaction Views - Stock movement operations
عروض معاملات المخزون - عمليات حركة المخزون
"""

from typing import Any, Dict
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db import transaction as db_transaction
from django.utils import timezone

from inventory.models import Product, Warehouse, StockTransaction
from inventory.permissions import can_transfer_stock
from inventory.inventory_utils import invalidate_product_cache



@login_required
@can_transfer_stock
def transaction_create(request: HttpRequest) -> HttpResponse:
    """
    إنشاء معاملة مخزون جديدة
    
    Args:
        request: طلب HTTP
        
    Returns:
        HttpResponse: نموذج إنشاء المعاملة
    """
    if request.method == "POST":
        try:
            with db_transaction.atomic():
                # الحصول على البيانات من POST
                product_id = request.POST.get("product")
                warehouse_id = request.POST.get("warehouse")
                transaction_type = request.POST.get("transaction_type")
                reason = request.POST.get("reason", "manual")
                quantity = float(request.POST.get("quantity", 0))
                reference = request.POST.get("reference", "")
                notes = request.POST.get("notes", "")

                # التحقق من البيانات
                if not all([product_id, warehouse_id, transaction_type, quantity]):
                    messages.error(request, "جميع الحقول مطلوبة")
                    return redirect("inventory:transaction_create")

                product = get_object_or_404(Product, pk=product_id)
                warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

                # الحصول على آخر معاملة
                last_transaction = (
                    StockTransaction.objects.filter(
                        product=product, warehouse=warehouse
                    )
                    .order_by("-transaction_date", "-id")
                    .first()
                )

                previous_balance = (
                    last_transaction.running_balance if last_transaction else 0
                )

                # حساب الرصيد الجديد
                if transaction_type == "in":
                    new_balance = previous_balance + quantity
                else:  # out
                    new_balance = previous_balance - quantity

                # التحقق من عدم وجود رصيد سالب
                if new_balance < 0:
                    messages.error(
                        request,
                        f"لا يمكن إجراء العملية. الكمية المتاحة: {previous_balance}",
                    )
                    return redirect("inventory:transaction_create")

                # إنشاء المعاملة
                StockTransaction.objects.create(
                    product=product,
                    warehouse=warehouse,
                    transaction_type=transaction_type,
                    reason=reason,
                    quantity=quantity,
                    running_balance=new_balance,
                    reference=reference,
                    notes=notes,
                    created_by=request.user,
                    transaction_date=timezone.now(),
                )

                # تحديث current_stock في المنتج
                invalidate_product_cache(product.id)

                messages.success(request, "تم إضافة المعاملة بنجاح.")
                return redirect("inventory:product_detail", pk=product.id)

        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء إضافة المعاملة: {str(e)}")

    # عرض النموذج
    products = Product.objects.only("id", "name", "code")
    warehouses = Warehouse.objects.filter(is_active=True).only("id", "name")

    context = {
        "products": products,
        "warehouses": warehouses,
        "active_menu": "inventory",
    }

    return render(request, "inventory/transaction_form.html", context)


@login_required
@can_transfer_stock
def transfer_stock(request: HttpRequest) -> HttpResponse:
    """
    نقل مخزون بين مستودعات
    
    Args:
        request: طلب HTTP
        
    Returns:
        HttpResponse: نموذج النقل
    """
    if request.method == "POST":
        product_id = request.POST.get("product")
        from_warehouse_id = request.POST.get("from_warehouse")
        to_warehouse_id = request.POST.get("to_warehouse")
        quantity = request.POST.get("quantity")

        try:
            quantity = float(quantity)
            
            if quantity <= 0:
                messages.error(request, "الكمية يجب أن تكون أكبر من صفر")
                return redirect("inventory:transfer_stock")

            product = get_object_or_404(Product, pk=product_id)
            from_warehouse = get_object_or_404(Warehouse, pk=from_warehouse_id)
            to_warehouse = get_object_or_404(Warehouse, pk=to_warehouse_id)

            if from_warehouse == to_warehouse:
                messages.error(request, "لا يمكن النقل إلى نفس المستودع")
                return redirect("inventory:transfer_stock")

            with db_transaction.atomic():
                # معاملة الصادر من المستودع الأول
                last_from = (
                    StockTransaction.objects.filter(
                        product=product, warehouse=from_warehouse
                    )
                    .order_by("-transaction_date", "-id")
                    .first()
                )

                from_balance = last_from.running_balance if last_from else 0

                if from_balance < quantity:
                    messages.error(
                        request,
                        f"الكمية المتاحة في {from_warehouse.name}: {from_balance}",
                    )
                    return redirect("inventory:transfer_stock")

                # إنشاء معاملة صادر
                StockTransaction.objects.create(
                    product=product,
                    warehouse=from_warehouse,
                    transaction_type="out",
                    reason="transfer",
                    quantity=quantity,
                    running_balance=from_balance - quantity,
                    reference=f"نقل إلى {to_warehouse.name}",
                    notes=f"نقل مخزون إلى {to_warehouse.name}",
                    created_by=request.user,
                    transaction_date=timezone.now(),
                )

                # معاملة الوارد للمستودع الثاني
                last_to = (
                    StockTransaction.objects.filter(
                        product=product, warehouse=to_warehouse
                    )
                    .order_by("-transaction_date", "-id")
                    .first()
                )

                to_balance = last_to.running_balance if last_to else 0

                StockTransaction.objects.create(
                    product=product,
                    warehouse=to_warehouse,
                    transaction_type="in",
                    reason="transfer",
                    quantity=quantity,
                    running_balance=to_balance + quantity,
                    reference=f"نقل من {from_warehouse.name}",
                    notes=f"نقل مخزون من {from_warehouse.name}",
                    created_by=request.user,
                    transaction_date=timezone.now(),
                )

                invalidate_product_cache(product.id)

                messages.success(
                    request,
                    f"تم نقل {quantity} وحدة من {from_warehouse.name} إلى {to_warehouse.name}",
                )
                return redirect("inventory:product_detail", pk=product.id)

        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء النقل: {str(e)}")

    # عرض النموذج
    products = Product.objects.only("id", "name", "code")
    warehouses = Warehouse.objects.filter(is_active=True).only("id", "name")

    context = {
        "products": products,
        "warehouses": warehouses,
        "active_menu": "inventory",
    }

    return render(request, "inventory/transfer_stock.html", context)


@login_required
def get_product_stock_api(request: HttpRequest, product_id: int) -> JsonResponse:
    """
    API للحصول على مخزون منتج في جميع المستودعات
    
    Args:
        request: طلب HTTP
        product_id: معرف المنتج
        
    Returns:
        JsonResponse: بيانات المخزون
    """
    try:
        product = get_object_or_404(Product, pk=product_id)
        warehouses = Warehouse.objects.filter(is_active=True)

        stock_data = []
        for warehouse in warehouses:
            last_transaction = (
                StockTransaction.objects.filter(
                    product=product, warehouse=warehouse
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            stock = last_transaction.running_balance if last_transaction else 0

            stock_data.append(
                {
                    "warehouse_id": warehouse.id,
                    "warehouse_name": warehouse.name,
                    "stock": float(stock),
                }
            )

        return JsonResponse(
            {
                "product_id": product.id,
                "product_name": product.name,
                "total_stock": float(product.current_stock),
                "warehouses": stock_data,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
