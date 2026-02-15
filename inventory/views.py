from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Case, Count, F, OuterRef, Q, Subquery, Sum, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
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


# ===== API لتبديل وضع عرض السعر =====
@login_required
@require_POST
def toggle_price_display_mode(request):
    """تبديل وضع عرض السعر بين قطاعي وجملة وحفظه في الجلسة"""
    mode = request.POST.get("mode", "retail")
    if mode in ["retail", "wholesale"]:
        request.session["price_display_mode"] = mode
        return JsonResponse({"success": True, "mode": mode})
    return JsonResponse({"success": False, "error": "Invalid mode"}, status=400)


class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # استخدام التخزين المؤقت للإحصائيات - محسن للغاية
        stats = get_cached_dashboard_stats()
        context.update(stats)

        # إضافة active_menu للقائمة الجانبية
        context["active_menu"] = "dashboard"

        # الحصول على المنتجات منخفضة المخزون - محسن جداً
        # استخدام only() وتحديد 5 فقط بدلاً من 10
        latest_balance = (
            StockTransaction.objects.filter(product=OuterRef("pk"))
            .order_by("-transaction_date")
            .values("running_balance")[:1]
        )

        low_stock_products = (
            Product.objects.annotate(current_stock_level=Subquery(latest_balance))
            .filter(
                current_stock_level__gt=0, current_stock_level__lte=F("minimum_stock")
            )
            .select_related("category")
            .only("id", "name", "code", "minimum_stock", "category__name")[:5]
        )  # من 10 إلى 5

        context["low_stock_products"] = [
            {
                "product": p,
                "current_stock": p.current_stock_level or 0,
                "status": "مخزون منخفض",
                "is_available": (p.current_stock_level or 0) > 0,
            }
            for p in low_stock_products
        ]

        # آخر حركات المخزون - محسّن
        recent_transactions = (
            StockTransaction.objects.select_related("product", "created_by")
            .only(
                "id",
                "product__name",
                "transaction_type",
                "quantity",
                "date",
                "created_by__username",
            )
            .order_by("-date")[:5]
        )  # من 10 إلى 5

        context["recent_transactions"] = recent_transactions

        # عدد طلبات الشراء المعلقة - استخدام count فقط
        context["pending_purchase_orders"] = PurchaseOrder.objects.filter(
            status__in=["draft", "pending"]
        ).count()

        # بيانات الرسم البياني - محسّن جداً
        category_stats = (
            Category.objects.annotate(product_count=Count("products"))
            .filter(product_count__gt=0)
            .only("id", "name")
            .order_by("-product_count")[:5]
        )  # من 10 إلى 5

        stock_by_category = []
        for cat in category_stats:
            # حساب مبسّط باستخدام aggregate فقط
            total_stock = (
                StockTransaction.objects.filter(product__category=cat).aggregate(
                    total=Sum("running_balance")
                )["total"]
                or 0
            )

            stock_by_category.append(
                {
                    "name": cat.name,
                    "stock": int(total_stock),
                    "product_count": cat.product_count,
                }
            )

        context["stock_by_category"] = stock_by_category

        # بيانات حركة المخزون - محسّن (3 أيام فقط)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=2)  # من 6 إلى 2

        from django.db.models.functions import TruncDate

        stock_movements = (
            StockTransaction.objects.filter(date__date__range=[start_date, end_date])
            .annotate(date_only=TruncDate("date"))
            .values("date_only", "transaction_type")
            .annotate(total=Sum("quantity"))
            .order_by("date_only", "transaction_type")
        )

        # تنظيم البيانات
        dates = []
        stock_in = []
        stock_out = []

        movement_data = {}
        for movement in stock_movements:
            date_str = str(movement["date_only"])
            if date_str not in movement_data:
                movement_data[date_str] = {"in": 0, "out": 0}
            movement_data[date_str][movement["transaction_type"]] = movement["total"]

        current_date = start_date
        while current_date <= end_date:
            date_str = str(current_date)
            dates.append(current_date)
            stock_in.append(movement_data.get(date_str, {}).get("in", 0))
            stock_out.append(movement_data.get(date_str, {}).get("out", 0))
            current_date += timedelta(days=1)

        context["stock_movement_dates"] = dates
        context["stock_movement_in"] = stock_in
        context["stock_movement_out"] = stock_out

        # التنبيهات - محسّن
        context["alerts_count"] = StockAlert.objects.filter(status="active").count()
        context["recent_alerts"] = (
            StockAlert.objects.filter(status="active")
            .select_related("product")
            .only("id", "product__name", "alert_type", "created_at")
            .order_by("-created_at")[:3]
        )  # من 5 إلى 3

        context["current_year"] = timezone.now().year

        return context


@login_required
def product_list(request):
    # البحث والتصفية
    search_query = request.GET.get("search", "")
    category_id = request.GET.get("category", "")
    filter_type = request.GET.get("filter", "")
    sort_by = request.GET.get("sort", "-created_at")

    # الحصول على المنتجات مع حساب المخزون الحالي
    # استخدام Subquery للحصول على آخر رصيد من جدول StockTransaction
    from django.db.models import IntegerField, OuterRef, Subquery
    from django.db.models.functions import Coalesce

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

    # ملاحظة: لا نطبق فلتر السنة على المنتجات لأنها دائمة وليست مرتبطة بسنة معينة

    # تطبيق فلتر الفئة
    if category_id:
        products = products.filter(category_id=category_id)

    # تطبيق فلاتر خاصة
    if filter_type == "low_stock":
        # المنتجات التي المخزون الحالي أقل من الحد الأدنى
        products = products.filter(current_stock_calc__lt=F('minimum_stock'))
    elif filter_type == "out_of_stock":
        # المنتجات التي المخزون = 0
        products = products.filter(current_stock_calc=0)
    elif filter_type == "in_stock":
        # المنتجات المتوفرة في المخزون
        products = products.filter(current_stock_calc__gt=0)

    # تطبيق الترتيب
    valid_sort_fields = ['name', 'code', 'price', 'created_at', 'minimum_stock']
    sort_field = sort_by.lstrip("-")
    
    if sort_field in valid_sort_fields:
        products = products.order_by(sort_by)
    elif sort_field == 'current_stock':
        # ترتيب حسب المخزون الحالي
        products = products.order_by(sort_by.replace('current_stock', 'current_stock_calc'))
    else:
        products = products.order_by("-created_at")

    # الصفحات - زيادة الحجم الافتراضي
    page_size = request.GET.get("page_size", "50")  # من 20 إلى 50
    try:
        page_size = int(page_size)
        if page_size > 200:  # من 100 إلى 200
            page_size = 200
        elif page_size < 1:
            page_size = 50
    except Exception:
        page_size = 50

    paginator = Paginator(products, page_size)
    page_number = request.GET.get("page", "1")

    # إصلاح مشكلة pagination - تبسيط المنطق
    try:
        page_number = int(page_number) if page_number else 1
    except (ValueError, TypeError):
        page_number = 1

    page_obj = paginator.get_page(page_number)

    # التنبيهات - محسّن
    from .models import StockAlert

    alerts_count = StockAlert.objects.filter(status="active").count()
    recent_alerts = (
        StockAlert.objects.filter(status="active")
        .select_related("product")
        .only("id", "product__name", "alert_type", "created_at")
        .order_by("-created_at")[:5]
    )

    from datetime import datetime

    current_year = datetime.now().year

    # ===== نوع السعر المعروض (قطاعي/جملة) - محفوظ في الجلسة =====
    price_display_mode = request.session.get("price_display_mode", "retail")

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.only("id", "name"),
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
        "price_display_mode": price_display_mode,
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

    # الحصول على المخزون الحالي من property (يحسب من جميع المستودعات)
    current_stock = product.current_stock

    # استخدام select_related للمعاملات
    transactions = product.transactions.select_related(
        "created_by", "warehouse"
    ).order_by("-transaction_date", "-id")

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

    # إعداد بيانات الرسم البياني - استخدام running_balance
    from datetime import timedelta

    from django.utils import timezone

    from .models import Warehouse

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)

    # حساب الرصيد لكل يوم باستخدام running_balance من جميع المستودعات
    transaction_dates = []
    transaction_balances = []

    # الحصول على جميع المستودعات النشطة
    warehouses = Warehouse.objects.filter(is_active=True)

    # لكل يوم، احسب مجموع الرصيد من جميع المستودعات
    current_date = start_date
    while current_date <= end_date:
        daily_total = 0

        # لكل مستودع، احصل على آخر رصيد حتى هذا اليوم
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

    # جلب إعدادات النظام
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else "ج.م"

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

    # الحصول على المخزون حسب المستودع
    from django.db.models import Max

    from .models import StockTransaction, Warehouse

    warehouses_stock = []
    warehouses = Warehouse.objects.filter(is_active=True)

    for warehouse in warehouses:
        # الحصول على آخر حركة للمنتج في هذا المستودع
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
        "alerts_count": alerts_count,
        "recent_alerts": recent_alerts,
        "current_year": current_year,
        "currency_symbol": currency_symbol,
        "warehouses_stock": warehouses_stock,
    }
    return render(request, "inventory/product_detail.html", context)


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

    # الحصول على مستوى المخزون الحالي من property
    current_stock = product.current_stock

    # الحصول على المستودعات النشطة مع مخزونها
    from .models import Warehouse

    warehouses_list = []
    for warehouse in Warehouse.objects.filter(is_active=True):
        last_trans = (
            StockTransaction.objects.filter(product=product, warehouse=warehouse)
            .order_by("-transaction_date", "-id")
            .first()
        )

        warehouses_list.append(
            {
                "id": warehouse.id,
                "name": warehouse.name,
                "stock": last_trans.running_balance if last_trans else 0,
            }
        )

    if request.method == "POST":
        try:
            # استخراج البيانات من النموذج
            transaction_type = request.POST.get("transaction_type")
            reason = request.POST.get("reason")
            quantity = request.POST.get("quantity")
            warehouse_id = request.POST.get("warehouse")
            reference = request.POST.get("reference", "")
            notes = request.POST.get("notes", "")

            # التحقق من البيانات المطلوبة
            if not all([transaction_type, reason, quantity, warehouse_id]):
                raise ValueError("جميع الحقول المطلوبة يجب ملؤها")

            # التحقق من صحة الكمية
            try:
                quantity = Decimal(quantity)
                if quantity <= 0:
                    raise ValueError("يجب أن تكون الكمية أكبر من صفر")
            except (ValueError, TypeError, Exception):
                raise ValueError("الكمية يجب أن تكون رقماً صحيحاً")

            # الحصول على المستودع
            warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

            # تحديث وحدة القياس إذا تم تغييرها
            new_unit = request.POST.get("unit")
            if new_unit and new_unit != product.unit:
                # التحقق من أن الوحدة صالحة
                valid_units = [choice[0] for choice in Product.UNIT_CHOICES]
                if new_unit in valid_units:
                    product.unit = new_unit
                    product.save()
                    # تحديث الكائن في الذاكرة
                    product.refresh_from_db()

            # إعادة فحص المخزون الحالي قبل تسجيل الحركة
            current_stock = product.current_stock

            # الحصول على مخزون المستودع المحدد
            warehouse_stock = 0
            last_trans = (
                StockTransaction.objects.filter(product=product, warehouse=warehouse)
                .order_by("-transaction_date", "-id")
                .first()
            )

            if last_trans:
                warehouse_stock = last_trans.running_balance

            # التحقق من توفر المخزون للحركات الصادرة
            if transaction_type == "out":
                if warehouse_stock <= 0:
                    raise ValueError(
                        f"لا يوجد مخزون متاح للصرف من مستودع {warehouse.name}"
                    )
                if quantity > warehouse_stock:
                    raise ValueError(
                        f"الكمية المطلوبة ({quantity}) أكبر من المخزون المتاح في {warehouse.name} ({warehouse_stock})"
                    )

            # حساب running_balance
            if last_trans:
                previous_balance = last_trans.running_balance
            else:
                previous_balance = 0

            if transaction_type == "in":
                new_balance = previous_balance + quantity
            else:
                new_balance = previous_balance - quantity

            # إنشاء حركة المخزون
            transaction = StockTransaction.objects.create(
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

            # إعادة تحميل الذاكرة المؤقتة للمنتج
            invalidate_product_cache(product.id)

            # إضافة رسالة نجاح
            if transaction_type == "in":
                messages.success(
                    request,
                    f"تم تسجيل حركة وارد بنجاح إلى {warehouse.name}. الكمية: {quantity}",
                )
            else:
                messages.success(
                    request,
                    f"تم تسجيل حركة صادر بنجاح من {warehouse.name}. الكمية: {quantity}",
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
        "unit_choices": Product.UNIT_CHOICES,
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


@login_required
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


@login_required
def barcode_scan_api(request):
    """
    API لفحص الباركود والحصول على معلومات المنتج
    يستقبل كود المنتج ويرجع كل المعلومات
    """
    barcode = request.GET.get("barcode", "").strip()

    if not barcode:
        return JsonResponse(
            {"success": False, "error": "لم يتم توفير رمز الباركود"}, status=400
        )

    try:
        # البحث عن المنتج بواسطة الكود أولاً، ثم بالاسم
        try:
            product = Product.objects.select_related("category").get(code=barcode)
        except Product.DoesNotExist:
            # محاولة البحث بالاسم (مطابقة تامة أو جزئية)
            products = Product.objects.select_related("category").filter(
                Q(name__iexact=barcode) | Q(name__icontains=barcode)
            )
            if products.exists():
                product = products.first()
            else:
                raise Product.DoesNotExist()

        # حساب المخزون الحالي من جميع المستودعات
        current_stock = product.current_stock

        # الحصول على المخزون حسب المستودع
        from .models import Warehouse

        warehouses_stock = []
        warehouses = Warehouse.objects.filter(is_active=True)

        for warehouse in warehouses:
            last_transaction = (
                StockTransaction.objects.filter(product=product, warehouse=warehouse)
                .order_by("-transaction_date", "-id")
                .first()
            )

            if last_transaction and last_transaction.running_balance > 0:
                warehouses_stock.append(
                    {
                        "warehouse_id": warehouse.id,
                        "warehouse_name": warehouse.name,
                        "warehouse_code": warehouse.code,
                        "stock": float(last_transaction.running_balance),
                        "last_update": last_transaction.transaction_date.strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    }
                )

        # جلب إعدادات النظام للعملة
        system_settings = SystemSettings.get_settings()
        currency_symbol = system_settings.currency_symbol if system_settings else "ج.م"

        # تجهيز البيانات
        data = {
            "success": True,
            "product": {
                "id": product.id,
                "name": product.name,
                "code": product.code,
                "price": float(product.price),
                "currency": product.currency,
                "currency_symbol": currency_symbol,
                "unit": product.unit,
                "unit_display": product.get_unit_display(),
                "category": product.category.name if product.category else "غير مصنف",
                "description": product.description,
                "current_stock": float(current_stock),
                "minimum_stock": product.minimum_stock,
                "stock_status": product.stock_status,
                "is_available": product.is_available,
                "warehouses": warehouses_stock,
                "created_at": product.created_at.strftime("%Y-%m-%d"),
            },
        }

        return JsonResponse(data)

    except Product.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "المنتج غير موجود",
                "message": f"لا يوجد منتج بكود الباركود: {barcode}",
            },
            status=404,
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": "حدث خطأ أثناء البحث عن المنتج",
                "message": str(e),
            },
            status=500,
        )


# ==================== QR Code Generation APIs ====================


@login_required
def generate_single_qr_api(request, pk):
    """
    API لتوليد QR لمنتج واحد
    POST /inventory/api/product/<pk>/generate-qr/
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    product = get_object_or_404(Product, pk=pk)

    if not product.code:
        return JsonResponse(
            {"success": False, "error": "لا يوجد كود للمنتج - لا يمكن توليد QR"}
        )

    # التحقق من وجود QR مسبق
    had_existing = bool(product.qr_code_base64)

    # توليد QR (مع الإجبار لإعادة التوليد)
    product.generate_qr(force=True)
    product.save(update_fields=["qr_code_base64"])

    return JsonResponse(
        {
            "success": True,
            "message": (
                "تم إعادة توليد رمز QR بنجاح"
                if had_existing
                else "تم توليد رمز QR بنجاح"
            ),
            "qr_exists": True,
            "product_code": product.code,
        }
    )


@login_required
def generate_all_qr_api(request):
    """
    API لتوليد QR للمنتجات الأساسية (النظام الجديد)
    POST /inventory/api/generate-all-qr/
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method not allowed"}, status=405
        )

    from .models import BaseProduct

    # الحصول على المنتجات الأساسية التي ليس لها QR ولديها كود
    base_products_no_qr = (
        BaseProduct.objects.filter(qr_code_base64__isnull=True)
        .exclude(code__isnull=True)
        .exclude(code="")
    )

    total = base_products_no_qr.count()

    if total == 0:
        return JsonResponse(
            {
                "success": True,
                "message": "جميع المنتجات لديها رموز QR بالفعل!",
                "generated": 0,
                "total": 0,
            }
        )

    generated = 0
    errors = 0
    error_list = []

    # معالجة المنتجات (بحد أقصى 500 لتجنب التوقف)
    LIMIT = 500
    for bp in base_products_no_qr[:LIMIT]:
        try:
            if bp.generate_qr():
                # استخدام update_fields للتحديث السريع والآمن
                BaseProduct.objects.filter(pk=bp.pk).update(
                    qr_code_base64=bp.qr_code_base64
                )
                generated += 1
        except Exception as e:
            errors += 1
            error_list.append(f"{bp.code}: {str(e)}")

    remaining = total - generated - errors

    return JsonResponse(
        {
            "success": True,
            "message": f"تم توليد {generated} رمز QR. الأخطاء: {errors}. المتبقي: {remaining}",
            "generated": generated,
            "errors": errors,
            "remaining": remaining,
            "total": total,
        }
    )


@login_required
def generate_qr_pdf_api(request):
    """
    API لتوليد وتحميل ملف PDF للـ QR Codes
    GET /inventory/api/generate-qr-pdf/
    """
    import os

    from django.conf import settings
    from django.core.management import call_command

    try:
        # Define output relative to MEDIA_ROOT
        filename = "products_qr_catalog.pdf"
        relative_path = os.path.join("qr_codes", filename)
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Run command
        call_command("generate_qr_pdf", output=full_path)

        # Construct URL
        file_url = os.path.join(settings.MEDIA_URL, relative_path)

        return JsonResponse(
            {"success": True, "message": "تم توليد ملف PDF بنجاح", "file_url": file_url}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ==================== Excel Export API ====================


@login_required
def export_products_excel(request):
    """
    تصدير جميع المنتجات إلى ملف Excel
    يحتوي على: الكود، اسم المنتج، الفئة، السعر، المخزون الحالي
    """
    # فحص الصلاحية - فقط المستخدمون الذين لديهم can_export=True
    if not request.user.can_export:
        messages.error(request, "ليس لديك صلاحية تصدير البيانات")
        return redirect("inventory:product_list")

    from django.db.models import IntegerField, OuterRef, Subquery
    from django.db.models.functions import Coalesce
    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    # إنشاء ملف Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "قائمة المنتجات"

    # تنسيق العناوين
    header_fill = PatternFill(
        start_color="4472C4", end_color="4472C4", fill_type="solid"
    )
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")

    # إضافة العناوين
    headers = [
        "Code",
        "Product Name",
        "Category",
        "Price",
        "Wholesale Price",
        "Currency",
        "Unit",
        "Width",
        "Material",
        "Description",
        "Total Stock",
        "Warehouse",
        "Quantity",
        "Min Stock",
        "Date Added",
        "Last Updated",
        "Status",
    ]
    ws.append(headers)

    # تنسيق صف العناوين
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment

    # الحصول على المنتجات مع المخزون الحالي
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
        .order_by("code")
    )

    # تجهيز قائمة المستودعات النشطة
    from .models import Warehouse

    active_warehouses = list(Warehouse.objects.filter(is_active=True))

    # تحسين الأداء: جلب أرصدة المستودعات دفعة واحدة لتجنب N+1 queries
    # سنقوم بجلب أحدث حركة لكل (منتج، مستودع)
    # ملاحظة: هذا يتطلب استعلاماً معقداً قليلاً، لذا للتبسيط والسرعة سنقوم بجلب كل الأرصدة الحالية
    # ونقوم بتجميعها في القاموس.

    # 1. جلب معرفات المنتجات
    product_ids = [p.id for p in products]

    # 2. جلب أحدث الحركات لكل منتج ومستودع
    # نستخدم Subquery للحصول على ID أحدث حركة
    from django.db.models import Max

    latest_tx_ids = (
        StockTransaction.objects.filter(
            product_id__in=product_ids, warehouse__in=active_warehouses
        )
        .values("product_id", "warehouse_id")
        .annotate(max_id=Max("id"))
        .values("max_id")
    )

    stock_data = StockTransaction.objects.filter(id__in=latest_tx_ids).values(
        "product_id", "warehouse__name", "running_balance"
    )

    # 3. تحويل البيانات إلى قاموس للوصول السريع
    # structure: {product_id: [{'name': warehouse_name, 'qty': balance}, ...]}
    product_stock_map = {}
    for item in stock_data:
        p_id = item["product_id"]
        w_name = item["warehouse__name"]
        balance = item["running_balance"]

        if balance > 0:
            if p_id not in product_stock_map:
                product_stock_map[p_id] = []
            product_stock_map[p_id].append({"name": w_name, "qty": balance})

    # إضافة البيانات
    for product in products:
        # تحديد الحالة
        if product.current_stock_calc == 0:
            status = "Out of Stock"
        elif product.current_stock_calc <= product.minimum_stock:
            status = "Low Stock"
        else:
            status = "Available"

        # البيانات الأساسية للمنتج
        base_row = [
            str(product.code or "-"),
            str(product.name),
            str(product.category.name if product.category else "Uncategorized"),
            float(product.price),
            float(product.wholesale_price),
            str(product.currency),
            str(product.get_unit_display()),
            str(product.width),
            str(product.material),
            str(product.description),
            product.current_stock_calc,
        ]

        # البيانات الختامية
        end_row = [
            product.minimum_stock,
            product.created_at.strftime("%Y-%m-%d"),
            product.updated_at.strftime("%Y-%m-%d %H:%M"),
            status,
        ]

        # تفاصيل المستودعات (صفوف متعددة)
        wh_entries = product_stock_map.get(product.id, [])

        if wh_entries:
            for entry in wh_entries:
                # دمج: أساسي + مستودع + كمية + ختامي
                full_row = base_row + [entry["name"], entry["qty"]] + end_row
                ws.append(full_row)
        else:
            # صف واحد ببيانات فارغة للمستودع إذا لم يوجد مخزون
            full_row = base_row + ["-", 0] + end_row
            ws.append(full_row)

    # تنسيق الأعمدة
    for col_num in range(1, len(headers) + 1):
        column_letter = get_column_letter(col_num)

        # تعيين عرض العمود
        if col_num == 1:  # الكود
            ws.column_dimensions[column_letter].width = 15
        elif col_num == 2:  # اسم المنتج
            ws.column_dimensions[column_letter].width = 40
        elif col_num == 3:  # الفئة
            ws.column_dimensions[column_letter].width = 20
        elif col_num == 10:  # Description
            ws.column_dimensions[column_letter].width = 50
        elif col_num == 12:  # Warehouse Name
            ws.column_dimensions[column_letter].width = 25
        elif col_num == 13:  # Quantity
            ws.column_dimensions[column_letter].width = 15
        elif col_num in [15, 16]:  # Dates
            ws.column_dimensions[column_letter].width = 20
        else:
            ws.column_dimensions[column_letter].width = 15

        # محاذاة النص
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row=row, column=col_num)
            if col_num in [4, 5, 6]:  # الأعمدة الرقمية
                cell.alignment = Alignment(horizontal="center")
            else:
                cell.alignment = Alignment(horizontal="right")

    # إعداد الاستجابة
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # تسمية الملف بالتاريخ الحالي
    from datetime import datetime

    filename = f"products_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    # حفظ الملف
    wb.save(response)

    return response
