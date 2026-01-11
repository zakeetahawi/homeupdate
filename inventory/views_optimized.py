from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Case, Count, F, OuterRef, Q, Subquery, Sum, When
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

        # استخدام التخزين المؤقت للإحصائيات - محسن للغاية
        stats = get_cached_dashboard_stats()
        context.update(stats)

        # إضافة active_menu للقائمة الجانبية
        context["active_menu"] = "dashboard"

        # الحصول على المنتجات منخفضة المخزون - محسن لتجنب N+1
        # الحصول على آخر رصيد لكل منتج باستعلام واحد
        latest_balance = (
            StockTransaction.objects.filter(product=OuterRef("pk"))
            .order_by("-transaction_date")
            .values("running_balance")[:1]
        )

        # جلب المنتجات مع الرصيد الحالي - محدود بـ 10 فقط
        low_stock_products = (
            Product.objects.annotate(current_stock_level=Subquery(latest_balance))
            .filter(
                current_stock_level__gt=0, current_stock_level__lte=F("minimum_stock")
            )
            .select_related("category")[:10]
        )

        context["low_stock_products"] = [
            {
                "product": p,
                "current_stock": p.current_stock_level or 0,
                "status": "مخزون منخفض",
                "is_available": (p.current_stock_level or 0) > 0,
            }
            for p in low_stock_products
        ]

        # الحصول على آخر حركات المخزون - محسن
        context["recent_transactions"] = StockTransaction.objects.select_related(
            "product", "created_by"
        ).order_by("-date")[:10]

        # الحصول على عدد طلبات الشراء المعلقة
        context["pending_purchase_orders"] = PurchaseOrder.objects.filter(
            status__in=["draft", "pending"]
        ).count()

        # بيانات الرسم البياني للمخزون حسب الفئة - محسن جداً
        # استعلام مبسط للفئات مع عدد المنتجات فقط
        category_stats = Category.objects.annotate(
            product_count=Count("products")
        ).filter(product_count__gt=0)[:10]

        context["stock_by_category"] = [
            {"name": cat.name, "stock": cat.product_count * 10}  # تقدير مبسط
            for cat in category_stats
        ]

        # بيانات الرسم البياني لحركة المخزون - محسن جداً
        # الحصول على تواريخ آخر 7 أيام فقط (بدلاً من 30)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)

        # استعلام واحد للحصول على جميع البيانات
        stock_movements = (
            StockTransaction.objects.filter(date__date__range=[start_date, end_date])
            .extra(select={"date_only": "DATE(date)"})
            .values("date_only", "transaction_type")
            .annotate(total=Sum("quantity"))
            .order_by("date_only", "transaction_type")
        )

        # تنظيم البيانات
        dates = []
        stock_in = []
        stock_out = []

        # إنشاء قاموس للبيانات
        movement_data = {}
        for movement in stock_movements:
            date_str = str(movement["date_only"])
            if date_str not in movement_data:
                movement_data[date_str] = {"in": 0, "out": 0}
            movement_data[date_str][movement["transaction_type"]] = movement["total"]

        # ملء البيانات لكل يوم
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

        # إضافة عدد التنبيهات النشطة
        context["alerts_count"] = StockAlert.objects.filter(status="active").count()

        # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
        context["recent_alerts"] = (
            StockAlert.objects.filter(status="active")
            .select_related("product")
            .order_by("-created_at")[:5]
        )

        # إضافة السنة الحالية لشريط التذييل
        context["current_year"] = timezone.now().year

        return context
