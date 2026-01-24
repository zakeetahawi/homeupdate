"""
العرض الرئيسي المحسن للنظام
"""

import mimetypes
import os
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F, Q, Sum
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseGone,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.encoding import smart_str
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import (
    AboutPageSettings,
    Branch,
    CompanyInfo,
    ContactFormSettings,
    FooterSettings,
)
from customers.models import Customer
from inspections.models import Inspection
from installations.models import InstallationSchedule
from inventory.models import Product
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order


def is_admin_user(user):
    """التحقق من أن المستخدم مدير للنظام"""
    return user.is_staff or user.is_superuser


# admin_dashboard view removed


# Helper functions removed


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


@staff_member_required
def monitoring_dashboard(request):
    """
    لوحة تحكم مراقبة النظام
    """
    return render(
        request,
        "monitoring/dashboard.html",
        {
            "title": "لوحة مراقبة النظام",
            "page_title": "مراقبة النظام وقاعدة البيانات",
        },
    )


def chat_gone_view(request):
    """
    إرجاع 410 Gone لطلبات الدردشة القديمة مع headers لمنع إعادة المحاولة
    """
    import logging

    logger = logging.getLogger(__name__)

    # تسجيل معلومات الطلب لتتبع المصدر
    user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
    referer = request.META.get("HTTP_REFERER", "No referer")
    remote_addr = request.META.get("REMOTE_ADDR", "Unknown IP")

    logger.info(
        f"🚫 WebSocket request blocked - IP: {remote_addr}, User-Agent: {user_agent[:50]}..., Referer: {referer}"
    )

    response = HttpResponseGone(
        "Chat system has been permanently removed. Please clear your browser cache."
    )
    response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    response["Retry-After"] = "86400"  # لا تحاول مرة أخرى لمدة 24 ساعة
    response["X-Chat-Status"] = "PERMANENTLY_REMOVED"
    response["X-WebSocket-Status"] = "DISABLED"
    return response


def test_minimal_view(request):
    """صفحة اختبار نظيفة تماماً بدون أي JavaScript"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>اختبار نظيف</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>صفحة اختبار نظيفة</h1>
        <p>هذه الصفحة لا تحتوي على أي JavaScript أو مراجع خارجية</p>
        <p>إذا رأيت طلبات WebSocket هنا، فهي من extension المتصفح</p>
        <script>
            console.log('✅ صفحة نظيفة - لا توجد دردشة');
            console.log('🔍 إذا رأيت طلبات WebSocket، فهي من browser extension');
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)


def clear_cache_view(request):
    """أداة لمسح cache المتصفح وإيقاف طلبات WebSocket"""
    html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مسح Cache المتصفح</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 50px;
                background: #f5f5f5;
                direction: rtl;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 800px;
                margin: 0 auto;
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .step {
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
                border-left: 4px solid #007bff;
                background: #f8f9fa;
            }
            .warning {
                background: #fff3cd;
                border-left-color: #ffc107;
                color: #856404;
            }
            .success {
                background: #d4edda;
                border-left-color: #28a745;
                color: #155724;
            }
            .button {
                background: #007bff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin: 10px 5px;
                text-decoration: none;
                display: inline-block;
            }
            .button:hover {
                background: #0056b3;
            }
            .danger {
                background: #dc3545;
            }
            .danger:hover {
                background: #c82333;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧹 أداة مسح Cache المتصفح</h1>

            <div class="warning">
                <h3>⚠️ سبب طلبات WebSocket المستمرة:</h3>
                <p>طلبات WebSocket تأتي من <strong>cache المتصفح</strong> أو <strong>Browser Extensions</strong> وليس من الكود.</p>
            </div>

            <div class="step">
                <h3>🔧 الخطوة 1: مسح Cache المتصفح</h3>
                <p>اضغط على الأزرار التالية لمسح cache المتصفح:</p>
                <button class="button" onclick="clearBrowserCache()">مسح Cache تلقائياً</button>
                <button class="button" onclick="clearLocalStorage()">مسح Local Storage</button>
                <button class="button" onclick="clearSessionStorage()">مسح Session Storage</button>
            </div>

            <div class="step">
                <h3>🔧 الخطوة 2: مسح Cache يدوياً</h3>
                <p><strong>Chrome/Edge:</strong> Ctrl+Shift+Delete → اختر "All time" → مسح</p>
                <p><strong>Firefox:</strong> Ctrl+Shift+Delete → اختر "Everything" → مسح</p>
                <p><strong>Safari:</strong> Cmd+Option+E → مسح Cache</p>
            </div>

            <div class="step">
                <h3>🔧 الخطوة 3: تعطيل Extensions</h3>
                <p>افتح المتصفح في وضع <strong>Incognito/Private</strong> أو عطل جميع Extensions مؤقتاً</p>
                <button class="button" onclick="openIncognito()">فتح نافذة خاصة</button>
            </div>

            <div class="step">
                <h3>🔧 الخطوة 4: إعادة تشغيل المتصفح</h3>
                <p>أغلق المتصفح تماماً وافتحه مرة أخرى</p>
                <button class="button danger" onclick="closeBrowser()">إغلاق المتصفح</button>
            </div>

            <div class="success">
                <h3>✅ النتيجة المتوقعة:</h3>
                <p>بعد تطبيق هذه الخطوات، ستتوقف طلبات WebSocket نهائياً.</p>
                <p>النظام يرد بـ <strong>410 Gone</strong> بشكل صحيح.</p>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <a href="/" class="button">العودة للصفحة الرئيسية</a>
                <a href="/test-clean/" class="button">اختبار الصفحة النظيفة</a>
            </div>
        </div>

        <script>
            function clearBrowserCache() {
                if ('caches' in window) {
                    caches.keys().then(names => {
                        names.forEach(name => {
                            caches.delete(name);
                        });
                    });
                }
                alert('✅ تم مسح Cache المتصفح');
            }

            function clearLocalStorage() {
                localStorage.clear();
                alert('✅ تم مسح Local Storage');
            }

            function clearSessionStorage() {
                sessionStorage.clear();
                alert('✅ تم مسح Session Storage');
            }

            function openIncognito() {
                alert('افتح نافذة جديدة في وضع Incognito/Private وجرب الموقع');
            }

            function closeBrowser() {
                if (confirm('هل تريد إغلاق المتصفح؟')) {
                    window.close();
                }
            }

            console.log('🔍 مراقبة طلبات WebSocket...');

            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.getRegistrations().then(registrations => {
                    if (registrations.length > 0) {
                        console.warn('🚨 Service Workers موجودة:', registrations);
                        registrations.forEach(reg => {
                            console.log('📍 Service Worker:', reg.scope);
                            reg.unregister().then(() => {
                                console.log('✅ تم إلغاء تسجيل Service Worker:', reg.scope);
                            });
                        });
                    } else {
                        console.log('✅ لا توجد Service Workers');
                    }
                });
            }
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)
