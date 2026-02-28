import logging
import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView

from accounts.models import User
from inventory.models import Warehouse
from manufacturing.models import FabricReceipt, FabricReceiptItem
from orders.models import Order

from .models import CuttingOrder, CuttingOrderItem, CuttingReport



logger = logging.getLogger(__name__)

def get_user_warehouses_for_user(user):
    """Helper function للحصول على المستودعات المتاحة للمستخدم - يدعم مستودعات متعددة"""
    if user.is_superuser:
        return Warehouse.objects.filter(is_active=True)
    # موظف مستودع: الوصول للمستودعات المخصصة له (متعددة)
    elif hasattr(user, "is_warehouse_staff") and user.is_warehouse_staff:
        warehouses = user.get_all_assigned_warehouses()
        if warehouses.exists():
            return warehouses
        else:
            return Warehouse.objects.none()
    return Warehouse.objects.filter(is_active=True)


def user_has_warehouse_access(user, warehouse_id):
    """التحقق من صلاحية المستخدم للوصول لمستودع معين - يدعم مستودعات متعددة"""
    user_warehouses = get_user_warehouses_for_user(user)
    return user_warehouses.filter(id=warehouse_id).exists()


class CuttingDashboardView(LoginRequiredMixin, TemplateView):
    """لوحة تحكم نظام التقطيع"""

    template_name = "cutting/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # الحصول على المستودعات المتاحة للمستخدم مع إحصائيات مفصلة
        user_warehouses = self.get_user_warehouses_with_stats()

        # إحصائيات عامة — استعلام واحد بدلاً من 4 استعلامات
        warehouse_ids = [w["id"] for w in user_warehouses]
        general_stats = CuttingOrder.objects.filter(
            warehouse_id__in=warehouse_ids
        ).aggregate(
            total_orders=Count('id'),
            pending_orders=Count('id', filter=Q(status="pending")),
            in_progress_orders=Count('id', filter=Q(status="in_progress")),
            completed_orders=Count('id', filter=Q(status="completed")),
        )

        context.update(
            {
                "total_orders": general_stats["total_orders"],
                "pending_orders": general_stats["pending_orders"],
                "in_progress_orders": general_stats["in_progress_orders"],
                "completed_orders": general_stats["completed_orders"],
                "user_warehouses": user_warehouses,
                "recent_orders": CuttingOrder.objects.filter(
                    warehouse_id__in=warehouse_ids
                )
                .select_related("order", "order__customer", "warehouse")
                .defer("rejection_reason", "notes", "notifications_sent")
                .order_by("-created_at")[:10],
            }
        )

        return context

    def get_user_warehouses(self):
        """الحصول على المستودعات المتاحة للمستخدم - يدعم مستودعات متعددة"""
        user = self.request.user

        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)

        # موظف مستودع: الوصول للمستودعات المخصصة له (متعددة)
        elif hasattr(user, "is_warehouse_staff") and user.is_warehouse_staff:
            warehouses = user.get_all_assigned_warehouses()
            if warehouses.exists():
                return warehouses
            else:
                # إذا لم يكن لديه مستودعات مخصصة، لا يرى أي مستودعات
                return Warehouse.objects.none()

        return Warehouse.objects.filter(is_active=True)

    def get_user_warehouses_with_stats(self):
        """الحصول على المستودعات مع إحصائيات أوامر التقطيع — محسّن باستعلام واحد"""
        warehouses = self.get_user_warehouses()

        # استعلام واحد بدلاً من 3 استعلامات لكل مستودع
        warehouses_annotated = warehouses.annotate(
            total_orders=Count('cutting_orders'),
            pending_orders=Count('cutting_orders', filter=Q(
                cutting_orders__status__in=["pending", "in_progress", "partially_completed"]
            )),
            completed_orders=Count('cutting_orders', filter=Q(cutting_orders__status="completed")),
        )

        warehouse_stats = []
        for warehouse in warehouses_annotated:
            warehouse_stats.append(
                {
                    "warehouse": warehouse,
                    "total_orders": warehouse.total_orders,
                    "pending_orders": warehouse.pending_orders,
                    "completed_orders": warehouse.completed_orders,
                    "name": warehouse.name,
                    "description": warehouse.notes or warehouse.address,
                    "id": warehouse.id,
                }
            )

        return warehouse_stats


class CuttingOrderListView(LoginRequiredMixin, ListView):
    """قائمة أوامر التقطيع"""

    model = CuttingOrder
    template_name = "cutting/order_list.html"
    context_object_name = "cutting_orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = CuttingOrder.objects.select_related(
            "order", "order__customer", "warehouse", "assigned_to"
        ).prefetch_related("items").defer(
            "rejection_reason", "notes", "notifications_sent"
        )

        # الحصول على المستودعات المتاحة للمستخدم أولاً
        user_warehouses = self.get_user_warehouses()

        # فلترة حسب المستودع - التحقق من GET parameters أولاً ثم من URL
        # GET parameters لها أولوية أعلى لأنها تأتي من اختيار المستخدم المباشر
        warehouse_id = self.request.GET.get("warehouse") or self.kwargs.get(
            "warehouse_id"
        )

        if warehouse_id:
            # التحقق من أن المستودع المطلوب ضمن المستودعات المتاحة للمستخدم
            if user_warehouses.filter(id=warehouse_id).exists():
                queryset = queryset.filter(warehouse_id=warehouse_id)
            else:
                # المستخدم ليس لديه صلاحية لهذا المستودع - عرض مستودعاته فقط
                queryset = queryset.filter(warehouse__in=user_warehouses)
        else:
            # عرض جميع المستودعات المتاحة للمستخدم
            queryset = queryset.filter(warehouse__in=user_warehouses)

        # البحث المحسّن - البحث برقم الفاتورة كخيار رئيسي (يشمل جميع أرقام الفواتير والعقود)
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(order__invoice_number__icontains=search)  # بحث برقم الفاتورة الأساسي
                | Q(order__invoice_number_2__icontains=search)  # رقم الفاتورة الإضافي 2
                | Q(order__invoice_number_3__icontains=search)  # رقم الفاتورة الإضافي 3
                | Q(cutting_code__icontains=search)
                | Q(order__contract_number__icontains=search)
                | Q(order__contract_number_2__icontains=search)  # رقم العقد الإضافي 2
                | Q(order__contract_number_3__icontains=search)  # رقم العقد الإضافي 3
                | Q(order__customer__name__icontains=search)
                | Q(order__customer__phone__icontains=search)
                | Q(order__order_number__icontains=search)  # إضافة البحث برقم الطلب
            )

        # فلترة حسب الحالة
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # فلتر إضافي حسب تاريخ الإنشاء
        date_filter = self.request.GET.get("date_filter")
        if date_filter:
            today = timezone.now().date()
            if date_filter == "today":
                queryset = queryset.filter(created_at__date=today)
            elif date_filter == "yesterday":
                yesterday = today - timezone.timedelta(days=1)
                queryset = queryset.filter(created_at__date=yesterday)
            elif date_filter == "this_week":
                week_start = today - timezone.timedelta(days=today.weekday())
                queryset = queryset.filter(created_at__date__gte=week_start)
            elif date_filter == "this_month":
                queryset = queryset.filter(
                    created_at__year=today.year, created_at__month=today.month
                )

        # فلتر حسب نوع الطلب (تسليم المصنع/تسليم الفرع)
        order_type = self.request.GET.get("order_type")
        if order_type:
            if order_type == "factory":
                queryset = queryset.filter(
                    Q(order__selected_types__icontains="installation")
                    | Q(order__selected_types__icontains="tailoring")
                )
            elif order_type == "branch":
                queryset = queryset.filter(
                    Q(order__selected_types__icontains="products")
                    | Q(order__selected_types__icontains="accessory")
                )

        # فلتر حسب الحاجة للإصلاح (جديد)
        needs_fix = self.request.GET.get("needs_fix")
        if needs_fix == "true":
            queryset = queryset.filter(needs_fix=True)

        return queryset.order_by("-created_at")

    def get_user_warehouses(self):
        """الحصول على المستودعات المتاحة للمستخدم - يدعم مستودعات متعددة"""
        user = self.request.user
        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)
        # موظف مستودع: الوصول للمستودعات المخصصة له (متعددة)
        elif hasattr(user, "is_warehouse_staff") and user.is_warehouse_staff:
            warehouses = user.get_all_assigned_warehouses()
            if warehouses.exists():
                return warehouses
            else:
                return Warehouse.objects.none()
        return Warehouse.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # الحصول على المستودع الحالي من GET parameters أولاً ثم من URL
        current_warehouse = self.request.GET.get("warehouse") or self.kwargs.get(
            "warehouse_id", ""
        )

        # حساب الإحصائيات - يجب أن تكون من queryset أساسي بدون فلاتر الحالة
        # للحصول على إحصائيات صحيحة لجميع الحالات
        base_queryset = CuttingOrder.objects.select_related(
            "order", "order__customer", "warehouse", "assigned_to"
        )

        # تطبيق فلتر المستودع والمستخدم فقط على الإحصائيات
        user_warehouses = self.get_user_warehouses()
        warehouse_id = self.request.GET.get("warehouse") or self.kwargs.get(
            "warehouse_id"
        )

        if warehouse_id and user_warehouses.filter(id=warehouse_id).exists():
            base_queryset = base_queryset.filter(warehouse_id=warehouse_id)
        else:
            base_queryset = base_queryset.filter(warehouse__in=user_warehouses)

        # تطبيق فلاتر البحث والتاريخ ونوع الطلب على الإحصائيات (لكن ليس فلتر الحالة)
        search = self.request.GET.get("search")
        if search:
            base_queryset = base_queryset.filter(
                Q(order__invoice_number__icontains=search)
                | Q(order__invoice_number_2__icontains=search)
                | Q(order__invoice_number_3__icontains=search)
                | Q(cutting_code__icontains=search)
                | Q(order__contract_number__icontains=search)
                | Q(order__contract_number_2__icontains=search)
                | Q(order__contract_number_3__icontains=search)
                | Q(order__customer__name__icontains=search)
                | Q(order__customer__phone__icontains=search)
                | Q(order__order_number__icontains=search)
            )

        date_filter = self.request.GET.get("date_filter")
        if date_filter:
            today = timezone.now().date()
            if date_filter == "today":
                base_queryset = base_queryset.filter(created_at__date=today)
            elif date_filter == "yesterday":
                yesterday = today - timezone.timedelta(days=1)
                base_queryset = base_queryset.filter(created_at__date=yesterday)
            elif date_filter == "this_week":
                week_start = today - timezone.timedelta(days=today.weekday())
                base_queryset = base_queryset.filter(created_at__date__gte=week_start)
            elif date_filter == "this_month":
                base_queryset = base_queryset.filter(
                    created_at__year=today.year, created_at__month=today.month
                )

        order_type = self.request.GET.get("order_type")
        if order_type:
            if order_type == "factory":
                base_queryset = base_queryset.filter(
                    Q(order__selected_types__icontains="installation")
                    | Q(order__selected_types__icontains="tailoring")
                )
            elif order_type == "branch":
                base_queryset = base_queryset.filter(
                    Q(order__selected_types__icontains="products")
                    | Q(order__selected_types__icontains="accessory")
                )

        # الآن احسب الإحصائيات بشكل صحيح - الحالات الموجودة فعلياً: pending, in_progress, completed, rejected
        pending_count = base_queryset.filter(status="pending").count()
        in_progress_count = base_queryset.filter(status="in_progress").count()
        completed_count = base_queryset.filter(status="completed").count()
        rejected_count = base_queryset.filter(status="rejected").count()

        context.update(
            {
                "warehouses": self.get_user_warehouses(),
                "current_warehouse": current_warehouse,
                "status_choices": CuttingOrder.STATUS_CHOICES,
                "search_query": self.request.GET.get("search", ""),
                "current_status": self.request.GET.get("status", ""),
                "current_date_filter": self.request.GET.get("date_filter", ""),
                "current_order_type": self.request.GET.get("order_type", ""),
                "current_needs_fix": self.request.GET.get("needs_fix", ""),
                "pending_count": pending_count,
                "in_progress_count": in_progress_count,
                "completed_count": completed_count,
                "rejected_count": rejected_count,
            }
        )
        return context


class CompletedCuttingOrdersView(LoginRequiredMixin, ListView):
    """قائمة أوامر التقطيع المجمعة - مع فلترة حسب الحالة"""

    model = CuttingOrder
    template_name = "cutting/completed_orders.html"
    context_object_name = "cutting_orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = CuttingOrder.objects.select_related(
            "order", "order__customer", "warehouse", "assigned_to"
        ).prefetch_related("items")

        # الحصول على المستودعات المتاحة للمستخدم أولاً
        user_warehouses = self.get_user_warehouses()

        # فلترة حسب المستودع إذا تم تحديده
        warehouse_id = self.request.GET.get("warehouse")
        if warehouse_id:
            # التحقق من أن المستودع المطلوب ضمن المستودعات المتاحة للمستخدم
            if user_warehouses.filter(id=warehouse_id).exists():
                queryset = queryset.filter(warehouse_id=warehouse_id)
            else:
                # المستخدم ليس لديه صلاحية لهذا المستودع - عرض مستودعاته فقط
                queryset = queryset.filter(warehouse__in=user_warehouses)
        else:
            # عرض جميع المستودعات المتاحة للمستخدم
            queryset = queryset.filter(warehouse__in=user_warehouses)

        # فلترة حسب الحالة
        status_filter = self.request.GET.get("status_filter")
        if status_filter == "completed":
            queryset = queryset.filter(status="completed")
        elif status_filter == "incomplete":
            queryset = queryset.exclude(status="completed")
        elif status_filter == "partially_completed":
            # الطلبات التي لديها بعض العناصر المكتملة وليست مكتملة بالكامل
            queryset = (
                queryset.filter(items__status="completed")
                .exclude(status="completed")
                .distinct()
            )

        # البحث المحسّن - البحث برقم الفاتورة كخيار رئيسي (يشمل جميع أرقام الفواتير والعقود)
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(order__invoice_number__icontains=search)  # بحث برقم الفاتورة الأساسي
                | Q(order__invoice_number_2__icontains=search)  # رقم الفاتورة الإضافي 2
                | Q(order__invoice_number_3__icontains=search)  # رقم الفاتورة الإضافي 3
                | Q(cutting_code__icontains=search)
                | Q(order__contract_number__icontains=search)
                | Q(order__contract_number_2__icontains=search)  # رقم العقد الإضافي 2
                | Q(order__contract_number_3__icontains=search)  # رقم العقد الإضافي 3
                | Q(order__customer__name__icontains=search)
                | Q(order__customer__phone__icontains=search)
                | Q(order__order_number__icontains=search)  # إضافة البحث برقم الطلب
            )

        return queryset.order_by("-created_at")

    def get_user_warehouses(self):
        """الحصول على المستودعات المتاحة للمستخدم - يدعم مستودعات متعددة"""
        user = self.request.user
        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)
        # موظف مستودع: الوصول للمستودعات المخصصة له (متعددة)
        elif hasattr(user, "is_warehouse_staff") and user.is_warehouse_staff:
            warehouses = user.get_all_assigned_warehouses()
            if warehouses.exists():
                return warehouses
            else:
                return Warehouse.objects.none()
        return Warehouse.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "warehouses": self.get_user_warehouses(),
                "selected_warehouse": self.request.GET.get("warehouse", ""),
                "status_filter": self.request.GET.get("status_filter", ""),
                "search_query": self.request.GET.get("search", ""),
            }
        )
        return context


class CuttingOrderDetailView(LoginRequiredMixin, DetailView):
    """تفاصيل أمر التقطيع"""

    model = CuttingOrder
    template_name = "cutting/order_detail.html"
    context_object_name = "cutting_order"

    def get_queryset(self):
        return CuttingOrder.objects.select_related(
            "order", "order__customer", "warehouse", "assigned_to"
        ).prefetch_related("items__order_item__product", "items__updated_by")


@login_required
def cutting_order_detail_by_code(request, cutting_code):
    """عرض تفاصيل أمر التقطيع بالكود"""
    cutting_order = get_object_or_404(
        CuttingOrder.objects.select_related(
            "order", "order__customer", "warehouse", "assigned_to"
        ).prefetch_related("items__order_item__product", "items__updated_by"),
        cutting_code=cutting_code,
    )

    return render(
        request, "cutting/order_detail.html", {"cutting_order": cutting_order}
    )


@login_required
def update_cutting_item(request, pk):
    """تحديث عنصر التقطيع"""
    item = get_object_or_404(CuttingOrderItem, pk=pk)

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            # التحقق من إعادة التعيين إلى حالة الانتظار
            requested_status = data.get("status", "")
            if requested_status == "pending" and item.status == "rejected":
                # استخدام دالة النموذج لإعادة التعيين
                item.reset_to_pending(request.user)
                return JsonResponse(
                    {
                        "success": True,
                        "message": "تم إعادة تعيين العنصر إلى حالة الانتظار",
                        "status": item.get_status_display(),
                    }
                )

            # تحديث البيانات العادية
            item.cutter_name = data.get("cutter_name", "")
            item.permit_number = data.get("permit_number", "")
            item.receiver_name = data.get("receiver_name", "")
            item.bag_number = data.get("bag_number", "")
            item.additional_quantity = float(data.get("additional_quantity", 0))
            item.notes = data.get("notes", "")
            item.updated_by = request.user

            # تحديث الحالة إذا تم ملء البيانات الأساسية
            if item.cutter_name and item.permit_number and item.receiver_name:
                item.status = "completed"
                item.cutting_date = timezone.now()
                item.delivery_date = timezone.now()

            item.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": "تم تحديث العنصر بنجاح",
                    "status": item.get_status_display(),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


@login_required
def complete_cutting_item(request, pk):
    """إكمال عنصر التقطيع"""
    from datetime import date, datetime

    item = get_object_or_404(CuttingOrderItem, pk=pk)

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            cutter_name = data.get("cutter_name")
            permit_number = data.get("permit_number")
            receiver_name = data.get("receiver_name")
            notes = data.get("notes", "")
            exit_date_str = data.get("exit_date")  # تاريخ الخروج
            backdate_reason = data.get("backdate_reason", "")  # سبب التسجيل بتاريخ سابق

            if not all([cutter_name, permit_number, receiver_name]):
                return JsonResponse(
                    {"success": False, "message": "يجب ملء جميع البيانات المطلوبة"}
                )

            # معالجة تاريخ الخروج
            exit_date = None
            if exit_date_str:
                try:
                    exit_date = datetime.strptime(exit_date_str, "%Y-%m-%d").date()
                    # التحقق من أن التاريخ ليس في المستقبل
                    if exit_date > date.today():
                        return JsonResponse(
                            {
                                "success": False,
                                "message": "لا يمكن اختيار تاريخ في المستقبل",
                            }
                        )
                    # إذا كان التاريخ سابق، يجب إدخال السبب
                    if exit_date < date.today() and not backdate_reason:
                        return JsonResponse(
                            {
                                "success": False,
                                "message": "يجب إدخال سبب التسجيل بتاريخ سابق",
                            }
                        )
                except ValueError:
                    return JsonResponse(
                        {"success": False, "message": "تنسيق تاريخ غير صحيح"}
                    )

            item.mark_as_completed(
                cutter_name=cutter_name,
                permit_number=permit_number,
                receiver_name=receiver_name,
                user=request.user,
                notes=notes,
                exit_date=exit_date,
                backdate_reason=backdate_reason,
            )

            return JsonResponse({"success": True, "message": "تم إكمال العنصر بنجاح"})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


@login_required
def reject_cutting_item(request, pk):
    """رفض عنصر التقطيع"""
    item = get_object_or_404(CuttingOrderItem, pk=pk)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            reason = data.get("reason")

            if not reason:
                return JsonResponse(
                    {"success": False, "message": "يجب كتابة سبب الرفض"}
                )

            item.mark_as_rejected(reason=reason, user=request.user)

            return JsonResponse({"success": True, "message": "تم رفض العنصر"})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


@login_required
def bulk_update_items(request, order_id):
    """تحديث مجمع لعناصر أمر التقطيع"""
    cutting_order = get_object_or_404(CuttingOrder, pk=order_id)

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            cutter_name = data.get("cutter_name")
            permit_number = data.get("permit_number")
            receiver_name = data.get("receiver_name")
            bag_number = data.get("bag_number", "")

            if not all([cutter_name, permit_number, receiver_name]):
                return JsonResponse(
                    {"success": False, "message": "يجب ملء جميع البيانات المطلوبة"}
                )

            # تحديث جميع العناصر المعلقة - مع تعيين الحالة كمكتملة
            updated_count = 0
            for item in cutting_order.items.filter(status="pending"):
                item.cutter_name = cutter_name
                item.permit_number = permit_number
                item.receiver_name = receiver_name
                item.bag_number = bag_number
                item.status = "completed"
                item.cutting_date = timezone.now()
                item.delivery_date = timezone.now()
                item.exit_date = timezone.now().date()
                item.updated_by = request.user
                item.save()
                updated_count += 1

            return JsonResponse(
                {"success": True, "message": f"تم إكمال {updated_count} عنصر بنجاح"}
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


@login_required
def bulk_complete_items(request, order_id):
    """إكمال مجمع لعناصر أمر التقطيع المختارة"""
    from datetime import date, datetime

    cutting_order = get_object_or_404(CuttingOrder, pk=order_id)

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            cutter_name = data.get("cutter_name")
            permit_number = data.get("permit_number")
            receiver_name = data.get("receiver_name")
            item_ids = data.get("item_ids", [])  # IDs العناصر المختارة
            exit_date_str = data.get("exit_date")  # تاريخ الخروج
            backdate_reason = data.get("backdate_reason", "")  # سبب التسجيل بتاريخ سابق

            if not all([cutter_name, permit_number, receiver_name]):
                return JsonResponse(
                    {"success": False, "message": "يجب ملء جميع البيانات المطلوبة"}
                )

            if not item_ids:
                return JsonResponse(
                    {"success": False, "message": "يجب اختيار عنصر واحد على الأقل"}
                )

            # معالجة تاريخ الخروج
            exit_date = None
            if exit_date_str:
                try:
                    exit_date = datetime.strptime(exit_date_str, "%Y-%m-%d").date()
                    if exit_date > date.today():
                        return JsonResponse(
                            {
                                "success": False,
                                "message": "لا يمكن اختيار تاريخ في المستقبل",
                            }
                        )
                    if exit_date < date.today() and not backdate_reason:
                        return JsonResponse(
                            {
                                "success": False,
                                "message": "يجب إدخال سبب التسجيل بتاريخ سابق",
                            }
                        )
                except ValueError:
                    return JsonResponse(
                        {"success": False, "message": "تنسيق تاريخ غير صحيح"}
                    )

            # التحقق من أن جميع العناصر المختارة معلقة
            items_to_complete = cutting_order.items.filter(id__in=item_ids)
            completed_items = items_to_complete.filter(status="completed")

            if completed_items.exists():
                completed_names = ", ".join(
                    [item.order_item.product.name[:30] for item in completed_items[:3]]
                )
                return JsonResponse(
                    {
                        "success": False,
                        "message": f'بعض العناصر المختارة مكتملة بالفعل: {completed_names}{"..." if completed_items.count() > 3 else ""}',
                    }
                )

            # إكمال العناصر المختارة المعلقة
            completed_count = 0
            for item in items_to_complete.filter(status="pending"):
                item.mark_as_completed(
                    cutter_name=cutter_name,
                    permit_number=permit_number,
                    receiver_name=receiver_name,
                    user=request.user,
                    exit_date=exit_date,
                    backdate_reason=backdate_reason,
                )
                completed_count += 1

            return JsonResponse(
                {
                    "success": True,
                    "message": f"تم إكمال {completed_count} عنصر بنجاح",
                    "completed_count": completed_count,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


class CuttingReportsView(LoginRequiredMixin, TemplateView):
    """صفحة التقارير"""

    template_name = "cutting/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_warehouses = self.get_user_warehouses()

        context.update(
            {
                "warehouses": user_warehouses,
                "report_types": CuttingReport.REPORT_TYPE_CHOICES,
                "recent_reports": CuttingReport.objects.filter(
                    warehouse__in=user_warehouses
                ).order_by("-generated_at")[:10],
            }
        )

        return context

    def get_user_warehouses(self):
        """الحصول على المستودعات المتاحة للمستخدم - يدعم مستودعات متعددة"""
        user = self.request.user
        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)
        # موظف مستودع: الوصول للمستودعات المخصصة له (متعددة)
        elif hasattr(user, "is_warehouse_staff") and user.is_warehouse_staff:
            warehouses = user.get_all_assigned_warehouses()
            if warehouses.exists():
                return warehouses
            else:
                return Warehouse.objects.none()
        return Warehouse.objects.filter(is_active=True)


@login_required
def generate_cutting_report(request):
    """إنشاء تقرير تقطيع"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            warehouse_id = data.get("warehouse_id")
            report_type = data.get("report_type")
            start_date = datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
            end_date = datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()

            # التحقق من صلاحية المستخدم للوصول للمستودع
            if not user_has_warehouse_access(request.user, warehouse_id):
                return JsonResponse(
                    {
                        "success": False,
                        "message": "ليس لديك صلاحية للوصول لهذا المستودع",
                    }
                )

            warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

            # حساب الإحصائيات
            cutting_orders = CuttingOrder.objects.filter(
                warehouse=warehouse, created_at__date__range=[start_date, end_date]
            )

            cutting_items = CuttingOrderItem.objects.filter(
                cutting_order__warehouse=warehouse,
                cutting_order__created_at__date__range=[start_date, end_date],
            )

            # إنشاء التقرير
            report = CuttingReport.objects.create(
                report_type=report_type,
                warehouse=warehouse,
                start_date=start_date,
                end_date=end_date,
                total_orders=cutting_orders.count(),
                completed_items=cutting_items.filter(status="completed").count(),
                rejected_items=cutting_items.filter(status="rejected").count(),
                pending_items=cutting_items.filter(status="pending").count(),
                generated_by=request.user,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "تم إنشاء التقرير بنجاح",
                    "report_id": report.id,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


@login_required
def daily_cutting_report(request, warehouse_id):
    """تقرير يومي للتقطيع"""
    # التحقق من صلاحية المستخدم للوصول للمستودع
    if not user_has_warehouse_access(request.user, warehouse_id):
        messages.error(request, "ليس لديك صلاحية للوصول لهذا المستودع")
        return redirect("cutting:dashboard")

    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    date = request.GET.get("date", timezone.now().date())

    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d").date()

    # الحصول على عناصر التقطيع لليوم المحدد
    cutting_items = (
        CuttingOrderItem.objects.filter(
            cutting_order__warehouse=warehouse,
            cutting_date__date=date,
            status="completed",
        )
        .select_related("cutting_order__order__customer", "order_item__product")
        .order_by("receiver_name", "cutting_date")
    )

    # تجميع حسب المستلم
    receivers_data = {}
    for item in cutting_items:
        receiver = item.receiver_name
        if receiver not in receivers_data:
            receivers_data[receiver] = []
        receivers_data[receiver].append(item)

    context = {
        "warehouse": warehouse,
        "date": date,
        "receivers_data": receivers_data,
        "total_items": cutting_items.count(),
    }

    return render(request, "cutting/daily_report.html", context)


@login_required
def print_daily_delivery_report(request, date, receiver):
    """طباعة تقرير التسليم اليومي لمستلم محدد"""
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

    # الحصول على جميع العناصر المسلمة لهذا المستلم في هذا التاريخ
    cutting_items = (
        CuttingOrderItem.objects.filter(
            receiver_name=receiver, delivery_date__date=date_obj, status="completed"
        )
        .select_related(
            "cutting_order__order__customer",
            "order_item__product",
            "cutting_order__warehouse",
        )
        .order_by("cutting_order__order__customer__name", "delivery_date")
    )

    context = {
        "receiver": receiver,
        "date": date_obj,
        "cutting_items": cutting_items,
        "total_items": cutting_items.count(),
    }

    return render(request, "cutting/print_daily_delivery.html", context)


@login_required
def warehouse_cutting_stats(request, warehouse_id):
    """إحصائيات المستودع API"""
    # التحقق من صلاحية المستخدم للوصول للمستودع
    if not user_has_warehouse_access(request.user, warehouse_id):
        return JsonResponse(
            {"success": False, "message": "ليس لديك صلاحية للوصول لهذا المستودع"},
            status=403,
        )

    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

    # إحصائيات أوامر التقطيع
    orders_stats = CuttingOrder.objects.filter(warehouse=warehouse).aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        completed=Count("id", filter=Q(status="completed")),
        partially_completed=Count("id", filter=Q(status="partially_completed")),
    )

    # إحصائيات العناصر
    items_stats = CuttingOrderItem.objects.filter(
        cutting_order__warehouse=warehouse
    ).aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        completed=Count("id", filter=Q(status="completed")),
        rejected=Count("id", filter=Q(status="rejected")),
    )

    return JsonResponse(
        {"warehouse_name": warehouse.name, "orders": orders_stats, "items": items_stats}
    )


@login_required
def get_item_status(request, item_id):
    """الحصول على حالة عنصر التقطيع API"""
    item = get_object_or_404(CuttingOrderItem, pk=item_id)

    return JsonResponse(
        {
            "status": item.status,
            "status_display": item.get_status_display(),
            "cutter_name": item.cutter_name,
            "permit_number": item.permit_number,
            "receiver_name": item.receiver_name,
            "cutting_date": (
                item.cutting_date.isoformat() if item.cutting_date else None
            ),
            "delivery_date": (
                item.delivery_date.isoformat() if item.delivery_date else None
            ),
            "notes": item.notes,
            "rejection_reason": item.rejection_reason,
        }
    )


class CuttingReceiptView(LoginRequiredMixin, ListView):
    """صفحة استلام أوامر التقطيع الجاهزة للاستلام"""

    template_name = "cutting/cutting_receipt.html"
    context_object_name = "cutting_orders"
    paginate_by = 20

    def get_user_warehouses(self):
        """الحصول على المستودعات المتاحة للمستخدم - يدعم مستودعات متعددة"""
        user = self.request.user
        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)
        # موظف مستودع: الوصول للمستودعات المخصصة له (متعددة)
        elif hasattr(user, "is_warehouse_staff") and user.is_warehouse_staff:
            warehouses = user.get_all_assigned_warehouses()
            if warehouses.exists():
                return warehouses
            else:
                return Warehouse.objects.none()
        return Warehouse.objects.filter(is_active=True)

    def get_queryset(self):
        """الحصول على أوامر التقطيع الجاهزة للاستلام"""
        from django.db.models import Q

        # الحصول على المستودعات المتاحة للمستخدم
        user_warehouses = self.get_user_warehouses()

        queryset = (
            CuttingOrder.objects.select_related("order", "order__customer", "warehouse")
            .prefetch_related("items")
            .filter(
                # فلترة حسب مستودعات المستخدم
                warehouse__in=user_warehouses
            )
            .filter(
                # أوامر التقطيع التي تحتوي على عناصر جاهزة للاستلام
                # (مكتملة أو لديها بيانات إكمال حتى لو الحالة لم تتغير)
                Q(items__status="completed")
                | Q(
                    items__receiver_name__isnull=False,
                    items__permit_number__isnull=False,
                    items__cutting_date__isnull=False,
                ),
                items__receiver_name__isnull=False,
                items__permit_number__isnull=False,
                # التأكد من عدم استلامها في المصنع بعد
                items__fabric_received=False,
            )
            .exclude(items__receiver_name="")
            .exclude(items__permit_number="")
            .filter(
                # تضمين جميع أنواع الطلبات: تركيب، تسليم، إكسسوار، تصنيع
                Q(order__selected_types__icontains="installation")
                | Q(order__selected_types__icontains="tailoring")
                | Q(order__selected_types__icontains="accessory")
                | Q(order__selected_types__icontains="manufacturing")
            )
            .distinct()
            .order_by("-created_at")
        )

        # فلتر المستودع إذا تم تحديده
        warehouse_id = self.request.GET.get("warehouse")
        if warehouse_id:
            if user_warehouses.filter(id=warehouse_id).exists():
                queryset = queryset.filter(warehouse_id=warehouse_id)

        # البحث المحسّن - البحث برقم الفاتورة كخيار رئيسي (يشمل جميع أرقام الفواتير والعقود)
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(order__invoice_number__icontains=search)  # بحث برقم الفاتورة الأساسي
                | Q(order__invoice_number_2__icontains=search)  # رقم الفاتورة الإضافي 2
                | Q(order__invoice_number_3__icontains=search)  # رقم الفاتورة الإضافي 3
                | Q(cutting_code__icontains=search)
                | Q(order__contract_number__icontains=search)
                | Q(order__contract_number_2__icontains=search)  # رقم العقد الإضافي 2
                | Q(order__contract_number_3__icontains=search)  # رقم العقد الإضافي 3
                | Q(order__customer__name__icontains=search)
                | Q(order__customer__phone__icontains=search)
                | Q(order__order_number__icontains=search)  # إضافة البحث برقم الطلب
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات
        total_available_orders = self.get_queryset().count()
        context["total_available_orders"] = total_available_orders

        # معلومات الصفحات
        paginator = context.get("paginator")
        if paginator:
            context["total_pages"] = paginator.num_pages
            context["current_page"] = context["page_obj"].number

        return context


@login_required
def receive_cutting_order_ajax(request, cutting_order_id):
    """استلام أمر تقطيع عبر AJAX"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})

    try:
        cutting_order = get_object_or_404(CuttingOrder, pk=cutting_order_id)

        # التحقق من وجود عناصر جاهزة للاستلام
        ready_items = cutting_order.items.filter(
            status="completed",
            receiver_name__isnull=False,
            permit_number__isnull=False,
            fabric_received=False,
        )

        if not ready_items.exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": "لا توجد عناصر جاهزة للاستلام في هذا الأمر",
                }
            )

        data = json.loads(request.body)
        bag_number = data.get("bag_number", "")
        received_by_name = data.get("received_by_name", "")
        notes = data.get("notes", "")

        if not received_by_name:
            return JsonResponse({"success": False, "message": "يجب إدخال اسم المستلم"})

        # إنشاء استلام الأقمشة
        fabric_receipt = FabricReceipt.objects.create(
            order=cutting_order.order,
            cutting_order=cutting_order,
            receipt_type="cutting_order",
            permit_number=ready_items.first().permit_number,
            bag_number=bag_number,
            received_by_name=received_by_name,
            received_by=request.user,
            notes=notes,
        )

        # إنشاء عناصر الاستلام وتحديث حالة العناصر
        items_count = 0
        for item in ready_items:
            FabricReceiptItem.objects.create(
                fabric_receipt=fabric_receipt,
                cutting_item=item,
                order_item=item.order_item,
                quantity_received=item.order_item.quantity + item.additional_quantity,
                item_notes=item.notes or "",
            )

            # تحديث حالة عنصر التقطيع
            item.fabric_received = True
            item.bag_number = bag_number
            item.save(update_fields=["fabric_received", "bag_number"])

            # مزامنة حالة الاستلام مع عنصر التصنيع المرتبط
            try:
                from manufacturing.models import ManufacturingOrderItem
                mfg_item = ManufacturingOrderItem.objects.filter(
                    cutting_item=item, fabric_received=False
                ).first()
                if mfg_item:
                    from django.utils import timezone as tz
                    mfg_item.fabric_received = True
                    mfg_item.bag_number = bag_number
                    mfg_item.fabric_received_date = tz.now()
                    mfg_item.fabric_received_by = request.user
                    mfg_item.save(update_fields=[
                        "fabric_received", "bag_number",
                        "fabric_received_date", "fabric_received_by"
                    ])
            except Exception:
                pass  # لا نوقف العملية إذا فشل التزامن

            items_count += 1

        return JsonResponse(
            {
                "success": True,
                "message": f"تم استلام {items_count} عنصر بنجاح",
                "receipt_id": fabric_receipt.id,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})


@login_required
def cutting_notifications_api(request):
    """API للإشعارات المتعلقة بالتقطيع"""
    try:
        from notifications.models import Notification

        notifications = Notification.objects.filter(
            user=request.user,
            notification_type__in=["cutting_completed", "stock_shortage"],
            is_read=False,
        ).order_by("-created_at")[:10]

        notifications_data = []
        for notification in notifications:
            notifications_data.append(
                {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.notification_type,
                    "created_at": notification.created_at.isoformat(),
                }
            )

        return JsonResponse({"success": True, "notifications": notifications_data})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})


class WarehouseSettingsView(LoginRequiredMixin, TemplateView):
    """إعدادات المستودعات"""

    template_name = "cutting/warehouse_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["warehouses"] = Warehouse.objects.filter(is_active=True)
        return context


class UserPermissionsView(LoginRequiredMixin, TemplateView):
    """إعدادات صلاحيات المستخدمين"""

    template_name = "cutting/user_permissions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "users": User.objects.filter(is_active=True),
                "warehouses": Warehouse.objects.filter(is_active=True),
            }
        )
        return context


@login_required
def print_cutting_report(request, report_id):
    """طباعة تقرير التقطيع المفصل"""
    from django.db.models import Count, Q, Sum

    report = get_object_or_404(CuttingReport, pk=report_id)

    # الحصول على جميع أوامر التقطيع في الفترة المحددة
    cutting_orders = (
        CuttingOrder.objects.filter(
            warehouse=report.warehouse,
            created_at__date__range=[report.start_date, report.end_date],
        )
        .select_related("order", "order__customer", "warehouse", "assigned_to")
        .prefetch_related("items__order_item__product")
        .order_by("created_at")
    )

    # الحصول على جميع عناصر التقطيع في الفترة
    cutting_items = (
        CuttingOrderItem.objects.filter(
            cutting_order__warehouse=report.warehouse,
            cutting_order__created_at__date__range=[report.start_date, report.end_date],
        )
        .select_related("cutting_order__order__customer", "order_item__product")
        .order_by("cutting_order__created_at", "id")
    )

    # إحصائيات تفصيلية
    items_stats = cutting_items.aggregate(
        total_quantity=Sum("order_item__quantity"),
        completed_count=Count("id", filter=Q(status="completed")),
        rejected_count=Count("id", filter=Q(status="rejected")),
        pending_count=Count("id", filter=Q(status="pending")),
        completed_quantity=Sum("order_item__quantity", filter=Q(status="completed")),
        rejected_quantity=Sum("order_item__quantity", filter=Q(status="rejected")),
        pending_quantity=Sum("order_item__quantity", filter=Q(status="pending")),
    )

    # تجميع حسب المنتج
    products_summary = (
        cutting_items.values("order_item__product__name")
        .annotate(
            total_quantity=Sum("order_item__quantity"),
            completed_count=Count("id", filter=Q(status="completed")),
            rejected_count=Count("id", filter=Q(status="rejected")),
            pending_count=Count("id", filter=Q(status="pending")),
        )
        .order_by("-total_quantity")
    )

    # تجميع حسب العميل
    customers_summary = (
        cutting_orders.values(
            "order__customer__name", "order__contract_number", "order__invoice_number"
        )
        .annotate(
            total_items=Count("items"),
            completed_items=Count("items", filter=Q(items__status="completed")),
            total_quantity=Sum("items__order_item__quantity"),
        )
        .order_by("order__customer__name")
    )

    # تجميع حسب المستلم
    receivers_summary = (
        cutting_items.exclude(receiver_name__isnull=True)
        .exclude(receiver_name="")
        .values("receiver_name")
        .annotate(
            total_items=Count("id"),
            completed_items=Count("id", filter=Q(status="completed")),
            total_quantity=Sum("order_item__quantity"),
        )
        .order_by("-total_items")
    )

    context = {
        "report": report,
        "cutting_orders": cutting_orders,
        "cutting_items": cutting_items,
        "items_stats": items_stats,
        "products_summary": products_summary,
        "customers_summary": customers_summary,
        "receivers_summary": receivers_summary,
        "total_orders_count": cutting_orders.count(),
        "total_items_count": cutting_items.count(),
    }

    return render(request, "cutting/print_report.html", context)


@login_required
def create_cutting_order_from_order(request, order_id):
    """إنشاء أمر تقطيع من طلب موجود"""
    if request.method == "POST":
        try:
            order = get_object_or_404(Order, pk=order_id)

            # التحقق من عدم وجود أمر تقطيع مسبق
            if CuttingOrder.objects.filter(order=order).exists():
                return JsonResponse(
                    {"success": False, "message": "يوجد أمر تقطيع مسبق لهذا الطلب"}
                )

            # الحصول على أول مستودع متاح
            warehouse = Warehouse.objects.filter(is_active=True).first()

            if not warehouse:
                return JsonResponse(
                    {"success": False, "message": "لا يوجد مستودع متاح"}
                )

            # إنشاء أمر التقطيع
            cutting_order = CuttingOrder.objects.create(
                order=order,
                warehouse=warehouse,
                created_by=request.user,
                notes=f"أمر تقطيع يدوي للطلب {order.order_number}",
            )

            # إنشاء عناصر التقطيع من عناصر الطلب
            for order_item in order.items.all():
                CuttingOrderItem.objects.create(
                    cutting_order=cutting_order, order_item=order_item, status="pending"
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"تم إنشاء أمر التقطيع {cutting_order.cutting_code} بنجاح",
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


@login_required
def start_cutting_order(request, order_id):
    """بدء أمر التقطيع"""
    if request.method == "POST":
        try:
            cutting_order = get_object_or_404(CuttingOrder, pk=order_id)

            if cutting_order.status != "pending":
                return JsonResponse(
                    {
                        "success": False,
                        "message": "لا يمكن بدء هذا الأمر - الحالة الحالية: "
                        + cutting_order.get_status_display(),
                    }
                )

            # تحديث حالة الأمر
            old_status = cutting_order.status
            cutting_order.status = "in_progress"
            cutting_order.assigned_to = request.user
            cutting_order.save()

            # إنشاء سجل تغيير الحالة فقط لطلبات المنتجات
            try:
                from orders.models import OrderStatusLog

                if (
                    cutting_order.order
                    and "products" in cutting_order.order.get_selected_types_list()
                ):
                    OrderStatusLog.objects.create(
                        order=cutting_order.order,
                        old_status=old_status,
                        new_status="in_progress",
                        changed_by=request.user,
                        change_type="general",
                        notes=f"تم بدء أمر التقطيع #{cutting_order.cutting_code}",
                    )
            except Exception as e:
                logger.debug(f"خطأ في تسجيل تغيير حالة الطلب: {e}")
            return JsonResponse(
                {"success": True, "message": "تم بدء أمر التقطيع بنجاح"}
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})


@login_required
def quick_stats_api(request):
    """API للإحصائيات السريعة في صفحة التقارير"""
    try:
        # الحصول على تاريخ اليوم
        today = timezone.now().date()

        # الحصول على المستودعات المتاحة للمستخدم
        if request.user.is_superuser:
            warehouses = Warehouse.objects.filter(is_active=True)
        else:
            warehouses = Warehouse.objects.filter(is_active=True)

        # عمليات التقطيع اليوم (العناصر المكتملة اليوم)
        today_items = CuttingOrderItem.objects.filter(
            cutting_order__warehouse__in=warehouses, cutting_date__date=today
        )

        # إحصائيات العناصر
        completed_today = today_items.filter(status="completed").count()
        rejected_today = today_items.filter(status="rejected").count()

        # العناصر المعلقة (جميع الأوقات)
        pending_items = CuttingOrderItem.objects.filter(
            cutting_order__warehouse__in=warehouses, status="pending"
        ).count()

        # إجمالي عمليات التقطيع اليوم
        total_today = today_items.count()

        # حساب نسبة الإنجاز
        if total_today > 0:
            completion_rate = round((completed_today / total_today) * 100)
        else:
            completion_rate = 0

        return JsonResponse(
            {
                "success": True,
                "stats": {
                    "total_today": total_today,
                    "completed": completed_today,
                    "rejected": rejected_today,
                    "pending": pending_items,
                    "completion_rate": completion_rate,
                },
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})
