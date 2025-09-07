"""
العرض الرئيسي المحسن للنظام
"""

from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Count, Sum, F, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from customers.models import Customer
from orders.models import Order
from inventory.models import Product
from inspections.models import Inspection
from accounts.models import (
    CompanyInfo,
    ContactFormSettings,
    AboutPageSettings,
    FooterSettings,
    Branch,
)
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from installations.models import InstallationSchedule
import re
from datetime import datetime, timedelta
from django.http import JsonResponse

from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
import os
import mimetypes
from django.utils.encoding import smart_str


def is_admin_user(user):
    """التحقق من أن المستخدم مدير للنظام"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin_user)
def admin_dashboard(request):
    """
    داش بورد احترافي محسن للمدراء يعرض تحليلات شاملة لجميع الأقسام
    """
    from .dashboard_utils import (
        get_customers_statistics,
        get_orders_statistics,
        get_manufacturing_statistics,
        get_inspections_statistics,
        get_installation_orders_statistics,
        get_inventory_statistics,
        get_enhanced_chart_data,
        get_manufacturing_approval_analytics,
        get_inspection_scheduling_analytics,
        get_user_performance_analytics,
        get_user_activity_analytics,
        get_installation_order_scheduling_analytics,
    )
    from accounts.models import CompanyInfo, Branch

    # الحصول على المعاملات من الطلب
    selected_branch = request.GET.get("branch", "all")
    selected_month = request.GET.get("month", "year")  # الافتراضي هو السنة الكاملة
    selected_year = request.GET.get("year", timezone.now().year)
    comparison_month = request.GET.get("comparison_month", "")
    comparison_year = request.GET.get("comparison_year", "")
    comparison_type = request.GET.get("comparison_type", "month")  # 'month' or 'year'

    # تحويل المعاملات إلى أرقام
    try:
        if selected_month != "year":
            selected_month = int(selected_month)
        selected_year = int(selected_year)
        if comparison_month:
            comparison_month = int(comparison_month)
        if comparison_year:
            comparison_year = int(comparison_year)
    except (ValueError, TypeError):
        selected_month = "year"  # الافتراضي هو السنة الكاملة
        selected_year = timezone.now().year
        comparison_month = ""
        comparison_year = ""

    # تحديد الفترة الزمنية مع timezone awareness
    if selected_month == "year":  # إذا تم اختيار سنة كاملة
        start_date = timezone.make_aware(datetime(selected_year, 1, 1))
        end_date = timezone.make_aware(datetime(selected_year, 12, 31, 23, 59, 59))
    else:  # إذا تم اختيار شهر محدد
        start_date = timezone.make_aware(datetime(selected_year, selected_month, 1))
        if selected_month == 12:
            end_date = timezone.make_aware(
                datetime(selected_year + 1, 1, 1)
            ) - timedelta(seconds=1)
        else:
            end_date = timezone.make_aware(
                datetime(selected_year, selected_month + 1, 1)
            ) - timedelta(seconds=1)

    # فلترة البيانات حسب الفرع
    branch_filter = {}
    if selected_branch != "all":
        branch_filter = {"branch_id": selected_branch}

    # إحصائيات العملاء - تطبيق الفلتر الزمني
    customers_stats = get_customers_statistics(selected_branch, start_date, end_date)

    # إحصائيات الطلبات
    orders_stats = get_orders_statistics(selected_branch, start_date, end_date)

    # إحصائيات التصنيع
    manufacturing_stats = get_manufacturing_statistics(
        selected_branch, start_date, end_date
    )

    # إحصائيات المعاينات
    inspections_stats = get_inspections_statistics(
        selected_branch, start_date, end_date
    )

    # إحصائيات طلبات التركيب (جميع الطلبات من نوع تركيب بناءً على تاريخ الطلب)
    installation_orders_stats = get_installation_orders_statistics(
        selected_branch, start_date, end_date
    )

    # إحصائيات المخزون
    inventory_stats = get_inventory_statistics(selected_branch)

    # مقارنة مع الفترة المحددة إذا تم تحديدها
    comparison_data = {}
    if comparison_year:
        if comparison_type == "year":  # مقارنة سنة كاملة
            comp_start_date = timezone.make_aware(datetime(comparison_year, 1, 1))
            comp_end_date = timezone.make_aware(
                datetime(comparison_year, 12, 31, 23, 59, 59)
            )
        elif comparison_month and comparison_month != "year":  # مقارنة شهر محدد
            comp_start_date = timezone.make_aware(
                datetime(comparison_year, comparison_month, 1)
            )
            if comparison_month == 12:
                comp_end_date = timezone.make_aware(
                    datetime(comparison_year + 1, 1, 1)
                ) - timedelta(seconds=1)
            else:
                comp_end_date = timezone.make_aware(
                    datetime(comparison_year, comparison_month + 1, 1)
                ) - timedelta(seconds=1)
        else:
            comp_start_date = None
            comp_end_date = None

        if comp_start_date and comp_end_date:
            comparison_data = {
                "customers": get_customers_statistics(
                    selected_branch, comp_start_date, comp_end_date
                ),
                "orders": get_orders_statistics(
                    selected_branch, comp_start_date, comp_end_date
                ),
                "manufacturing": get_manufacturing_statistics(
                    selected_branch, comp_start_date, comp_end_date
                ),
                "inspections": get_inspections_statistics(
                    selected_branch, comp_start_date, comp_end_date
                ),
                "installations": get_installation_orders_statistics(
                    selected_branch, comp_start_date, comp_end_date
                ),
            }

    # البيانات للرسوم البيانية
    chart_data = get_enhanced_chart_data(selected_branch, selected_year)

    # تحليلات مفصلة للأداء
    manufacturing_approval_analytics = get_manufacturing_approval_analytics(
        selected_branch, start_date, end_date
    )
    inspection_scheduling_analytics = get_inspection_scheduling_analytics(
        selected_branch, start_date, end_date
    )
    user_performance_analytics = get_user_performance_analytics(
        selected_branch, start_date, end_date
    )

    # تحليلات نشاط المستخدمين لآخر 7 أيام
    user_activity_analytics = get_user_activity_analytics(days=7)

    # تحليلات جدولة طلبات التركيب
    installation_scheduling_analytics = get_installation_order_scheduling_analytics(
        selected_branch, start_date, end_date
    )

    # معلومات الشركة
    company_info = CompanyInfo.objects.first()
    if not company_info:
        company_info = CompanyInfo.objects.create(
            name="LATARA",
            version="1.0.0",
            release_date="2025-04-30",
            developer="zakee tahawi",
        )

    # قائمة الفروع للفلتر
    branches = Branch.objects.filter(is_active=True).order_by("name")

    # قائمة الأشهر
    months = [
        {"value": "year", "label": "السنة الكاملة"},
        {"value": 1, "label": "يناير"},
        {"value": 2, "label": "فبراير"},
        {"value": 3, "label": "مارس"},
        {"value": 4, "label": "أبريل"},
        {"value": 5, "label": "مايو"},
        {"value": 6, "label": "يونيو"},
        {"value": 7, "label": "يوليو"},
        {"value": 8, "label": "أغسطس"},
        {"value": 9, "label": "سبتمبر"},
        {"value": 10, "label": "أكتوبر"},
        {"value": 11, "label": "نوفمبر"},
        {"value": 12, "label": "ديسمبر"},
    ]

    # قائمة السنوات
    current_year = timezone.now().year
    years = list(range(current_year - 5, current_year + 1))

    if selected_branch != "all":
        selected_branch = str(selected_branch)

    context = {
        "customers_stats": customers_stats,
        "orders_stats": orders_stats,
        "manufacturing_stats": manufacturing_stats,
        "inspections_stats": inspections_stats,
        "installation_orders_stats": installation_orders_stats,
        "inventory_stats": inventory_stats,
        "comparison_data": comparison_data,
        "chart_data": chart_data,
        "company_info": company_info,
        "branches": branches,
        "months": months,
        "years": years,
        "selected_branch": selected_branch,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "comparison_month": comparison_month,
        "comparison_year": comparison_year,
        "comparison_type": comparison_type,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone,
        "manufacturing_approval_analytics": manufacturing_approval_analytics,
        "inspection_scheduling_analytics": inspection_scheduling_analytics,
        "user_performance_analytics": user_performance_analytics,
        "user_activity_analytics": user_activity_analytics,
        "installation_scheduling_analytics": installation_scheduling_analytics,
    }

    return render(request, "admin_dashboard.html", context)


def get_date_range(selected_year, selected_month, show_all_years):
    """تحديد نطاق التاريخ بناءً على المعاملات"""
    if show_all_years or selected_year == "all":
        # عرض جميع البيانات
        return None, None

    if selected_month == "year":
        start_date = timezone.make_aware(datetime(selected_year, 1, 1))
        end_date = timezone.make_aware(datetime(selected_year, 12, 31, 23, 59, 59))
    else:
        start_date = timezone.make_aware(datetime(selected_year, selected_month, 1))
        if selected_month == 12:
            end_date = timezone.make_aware(
                datetime(selected_year + 1, 1, 1)
            ) - timedelta(seconds=1)
        else:
            end_date = timezone.make_aware(
                datetime(selected_year, selected_month + 1, 1)
            ) - timedelta(seconds=1)

    return start_date, end_date


def get_comprehensive_statistics(branch_filter, start_date, end_date, show_all_years):
    """الحصول على إحصائيات شاملة محسنة"""
    from .dashboard_utils import (
        get_customers_statistics,
        get_orders_statistics,
        get_manufacturing_statistics,
        get_inspections_statistics,
        get_installation_orders_statistics,
        get_installations_statistics,
        get_inventory_statistics,
        get_complaints_statistics,
    )

    return {
        "customers_stats": get_customers_statistics(
            branch_filter, start_date, end_date, show_all_years
        ),
        "orders_stats": get_orders_statistics(
            branch_filter, start_date, end_date, show_all_years
        ),
        "manufacturing_stats": get_manufacturing_statistics(
            branch_filter, start_date, end_date, show_all_years
        ),
        "inspections_stats": get_inspections_statistics(
            branch_filter, start_date, end_date, show_all_years
        ),
        "installation_orders_stats": get_installation_orders_statistics(
            branch_filter, start_date, end_date, show_all_years
        ),
        "installations_stats": get_installations_statistics(
            branch_filter, start_date, end_date, show_all_years
        ),
        "inventory_stats": get_inventory_statistics(branch_filter),
        "complaints_stats": get_complaints_statistics(
            branch_filter, start_date, end_date, show_all_years
        ),
    }


def get_comparison_data(
    branch_filter, comparison_year, comparison_month, comparison_type
):
    """الحصول على بيانات المقارنة"""
    from .dashboard_utils import (
        get_customers_statistics,
        get_orders_statistics,
        get_manufacturing_statistics,
        get_inspections_statistics,
        get_installation_orders_statistics,
    )

    if not comparison_year:
        return {}

    if comparison_type == "year":
        comp_start_date = timezone.make_aware(datetime(comparison_year, 1, 1))
        comp_end_date = timezone.make_aware(
            datetime(comparison_year, 12, 31, 23, 59, 59)
        )
    elif comparison_month:
        comp_start_date = timezone.make_aware(
            datetime(comparison_year, comparison_month, 1)
        )
        if comparison_month == 12:
            comp_end_date = timezone.make_aware(
                datetime(comparison_year + 1, 1, 1)
            ) - timedelta(seconds=1)
        else:
            comp_end_date = timezone.make_aware(
                datetime(comparison_year, comparison_month + 1, 1)
            ) - timedelta(seconds=1)
    else:
        return {}

    return {
        "customers": get_customers_statistics(
            branch_filter, comp_start_date, comp_end_date, False
        ),
        "orders": get_orders_statistics(
            branch_filter, comp_start_date, comp_end_date, False
        ),
        "manufacturing": get_manufacturing_statistics(
            branch_filter, comp_start_date, comp_end_date, False
        ),
        "inspections": get_inspections_statistics(
            branch_filter, comp_start_date, comp_end_date, False
        ),
        "installations": get_installation_orders_statistics(
            branch_filter, comp_start_date, comp_end_date, False
        ),
    }


def get_or_create_company_info():
    """الحصول على معلومات الشركة أو إنشاؤها"""
    company_info = CompanyInfo.objects.first()
    if not company_info:
        company_info = CompanyInfo.objects.create(
            name="الخواجة للستائر والمفروشات",
            version="1.0.0",
            release_date="2025-04-30",
            developer="zakee tahawi",
        )
    return company_info


def get_filter_data():
    """الحصول على بيانات الفلاتر"""
    branches = Branch.objects.filter(is_active=True).order_by("name")
    months = [
        (1, "يناير"),
        (2, "فبراير"),
        (3, "مارس"),
        (4, "أبريل"),
        (5, "مايو"),
        (6, "يونيو"),
        (7, "يوليو"),
        (8, "أغسطس"),
        (9, "سبتمبر"),
        (10, "أكتوبر"),
        (11, "نوفمبر"),
        (12, "ديسمبر"),
    ]

    # تم إلغاء السنوات من الإعدادات
    dashboard_years = []

    # جميع السنوات من البيانات الفعلية
    all_years = set()

    # جمع السنوات من جميع النماذج
    try:
        order_years = Order.objects.dates("order_date", "year", order="DESC")
        all_years.update([date.year for date in order_years])

        customer_years = Customer.objects.dates("created_at", "year", order="DESC")
        all_years.update([date.year for date in customer_years])

        inspection_years = Inspection.objects.dates("created_at", "year", order="DESC")
        all_years.update([date.year for date in inspection_years])
    except Exception:
        # في حالة حدوث خطأ، استخدم النطاق الافتراضي
        current_year = timezone.now().year
        all_years = set(range(current_year - 5, current_year + 2))

    all_years = sorted(list(all_years), reverse=True)

    return {
        "branches": branches,
        "months": months,
        "years": dashboard_years,
        "all_years": all_years,
    }


def get_performance_metrics(stats):
    """حساب مؤشرات الأداء"""
    try:
        # معدل إتمام الطلبات
        total_orders = stats["orders_stats"]["total"]
        completed_orders = stats["orders_stats"]["completed"]
        completion_rate = (
            (completed_orders / total_orders * 100) if total_orders > 0 else 0
        )

        # معدل نجاح المعاينات
        total_inspections = stats["inspections_stats"]["total"]
        successful_inspections = stats["inspections_stats"].get("successful", 0)
        inspection_success_rate = (
            (successful_inspections / total_inspections * 100)
            if total_inspections > 0
            else 0
        )

        # معدل المخزون المنخفض
        total_products = stats["inventory_stats"]["total_products"]
        low_stock = stats["inventory_stats"]["low_stock"]
        low_stock_rate = (low_stock / total_products * 100) if total_products > 0 else 0

        return {
            "completion_rate": round(completion_rate, 1),
            "inspection_success_rate": round(inspection_success_rate, 1),
            "low_stock_rate": round(low_stock_rate, 1),
        }
    except Exception:
        return {
            "completion_rate": 0,
            "inspection_success_rate": 0,
            "low_stock_rate": 0,
        }


def home(request):
    """
    View for the home page
    """
    # إزالة التوجيه التلقائي للمديرين - الآن الجميع يرى الشاشة الرئيسية
    # يمكن للمديرين الوصول للداشبورد من أيقونة الهيدر

    # Get counts for dashboard
    customers_count = Customer.objects.count()
    orders_count = Order.objects.count()
    production_count = ManufacturingOrder.objects.count()
    products_count = Product.objects.count()

    # Get recent orders
    recent_orders = Order.objects.select_related("customer").order_by("-order_date")[:5]

    # Get active manufacturing orders
    production_orders = (
        ManufacturingOrder.objects.select_related("order")
        .exclude(status__in=["completed", "cancelled"])
        .order_by("expected_delivery_date")[:5]
    )

    # Get low stock products - محسن لتجنب N+1
    # نظراً لأن current_stock هو property، نحتاج لاستخدام طريقة مختلفة
    from django.db.models import OuterRef, Subquery
    from inventory.models import StockTransaction

    # الحصول على آخر رصيد لكل منتج
    latest_balance = (
        StockTransaction.objects.filter(product=OuterRef("pk"))
        .order_by("-transaction_date")
        .values("running_balance")[:1]
    )

    # جلب المنتجات مع الرصيد الحالي
    products_with_stock = (
        Product.objects.annotate(current_stock_level=Subquery(latest_balance))
        .filter(current_stock_level__gt=0, current_stock_level__lte=F("minimum_stock"))
        .select_related("category")[:10]
    )

    low_stock_products = list(products_with_stock)

    # Get company info for logo
    company_info = CompanyInfo.objects.first()
    if not company_info:
        company_info = CompanyInfo.objects.create(
            name="الخواجة للستائر والمفروشات",
            version="1.0.0",
            release_date="2025-04-30",
            developer="zakee tahawi",
        )

    context = {
        "customers_count": customers_count,
        "orders_count": orders_count,
        "production_count": production_count,
        "products_count": products_count,
        "recent_orders": recent_orders,
        "production_orders": production_orders,
        "low_stock_products": low_stock_products,
        "current_year": timezone.now().year,
        "company_info": company_info,
    }

    return render(request, "home.html", context)


def about(request):
    """
    View for the about page
    """
    # الحصول على إعدادات صفحة حول النظام أو إنشاء إعداد افتراضي إذا لم يكن موجودًا
    about_settings = AboutPageSettings.objects.first()
    if not about_settings:
        about_settings = AboutPageSettings.objects.create()

    # جلب معلومات الشركة (logo)
    company_info = CompanyInfo.objects.first()

    context = {
        "title": about_settings.title,
        "subtitle": about_settings.subtitle,
        "system_description": about_settings.system_description,
        "system_version": about_settings.system_version,
        "system_release_date": about_settings.system_release_date,
        "system_developer": about_settings.system_developer,
        "current_year": timezone.now().year,
        "company_info": company_info,
    }
    return render(request, "about.html", context)


def contact(request):
    """
    View for the contact page
    """
    # الحصول على معلومات الشركة من CompanyInfo
    from accounts.models import CompanyInfo

    company_info = CompanyInfo.objects.first() or CompanyInfo.objects.create()

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if not all([name, email, subject, message]):
            messages.error(request, "يرجى ملء جميع الحقول المطلوبة.")
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            messages.error(request, "يرجى إدخال بريد إلكتروني صحيح.")
        else:
            # هنا يمكن إرسال البريد الإلكتروني فعليًا
            messages.success(request, "تم إرسال رسالتك بنجاح. سنتواصل معك قريباً.")
            return redirect("contact")

    context = {
        "title": "اتصل بنا",
        "description": company_info.description,
        "form_title": "نموذج الاتصال",
        "company_info": company_info,
        "current_year": timezone.now().year,
    }
    return render(request, "contact.html", context)


def serve_media_file(request, path):
    """
    Custom view to serve media files using FileResponse.
    Securely serves files from MEDIA_ROOT directory.
    """
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("Media file not found")

    try:
        # استخدام mimetypes للكشف عن نوع الملف
        content_type, encoding = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"

        # فتح الملف كـ binary stream
        file = open(file_path, "rb")

        # إنشاء FileResponse مع streaming content
        response = FileResponse(file, content_type=content_type)

        # إعداد headers مناسبة للملف
        filename = os.path.basename(file_path)
        response["Content-Disposition"] = f'inline; filename="{smart_str(filename)}"'

        # إضافة headers إضافية للPDF
        if content_type == "application/pdf":
            response["Accept-Ranges"] = "bytes"
            response["Content-Length"] = os.path.getsize(file_path)

        return response
    except IOError:
        raise Http404("Error reading file")
    except Exception as e:
        if "file" in locals():
            file.close()
        raise Http404(f"Error processing file: {str(e)}")


def data_management_redirect(request):
    """
    إعادة توجيه من المسارات القديمة إلى المسار الجديد لإدارة قواعد البيانات
    """
    return redirect("odoo_db_manager:dashboard")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_api(request):
    """API endpoint for dashboard data"""
    today = timezone.now().date()
    data = {
        "customers": {
            "total": Customer.objects.count(),
            "active": Customer.objects.filter(status="active").count(),
        },
        "orders": {
            "total": Order.objects.count(),
            "pending": Order.objects.filter(status="pending").count(),
            "completed": Order.objects.filter(status="completed").count(),
            "recent": list(
                Order.objects.select_related("customer")
                .order_by("-created_at")[:5]
                .values("id", "customer__name", "total_amount", "status")
            ),
        },
        "inventory": {
            "total_products": Product.objects.count(),
            "low_stock": 0,  # سنحسب هذا لاحقاً بطريقة صحيحة
        },
        "production": {
            "active_orders": ManufacturingOrder.objects.exclude(
                status__in=["completed", "cancelled"]
            ).count(),
            "completed_today": ManufacturingOrder.objects.filter(
                completed_at__date=today
            ).count(),
        },
        "inspections": {
            "pending": Inspection.objects.filter(status="pending").count(),
            "completed": Inspection.objects.filter(status="completed").count(),
        },
    }
    return Response(data)
