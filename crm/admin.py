"""
تخصيص لوحة تحكم Django Admin مع Jazzmin
"""

import json

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from installations.models import CustomerDebt

# تطبيق الإعدادات على الموقع الافتراضي
admin.site.site_header = "نظام إدارة الخواجة"
admin.site.site_title = "لوحة التحكم"
admin.site.index_title = "مرحباً بك في نظام إدارة الخواجة"


def get_admin_stats():
    """إحصائيات سريعة للوحة التحكم مع إدارة المديونيات"""
    try:
        from django.db.models import Count, Sum
        from django.utils import timezone

        from customers.models import Customer
        from inspections.models import Inspection
        from installations.models import CustomerDebt, InstallationPayment
        from manufacturing.models import ManufacturingOrder
        from orders.models import Order

        # Basic stats
        stats = {
            "total_customers": Customer.objects.count(),
            "total_orders": Order.objects.count(),
            "pending_inspections": Inspection.objects.filter(status="pending").count(),
            "active_manufacturing": ManufacturingOrder.objects.filter(
                status="in_progress"
            ).count(),
        }

        # Debt statistics
        debt_stats = CustomerDebt.objects.filter(is_paid=False).aggregate(
            total_debts=Count("id"), total_amount=Sum("debt_amount")
        )

        # Count overdue debts (created more than 30 days ago)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        overdue_count = CustomerDebt.objects.filter(
            is_paid=False, created_at__lt=thirty_days_ago
        ).count()

        stats["debt_stats"] = {
            "total_debts": debt_stats["total_debts"] or 0,
            "total_amount": debt_stats["total_amount"] or 0,
            "overdue_count": overdue_count,
        }

        # Payment statistics for today
        today = timezone.now().date()
        today_payments = InstallationPayment.objects.filter(
            created_at__date=today
        ).aggregate(today_count=Count("id"), today_amount=Sum("amount"))

        # This month payments
        this_month_start = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        this_month_count = InstallationPayment.objects.filter(
            created_at__gte=this_month_start
        ).count()

        stats["payment_stats"] = {
            "today_count": today_payments["today_count"] or 0,
            "today_amount": today_payments["today_amount"] or 0,
            "this_month": this_month_count,
        }

        return stats
    except Exception:
        return {
            "total_customers": 0,
            "total_orders": 0,
            "pending_inspections": 0,
            "active_manufacturing": 0,
            "debt_stats": {"total_debts": 0, "total_amount": 0, "overdue_count": 0},
            "payment_stats": {"today_count": 0, "today_amount": 0, "this_month": 0},
        }


@staff_member_required
def debt_management_view(request):
    """صفحة إدارة المديونيات"""
    # الحصول على المعاملات
    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("search", "")
    min_amount = request.GET.get("min_amount", "")

    # بناء الاستعلام
    debts = CustomerDebt.objects.select_related("customer", "order").all()

    # تطبيق الفلاتر
    if status_filter == "paid":
        debts = debts.filter(is_paid=True)
    elif status_filter == "unpaid":
        debts = debts.filter(is_paid=False)
    elif status_filter == "overdue":
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        debts = debts.filter(is_paid=False, created_at__lt=thirty_days_ago)

    if search_query:
        debts = debts.filter(
            Q(customer__name__icontains=search_query)
            | Q(order__order_number__icontains=search_query)
        )

    if min_amount:
        try:
            min_amount_val = float(min_amount)
            debts = debts.filter(debt_amount__gte=min_amount_val)
        except ValueError:
            pass

    # ترتيب النتائج
    debts = debts.order_by("-created_at")

    # ترقيم الصفحات
    paginator = Paginator(debts, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # إحصائيات سريعة
    stats = {
        "total_debts": CustomerDebt.objects.filter(is_paid=False).count(),
        "total_amount": CustomerDebt.objects.filter(is_paid=False).aggregate(
            total=Sum("debt_amount")
        )["total"]
        or 0,
        "overdue_count": CustomerDebt.objects.filter(
            is_paid=False, created_at__lt=timezone.now() - timezone.timedelta(days=30)
        ).count(),
        "paid_today": CustomerDebt.objects.filter(
            is_paid=True, payment_date__date=timezone.now().date()
        ).count(),
        "paid_amount_today": CustomerDebt.objects.filter(
            is_paid=True, payment_date__date=timezone.now().date()
        ).aggregate(total=Sum("debt_amount"))["total"]
        or 0,
    }

    context = {
        "debts": page_obj,
        "stats": stats,
        "title": "إدارة المديونيات",
    }

    return render(request, "admin/debt_management.html", context)


@staff_member_required
def mark_debt_paid_view(request, debt_id):
    """تسديد المديونية"""
    if request.method == "POST":
        try:
            debt = get_object_or_404(CustomerDebt, id=debt_id)
            debt.is_paid = True
            debt.payment_date = timezone.now()
            debt.payment_receiver_name = (
                request.user.get_full_name() or request.user.username
            )
            debt.notes += f' - تم التسديد بواسطة {debt.payment_receiver_name} في {timezone.now().strftime("%Y-%m-%d %H:%M")}'

            # إنشاء دفعة جديدة في جدول الدفعات
            if debt.order:
                from orders.models import OrderNote, Payment

                Payment.objects.create(
                    order=debt.order,
                    amount=debt.debt_amount,
                    payment_method="cash",  # افتراضي
                    payment_date=debt.payment_date,
                    notes=f"إغلاق مديونية تلقائي من لوحة التحكم بواسطة {debt.payment_receiver_name}",
                    created_by=request.user,
                )

                # إنشاء ملاحظة في الطلب
                OrderNote.objects.create(
                    order=debt.order,
                    note_type="payment",
                    title="تسديد مديونية",
                    content=f"تم تسديد مديونية بمبلغ {debt.debt_amount} ج.م بواسطة {debt.payment_receiver_name} من لوحة التحكم وتسجيل دفعة تلقائية",
                    created_by=request.user,
                )

            debt.save()

            return JsonResponse(
                {"success": True, "message": "تم تسديد المديونية بنجاح وتسجيل الدفعة"}
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "طريقة غير مسموحة"})


# إضافة URLs مخصصة للوحة التحكم
def get_admin_urls():
    """الحصول على URLs إضافية للوحة التحكم"""
    return [
        path("debt-management/", debt_management_view, name="debt_management"),
        path(
            "mark-debt-paid/<int:debt_id>/", mark_debt_paid_view, name="mark_debt_paid"
        ),
    ]


# تسجيل URLs مع AdminSite
admin.site.get_urls = (
    lambda: admin.site.__class__.get_urls(admin.site) + get_admin_urls()
)


# admin_dashboard_view removed


# تخصيص إضافي للـ admin site
class JazzminAdminConfig:
    """إعدادات إضافية لـ Jazzmin"""

    @staticmethod
    def get_dashboard_stats():
        """إحصائيات للوحة التحكم"""
        return get_admin_stats()

    @staticmethod
    def get_recent_actions():
        """الإجراءات الأخيرة"""
        try:
            from django.contrib.admin.models import LogEntry

            return LogEntry.objects.select_related("content_type", "user").order_by(
                "-action_time"
            )[:10]
        except Exception:
            return []
