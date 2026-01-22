"""
Inventory Product Views - CRUD operations for products
عروض منتجات المخزون - عمليات CRUD للمنتجات
"""

from typing import Any, Dict
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.db.models import Q, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse

from inventory.models import Product, Category, StockTransaction
from inventory.forms import ProductForm
from inventory.permissions import view_product, add_product, change_product, delete_product
from inventory.inventory_utils import invalidate_product_cache


@login_required
@view_product
def product_list(request: HttpRequest) -> HttpResponse:
    """
    عرض قائمة المنتجات مع البحث والفلترة
    
    Args:
        request: طلب HTTP
        
    Returns:
        HttpResponse: صفحة قائمة المنتجات
    """
    # البحث والتصفية
    search_query = request.GET.get("search", "")
    category_id = request.GET.get("category", "")
    filter_type = request.GET.get("filter", "")
    sort_by = request.GET.get("sort", "-created_at")

    # الحصول على المنتجات مع حساب المخزون الحالي
    latest_balance = (
        StockTransaction.objects.filter(product=OuterRef("pk"))
        .order_by("-transaction_date", "-id")
        .values("running_balance")[:1]
    )

    products = (
        Product.objects.select_related("category")
        .annotate(
            current_stock_calc=Coalesce(
                Subquery(latest_balance, output_field=IntegerField()), 0
            )
        )
        .only("id", "name", "code", "price", "category", "created_at", "minimum_stock")
    )

    # تطبيق البحث
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(code__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    # تطبيق فلتر الفئة
    if category_id:
        products = products.filter(category_id=category_id)

    # تطبيق الترتيب
    if hasattr(Product, sort_by.lstrip("-")):
        products = products.order_by(sort_by)
    else:
        products = products.order_by("-created_at")

    # الصفحات
    page_size = request.GET.get("page_size", "50")
    try:
        page_size = int(page_size)
        if page_size > 200:
            page_size = 200
        elif page_size < 1:
            page_size = 50
    except Exception:
        page_size = 50

    paginator = Paginator(products, page_size)
    page_number = request.GET.get("page", "1")

    try:
        page_number = int(page_number) if page_number else 1
    except (ValueError, TypeError):
        page_number = 1

    page_obj = paginator.get_page(page_number)

    # نوع السعر المعروض
    price_display_mode = request.session.get("price_display_mode", "retail")

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.only("id", "name"),
        "search_query": search_query,
        "selected_category": category_id,
        "selected_filter": filter_type,
        "sort_by": sort_by,
        "active_menu": "products",
        "page_size": page_size,
        "paginator": paginator,
        "page_number": page_number,
        "price_display_mode": price_display_mode,
    }

    return render(request, "inventory/product_list_new_icons.html", context)


@login_required
@add_product
def product_create(request: HttpRequest) -> HttpResponse:
    """
    إنشاء منتج جديد
    
    Args:
        request: طلب HTTP
        
    Returns:
        HttpResponse: نموذج إنشاء المنتج
    """
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                product = form.save()

                # إضافة الكمية الحالية إذا تم تحديدها
                initial_quantity = form.cleaned_data.get("initial_quantity", 0)
                warehouse = form.cleaned_data.get("warehouse")

                if initial_quantity > 0 and warehouse:
                    from django.utils import timezone
                    
                    StockTransaction.objects.create(
                        product=product,
                        warehouse=warehouse,
                        transaction_type="in",
                        reason="initial_stock",
                        quantity=initial_quantity,
                        reference="إضافة منتج جديد",
                        notes="الكمية الابتدائية عند إضافة المنتج",
                        created_by=request.user,
                        transaction_date=timezone.now(),
                    )

                invalidate_product_cache(product.id)

                success_msg = "تم إضافة المنتج بنجاح."
                if initial_quantity > 0:
                    success_msg += f" تم إضافة {initial_quantity} وحدة إلى مستودع {warehouse.name}."

                messages.success(request, success_msg)
                return redirect("inventory:product_list")

            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء إضافة المنتج: {str(e)}")
    else:
        form = ProductForm()

    return render(request, "inventory/product_form.html", {"form": form})


@login_required
@change_product
def product_update(request: HttpRequest, pk: int) -> HttpResponse:
    """
    تحديث منتج موجود
    
    Args:
        request: طلب HTTP
        pk: معرف المنتج
        
    Returns:
        HttpResponse: نموذج تحديث المنتج
    """
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            try:
                product = form.save()
                invalidate_product_cache(product.id)
                messages.success(request, "تم تحديث المنتج بنجاح.")
                return redirect("inventory:product_list")

            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء تحديث المنتج: {str(e)}")
    else:
        form = ProductForm(instance=product)

    return render(
        request, "inventory/product_form.html", {"form": form, "product": product}
    )


@login_required
@delete_product
def product_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """
    حذف منتج
    
    Args:
        request: طلب HTTP
        pk: معرف المنتج
        
    Returns:
        HttpResponse: تأكيد الحذف
    """
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        try:
            product.delete()
            invalidate_product_cache(product.id)
            messages.success(request, "تم حذف المنتج بنجاح.")
        except Exception as e:
            messages.error(request, "حدث خطأ أثناء حذف المنتج.")
        return redirect("inventory:product_list")

    return render(
        request, "inventory/product_confirm_delete.html", {"product": product}
    )


@login_required
@view_product
def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    عرض تفاصيل منتج
    
    Args:
        request: طلب HTTP
        pk: معرف المنتج
        
    Returns:
        HttpResponse: صفحة تفاصيل المنتج
    """
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Sum
    
    product = get_object_or_404(Product, pk=pk)

    # الحصول على المخزون الحالي
    current_stock = product.current_stock

    # المعاملات
    transactions = product.transactions.select_related(
        "created_by", "warehouse"
    ).order_by("-transaction_date", "-id")

    # حساب إجمالي الوارد والصادر
    transactions_in = product.transactions.filter(transaction_type="in")
    transactions_out = product.transactions.filter(transaction_type="out")

    transactions_in_total = (
        transactions_in.aggregate(total=Sum("quantity"))["total"] or 0
    )
    transactions_out_total = (
        transactions_out.aggregate(total=Sum("quantity"))["total"] or 0
    )

    # بيانات الرسم البياني
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)

    transaction_dates = []
    transaction_balances = []

    # حساب الرصيد لكل يوم
    from inventory.models import Warehouse
    
    warehouses = Warehouse.objects.filter(is_active=True)
    current_date = start_date
    
    while current_date <= end_date:
        daily_total = 0

        for warehouse in warehouses:
            last_trans = (
                product.transactions.filter(
                    warehouse=warehouse, transaction_date__date__lte=current_date
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            if last_trans:
                daily_total += last_trans.running_balance

        transaction_dates.append(current_date)
        transaction_balances.append(float(daily_total))

        current_date += timedelta(days=1)

    # المخزون حسب المستودع
    warehouses_stock = []
    for warehouse in warehouses:
        last_transaction = (
            StockTransaction.objects.filter(product=product, warehouse=warehouse)
            .order_by("-transaction_date", "-id")
            .first()
        )

        if last_transaction:
            warehouses_stock.append(
                {
                    "warehouse": warehouse,
                    "stock": last_transaction.running_balance,
                    "last_update": last_transaction.transaction_date,
                }
            )

    context = {
        "product": product,
        "current_stock": current_stock,
        "stock_status": (
            "نفذ من المخزون"
            if current_stock == 0
            else "مخزون منخفض" if current_stock <= product.minimum_stock else "متوفر"
        ),
        "transactions": transactions,
        "transactions_in_total": transactions_in_total,
        "transactions_out_total": transactions_out_total,
        "transaction_dates": transaction_dates,
        "transaction_balances": transaction_balances,
        "active_menu": "products",
        "warehouses_stock": warehouses_stock,
    }
    
    return render(request, "inventory/product_detail.html", context)
