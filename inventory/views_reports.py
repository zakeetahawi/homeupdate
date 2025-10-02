from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from .inventory_utils import get_cached_product_list, get_cached_stock_level
from .models import Product, StockAlert, StockTransaction


@login_required
def report_list(request):
    """View for listing inventory reports"""
    # الحصول على المنتجات منخفضة المخزون
    products = get_cached_product_list(include_stock=True)
    low_stock_products = [
        p for p in products if 0 < p.current_stock_calc <= p.minimum_stock
    ]

    # الحصول على آخر حركات المخزون
    recent_transactions = StockTransaction.objects.select_related(
        "product", "created_by"
    ).order_by("-date")[:10]

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
        "low_stock_products": low_stock_products[:5],
        "recent_transactions": recent_transactions,
        "active_menu": "inventory_reports",
        "alerts_count": alerts_count,
        "recent_alerts": recent_alerts,
        "current_year": current_year,
    }
    return render(request, "inventory/report_list.html", context)


@login_required
def low_stock_report(request):
    """View for low stock report"""
    # البحث والتصفية
    search_query = request.GET.get("search", "")
    category_id = request.GET.get("category", "")
    sort_by = request.GET.get("sort", "stock")

    # الحصول على المنتجات من الذاكرة المؤقتة
    products = get_cached_product_list(
        category_id=category_id if category_id else None, include_stock=True
    )

    # تصفية المنتجات منخفضة المخزون
    low_stock_products = [
        p for p in products if 0 < p.current_stock_calc <= p.minimum_stock
    ]
    out_of_stock_products = [p for p in products if p.current_stock_calc <= 0]

    # تطبيق البحث
    if search_query:
        low_stock_products = [
            p
            for p in low_stock_products
            if search_query.lower() in p.name.lower()
            or search_query in str(p.code)
            or search_query.lower() in p.description.lower()
        ]
        out_of_stock_products = [
            p
            for p in out_of_stock_products
            if search_query.lower() in p.name.lower()
            or search_query in str(p.code)
            or search_query.lower() in p.description.lower()
        ]

    # تطبيق الترتيب
    if sort_by == "name":
        low_stock_products = sorted(low_stock_products, key=lambda x: x.name)
        out_of_stock_products = sorted(out_of_stock_products, key=lambda x: x.name)
    elif sort_by == "-name":
        low_stock_products = sorted(
            low_stock_products, key=lambda x: x.name, reverse=True
        )
        out_of_stock_products = sorted(
            out_of_stock_products, key=lambda x: x.name, reverse=True
        )
    elif sort_by == "stock":
        low_stock_products = sorted(
            low_stock_products, key=lambda x: x.current_stock_calc
        )
        out_of_stock_products = sorted(
            out_of_stock_products, key=lambda x: x.current_stock_calc
        )
    elif sort_by == "-stock":
        low_stock_products = sorted(
            low_stock_products, key=lambda x: x.current_stock_calc, reverse=True
        )
        out_of_stock_products = sorted(
            out_of_stock_products, key=lambda x: x.current_stock_calc, reverse=True
        )
    elif sort_by == "category":
        low_stock_products = sorted(
            low_stock_products, key=lambda x: x.category.name if x.category else ""
        )
        out_of_stock_products = sorted(
            out_of_stock_products, key=lambda x: x.category.name if x.category else ""
        )

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
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
        "search_query": search_query,
        "selected_category": category_id,
        "sort_by": sort_by,
        "active_menu": "inventory_reports",
        "alerts_count": alerts_count,
        "recent_alerts": recent_alerts,
        "current_year": current_year,
    }
    return render(request, "inventory/low_stock_report.html", context)


@login_required
def stock_movement_report(request):
    """View for stock movement report"""
    # البحث والتصفية
    search_query = request.GET.get("search", "")
    product_id = request.GET.get("product", "")
    transaction_type = request.GET.get("type", "")
    date_range = request.GET.get("date_range", "")

    # البدء بجميع المعاملات
    transactions = StockTransaction.objects.select_related(
        "product", "created_by"
    ).order_by("-date")

    # تطبيق البحث
    if search_query:
        transactions = transactions.filter(
            Q(product__name__icontains=search_query)
            | Q(product__code__icontains=search_query)
            | Q(reference__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    # تصفية حسب المنتج
    if product_id:
        transactions = transactions.filter(product_id=product_id)

    # تصفية حسب نوع المعاملة
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    # تصفية حسب الفترة الزمنية
    today = timezone.now().date()
    if date_range == "today":
        transactions = transactions.filter(date__date=today)
    elif date_range == "week":
        start_of_week = today - timedelta(days=today.weekday())
        transactions = transactions.filter(date__date__gte=start_of_week)
    elif date_range == "month":
        transactions = transactions.filter(
            date__date__year=today.year, date__date__month=today.month
        )
    elif date_range == "quarter":
        current_quarter = (today.month - 1) // 3 + 1
        quarter_start_month = (current_quarter - 1) * 3 + 1
        quarter_start_date = timezone.datetime(
            today.year, quarter_start_month, 1
        ).date()
        transactions = transactions.filter(date__date__gte=quarter_start_date)
    elif date_range == "year":
        transactions = transactions.filter(date__date__year=today.year)

    # الإحصائيات
    total_in = (
        transactions.filter(transaction_type="in").aggregate(total=Sum("quantity"))[
            "total"
        ]
        or 0
    )
    total_out = (
        transactions.filter(transaction_type="out").aggregate(total=Sum("quantity"))[
            "total"
        ]
        or 0
    )
    net_change = total_in - total_out

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

    # الحصول على المنتجات لفلتر البحث
    products = Product.objects.all()

    context = {
        "transactions": transactions[:100],  # تحديد عدد المعاملات المعروضة
        "products": products,
        "total_in": total_in,
        "total_out": total_out,
        "net_change": net_change,
        "search_query": search_query,
        "selected_product": product_id,
        "selected_type": transaction_type,
        "selected_date_range": date_range,
        "active_menu": "inventory_reports",
        "alerts_count": alerts_count,
        "recent_alerts": recent_alerts,
        "current_year": current_year,
    }
    return render(request, "inventory/stock_movement_report.html", context)
