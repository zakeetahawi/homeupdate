from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import SystemSettings

from .forms import ProductForm
from .inventory_utils import (
    get_cached_dashboard_stats,
    get_cached_product_list,
    get_cached_stock_level,
    invalidate_product_cache,
)
from .models import Category, Product, PurchaseOrder, StockAlert, StockTransaction


class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # استخدام التخزين المؤقت للإحصائيات
        stats = get_cached_dashboard_stats()
        context.update(stats)

        # إضافة active_menu للقائمة الجانبية
        context["active_menu"] = "dashboard"

        # الحصول على المنتجات منخفضة المخزون مع حالة المخزون
        products = get_cached_product_list(include_stock=True)
        low_stock_products = [
            {"product": p, "status": p.status, "is_available": p.is_available}
            for p in products
            if 0 < get_cached_stock_level(p.id) <= p.minimum_stock
        ]
        context["low_stock_products"] = low_stock_products[:10]

        # الحصول على آخر حركات المخزون
        from .models import StockTransaction

        context["recent_transactions"] = StockTransaction.objects.select_related(
            "product", "created_by"
        ).order_by("-date")[:10]

        # الحصول على عدد طلبات الشراء المعلقة
        from .models import PurchaseOrder

        context["pending_purchase_orders"] = PurchaseOrder.objects.filter(
            status__in=["draft", "pending"]
        ).count()

        # بيانات الرسم البياني للمخزون حسب الفئة - محسن لتجنب N+1
        from django.db.models import Count, Sum

        from .models import Category, Product

        # استخدام استعلام واحد للحصول على جميع المنتجات مع فئاتها
        products_with_categories = Product.objects.select_related("category").all()

        # تجميع المنتجات حسب الفئة في الذاكرة
        category_products = {}
        for product in products_with_categories:
            category_name = product.category.name if product.category else "بدون فئة"
            if category_name not in category_products:
                category_products[category_name] = []
            category_products[category_name].append(product)

        # حساب إجمالي المخزون لكل فئة
        stock_by_category = []
        for category_name, products in category_products.items():
            total_stock = sum(
                get_cached_stock_level(product.id) for product in products
            )
            stock_by_category.append({"name": category_name, "stock": total_stock})

        context["stock_by_category"] = stock_by_category

        # بيانات الرسم البياني لحركة المخزون
        from datetime import timedelta

        from django.utils import timezone

        # الحصول على تواريخ آخر 30 يوم
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)

        dates = []
        stock_in = []
        stock_out = []

        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)

            # حساب إجمالي الوارد والصادر لهذا اليوم
            day_in = (
                StockTransaction.objects.filter(
                    date__date=current_date, transaction_type="in"
                ).aggregate(total=Sum("quantity"))["total"]
                or 0
            )

            day_out = (
                StockTransaction.objects.filter(
                    date__date=current_date, transaction_type="out"
                ).aggregate(total=Sum("quantity"))["total"]
                or 0
            )

            stock_in.append(day_in)
            stock_out.append(day_out)

            current_date += timedelta(days=1)

        context["stock_movement_dates"] = dates
        context["stock_movement_in"] = stock_in
        context["stock_movement_out"] = stock_out

        # إضافة عدد التنبيهات النشطة
        from .models import StockAlert

        context["alerts_count"] = StockAlert.objects.filter(status="active").count()

        # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
        context["recent_alerts"] = (
            StockAlert.objects.filter(status="active")
            .select_related("product")
            .order_by("-created_at")[:5]
        )

        # إضافة السنة الحالية لشريط التذييل
        from datetime import datetime

        context["current_year"] = datetime.now().year

        return context


@login_required
def product_list(request):
    # البحث والتصفية
    search_query = request.GET.get("search", "")
    category_id = request.GET.get("category", "")
    filter_type = request.GET.get("filter", "")
    sort_by = request.GET.get("sort", "-created_at")

    # الحصول على المنتجات من قاعدة البيانات مع حساب المخزون
    products = Product.objects.select_related("category")

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

    # تطبيق فلتر المخزون

    # تطبيق الترتيب
    if hasattr(Product, sort_by.lstrip("-")):
        products = products.order_by(sort_by)
    else:
        products = products.order_by("-created_at")

    # الصفحات
    page_size = request.GET.get("page_size", "20")
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 20
    except Exception:
        page_size = 20
    paginator = Paginator(products, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # إضافة عدد التنبيهات النشطة
    from .models import StockAlert

    alerts_count = StockAlert.objects.filter(status="active").count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = (
        StockAlert.objects.filter(status="active")
        .select_related("product")
        .order_by("-created_at")[:5]
    )

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime

    current_year = datetime.now().year

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "search_query": search_query,
        "selected_category": category_id,
        "selected_filter": filter_type,
        "sort_by": sort_by,
        "active_menu": "products",
        "alerts_count": alerts_count,
        "recent_alerts": recent_alerts,
        "current_year": current_year,
        "page_size": page_size,
        "paginator": paginator,
        "page_number": page_number,
    }

    return render(request, "inventory/product_list_new_icons.html", context)


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                # حفظ المنتج
                product = form.save()

                # إضافة الكمية الحالية إذا تم تحديدها
                initial_quantity = form.cleaned_data.get("initial_quantity", 0)
                warehouse = form.cleaned_data.get("warehouse")

                if initial_quantity > 0 and warehouse:
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

                # إعادة تحميل الذاكرة المؤقتة للمنتجات
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
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            try:
                # حفظ المنتج
                product = form.save()

                # ملاحظة: في التعديل، لا نضيف كمية جديدة تلقائياً
                # يمكن للمستخدم إضافة كمية من خلال صفحة حركات المخزون

                # إعادة تحميل الذاكرة المؤقتة للمنتجات
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
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            product.delete()
            # إعادة تحميل الذاكرة المؤقتة للمنتجات
            invalidate_product_cache(product.id)
            messages.success(request, "تم حذف المنتج بنجاح.")
        except Exception as e:
            messages.error(request, "حدث خطأ أثناء حذف المنتج.")
        return redirect("inventory:product_list")

    return render(
        request, "inventory/product_confirm_delete.html", {"product": product}
    )


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # الحصول على مستوى المخزون من الذاكرة المؤقتة
    current_stock = get_cached_stock_level(product.id)

    # استخدام select_related للمعاملات
    transactions = product.transactions.select_related("created_by").order_by("-date")

    # حساب إجمالي الوارد والصادر
    from django.db.models import Sum

    transactions_in = product.transactions.filter(transaction_type="in")
    transactions_out = product.transactions.filter(transaction_type="out")

    transactions_in_total = (
        transactions_in.aggregate(total=Sum("quantity"))["total"] or 0
    )
    transactions_out_total = (
        transactions_out.aggregate(total=Sum("quantity"))["total"] or 0
    )

    # إعداد بيانات الرسم البياني
    from datetime import timedelta  # Get dates for last 30 days

    from django.utils import timezone

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)

    # Get all transactions up to end_date ordered by transaction_date
    all_transactions = product.transactions.filter(
        transaction_date__date__lte=end_date
    ).order_by("transaction_date")

    # Calculate the running balance for each day in the range
    transaction_dates = []
    transaction_balances = []
    daily_balance = 0

    # Calculate opening balance from transactions before start_date
    opening_transactions = all_transactions.filter(
        transaction_date__date__lt=start_date
    )
    for trans in opening_transactions:
        if trans.transaction_type == "in":
            daily_balance += trans.quantity
        else:
            daily_balance -= trans.quantity

    # إضافة الرصيد لكل يوم    # Iterate through each day in the range
    current_date = start_date
    while current_date <= end_date:
        # Get all transactions for this day
        day_transactions = all_transactions.filter(
            transaction_date__date=current_date
        ).order_by("transaction_date")

        # Update balance with day's transactions
        for trans in day_transactions:
            if trans.transaction_type == "in":
                daily_balance += trans.quantity
            else:
                daily_balance -= trans.quantity

        # Add date and balance to lists
        transaction_dates.append(current_date)
        transaction_balances.append(daily_balance)

        # Move to next day
        current_date += timedelta(days=1)

    # جلب إعدادات النظام
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else "ر.س"

    # إضافة عدد التنبيهات النشطة
    from .models import StockAlert

    alerts_count = StockAlert.objects.filter(status="active").count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = (
        StockAlert.objects.filter(status="active")
        .select_related("product")
        .order_by("-created_at")[:5]
    )

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime

    current_year = datetime.now().year

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
        "alerts_count": alerts_count,
        "recent_alerts": recent_alerts,
        "current_year": current_year,
        "currency_symbol": currency_symbol,
    }
    return render(request, "inventory/product_detail_new_icons.html", context)


@login_required
def transaction_create(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)

    # إضافة أنواع المعاملات وأسبابها للقالب
    transaction_types = [
        ("in", "وارد"),
        ("out", "صادر"),
    ]

    transaction_reasons = [
        ("purchase", "شراء"),
        ("return", "مرتجع"),
        ("adjustment", "تسوية"),
        ("transfer", "نقل"),
        ("sale", "بيع"),
        ("damage", "تالف"),
        ("other", "أخرى"),
    ]

    # الحصول على مستوى المخزون الحالي من الذاكرة المؤقتة
    current_stock = get_cached_stock_level(product.pk)

    if request.method == "POST":
        try:
            # استخراج البيانات من النموذج
            transaction_type = request.POST.get("transaction_type")
            reason = request.POST.get("reason")
            quantity = request.POST.get("quantity")
            reference = request.POST.get("reference", "")
            notes = request.POST.get("notes", "")

            # التحقق من البيانات المطلوبة
            if not all([transaction_type, reason, quantity]):
                raise ValueError("جميع الحقول المطلوبة يجب ملؤها")

            # التحقق من صحة الكمية
            try:
                quantity = float(quantity)
                if quantity <= 0:
                    raise ValueError("يجب أن تكون الكمية أكبر من صفر")
            except (ValueError, TypeError):
                raise ValueError("الكمية يجب أن تكون رقماً صحيحاً")

            # إعادة فحص المخزون الحالي قبل تسجيل الحركة
            current_stock = get_cached_stock_level(product.pk)

            # التحقق من توفر المخزون للحركات الصادرة
            if transaction_type == "out":
                if current_stock <= 0:
                    raise ValueError("لا يوجد مخزون متاح للصرف")
                if quantity > current_stock:
                    raise ValueError(
                        f"الكمية المطلوبة ({quantity}) أكبر من المخزون المتاح ({current_stock})"
                    )

            # إنشاء حركة المخزون
            transaction = StockTransaction.objects.create(
                product=product,
                transaction_type=transaction_type,
                reason=reason,
                quantity=quantity,
                reference=reference,
                notes=notes,
                created_by=request.user,
                date=timezone.now(),
            )

            # إعادة تحميل الذاكرة المؤقتة للمنتج
            invalidate_product_cache(product.id)

            # إضافة رسالة نجاح
            if transaction_type == "in":
                messages.success(
                    request, f"تم تسجيل حركة وارد بنجاح. الكمية: {quantity}"
                )
            else:
                messages.success(
                    request, f"تم تسجيل حركة صادر بنجاح. الكمية: {quantity}"
                )

            return redirect("inventory:product_detail", pk=product.pk)

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء تسجيل حركة المخزون: {str(e)}")

    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status="active").count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = (
        StockAlert.objects.filter(status="active")
        .select_related("product")
        .order_by("-created_at")[:5]
    )

    # إضافة السنة الحالية لشريط التذييل
    current_year = datetime.now().year

    context = {
        "product": product,
        "transaction_types": transaction_types,
        "transaction_reasons": transaction_reasons,
        "current_stock": current_stock,
        "alerts_count": alerts_count,
        "recent_alerts": recent_alerts,
        "current_year": current_year,
    }

    return render(request, "inventory/transaction_form_new.html", context)


# API Endpoints
from django.http import JsonResponse


@login_required
def product_api_detail(request, pk):
    try:
        product = get_object_or_404(Product, pk=pk)
        current_stock = get_cached_stock_level(product.id)

        data = {
            "id": product.id,
            "name": product.name,
            "code": product.code,
            "category": str(product.category),
            "description": product.description,
            "price": product.price,
            "minimum_stock": product.minimum_stock,
            "current_stock": current_stock,
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({"error": "المنتج غير موجود"}, status=404)


@login_required
def product_api_list(request):
    product_type = request.GET.get("type")

    # الحصول على المنتجات من الذاكرة المؤقتة
    products = get_cached_product_list(include_stock=True)

    # تطبيق الفلتر حسب النوع
    if product_type:
        if product_type == "fabric":
            products = [p for p in products if p.category.name == "أقمشة"]
        elif product_type == "accessory":
            products = [p for p in products if p.category.name == "اكسسوارات"]

    # تحويل إلى JSON
    data = [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "category": str(p.category),
            "description": p.description,
            "price": p.price,
            "minimum_stock": p.minimum_stock,
            "current_stock": p.current_stock,
        }
        for p in products
    ]

    return JsonResponse(data, safe=False)


def product_api_autocomplete(request):
    """
    API للبحث السريع عن المنتجات (autocomplete) مع التخزين المؤقت
    يقبل باراميتر ?query= ويعيد قائمة مختصرة (id, name, code, price, current_stock)
    """
    query = request.GET.get("query", "").strip()

    # إذا كان هناك استعلام، استخدم التخزين المؤقت
    if query and len(query) >= 2:
        try:
            from orders.cache import search_products_cached

            results = search_products_cached(query)

            # تحديد النتائج إلى 10 عناصر فقط
            results = results[:10]

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في البحث المؤقت عن المنتجات: {str(e)}")

            # العودة للطريقة التقليدية في حالة الخطأ
            results = []
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            ).select_related("category")[:10]

            for p in products:
                results.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "code": p.code,
                        "price": float(p.price),
                        "current_stock": p.current_stock,
                        "category": p.category.name if p.category else None,
                        "description": p.description,
                    }
                )
    else:
        # للاستعلامات الفارغة أو القصيرة، عرض المنتجات الأكثر شيوعاً
        results = []
        products = Product.objects.select_related("category").order_by("-id")[:10]

        for p in products:
            results.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "code": p.code,
                    "price": float(p.price),
                    "current_stock": p.current_stock,
                    "category": p.category.name if p.category else None,
                    "description": p.description,
                }
            )

    return JsonResponse(results, safe=False)


from django.db.models import Count, Sum

# New API View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import ActivityLog
from customers.models import Customer
from orders.models import Order

from .models import Product


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    try:
        # Calculate statistics
        stats = {
            "totalCustomers": Customer.objects.count(),
            "totalOrders": Order.objects.count(),
            "inventoryValue": Product.objects.aggregate(total=Sum("price", default=0))[
                "total"
            ],
            "pendingInstallations": 0,
        }

        # Get recent activities
        activities = (
            ActivityLog.objects.select_related("user")
            .order_by("-timestamp")[:10]
            .values("id", "type", "description", "timestamp")
        )

        return Response({"stats": stats, "activities": list(activities)})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@login_required
def product_search_api(request):
    """API للبحث عن المنتجات لـ Select2"""
    query = request.GET.get("q", "").strip()
    page = int(request.GET.get("page", 1))
    page_size = 30

    # البحث في المنتجات
    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(description__icontains=query)
        )

    # حساب العدد الإجمالي
    total_count = products.count()

    # تطبيق الصفحات
    start = (page - 1) * page_size
    end = start + page_size
    products = products[start:end]

    # تحضير النتائج
    results = []
    for product in products:
        results.append(
            {
                "id": product.id,
                "text": f"{product.name} - {product.price} ج.م",
                "name": product.name,
                "price": float(product.price),
                "code": product.code or "",
                "current_stock": get_cached_stock_level(product.id),
            }
        )

    return JsonResponse(
        {
            "results": results,
            "pagination": {"more": end < total_count},
            "total_count": total_count,
        }
    )
