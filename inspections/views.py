from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from core.mixins import PaginationFixMixin

from .forms import (
    InspectionEvaluationForm,
    InspectionForm,
    InspectionNotificationForm,
    InspectionReportForm,
)
from .models import (
    Inspection,
    InspectionEvaluation,
    InspectionNotification,
    InspectionReport,
)


class CompletedInspectionsDetailView(PaginationFixMixin, LoginRequiredMixin, ListView):
    model = Inspection
    template_name = "inspections/completed_details.html"
    context_object_name = "inspections"
    paginate_by = 20
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def get_queryset(self):
        queryset = Inspection.objects.filter(status="completed")
        if not self.request.user.is_superuser and not self.request.user.has_perm(
            "inspections.view_inspection"
        ):
            queryset = queryset.filter(
                Q(inspector=self.request.user) | Q(created_by=self.request.user)
            )

        # تم إلغاء الفلترة الافتراضية

        return queryset.select_related("customer", "inspector", "branch")


class CancelledInspectionsDetailView(PaginationFixMixin, LoginRequiredMixin, ListView):
    model = Inspection
    template_name = "inspections/cancelled_details.html"
    context_object_name = "inspections"
    paginate_by = 20
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def get_queryset(self):
        queryset = Inspection.objects.filter(status="cancelled")
        if not self.request.user.is_superuser and not self.request.user.has_perm(
            "inspections.view_inspection"
        ):
            queryset = queryset.filter(
                Q(inspector=self.request.user) | Q(created_by=self.request.user)
            )

        # تم إلغاء الفلترة الافتراضية

        return queryset.select_related("customer", "inspector", "branch")


class PendingInspectionsDetailView(PaginationFixMixin, LoginRequiredMixin, ListView):
    model = Inspection
    template_name = "inspections/pending_details.html"
    context_object_name = "inspections"
    paginate_by = 20
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def get_queryset(self):
        queryset = Inspection.objects.filter(status="pending")
        if not self.request.user.is_superuser and not self.request.user.has_perm(
            "inspections.view_inspection"
        ):
            queryset = queryset.filter(
                Q(inspector=self.request.user) | Q(created_by=self.request.user)
            )

        # تم إلغاء الفلترة الافتراضية

        return queryset.select_related("customer", "inspector", "branch")


class InspectionListView(PaginationFixMixin, LoginRequiredMixin, ListView):
    model = Inspection
    template_name = "inspections/inspection_list.html"
    context_object_name = "inspections"
    paginate_by = 25  # الافتراضي
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def get_paginate_by(self, queryset):
        try:
            page_size = int(self.request.GET.get("page_size", 25))
            if page_size > 100:
                page_size = 100
            elif page_size < 1:
                page_size = 25
            return page_size
        except Exception:
            return 25

    def get_queryset(self):
        from .forms import InspectionSearchForm

        form = InspectionSearchForm(self.request.GET)

        # Check if user has permission to view all inspections
        if self.request.user.is_superuser or self.request.user.has_perm(
            "inspections.view_inspection"
        ):
            queryset = Inspection.objects.all()
        else:
            queryset = Inspection.objects.filter(
                Q(inspector=self.request.user) | Q(created_by=self.request.user)
            )

        # تم إلغاء الفلترة الافتراضية
        if form.is_valid():
            q = form.cleaned_data.get("q")
            branch_id = form.cleaned_data.get("branch")
            status = form.cleaned_data.get("status")
            from_orders = form.cleaned_data.get("from_orders")
            is_duplicated = form.cleaned_data.get("is_duplicated")
            if branch_id:
                queryset = queryset.filter(order__customer__branch_id=branch_id)
            if status == "pending" and from_orders == "1":
                queryset = queryset.filter(status="pending", is_from_orders=True)
            elif status:
                queryset = queryset.filter(status=status)
            if is_duplicated == "1":
                queryset = queryset.filter(notes__contains="تكرار من المعاينة رقم:")
            # بحث شامل متعدد الحقول (يشمل جميع أرقام الفواتير والعقود)
            if q:
                queryset = queryset.filter(
                    Q(order__order_number__icontains=q)
                    | Q(order__customer__name__icontains=q)
                    | Q(order__customer__code__icontains=q)
                    | Q(order__customer__phone__icontains=q)
                    | Q(order__contract_number__icontains=q)
                    | Q(order__contract_number_2__icontains=q)
                    | Q(order__contract_number_3__icontains=q)
                    | Q(order__invoice_number__icontains=q)
                    | Q(order__invoice_number_2__icontains=q)
                    | Q(order__invoice_number_3__icontains=q)
                    | Q(order__id__icontains=q)
                    | Q(order__customer__phone2__icontains=q)
                    | Q(order__customer__email__icontains=q)
                    | Q(customer__name__icontains=q)
                    | Q(customer__code__icontains=q)
                    | Q(customer__phone__icontains=q)
                    | Q(customer__phone2__icontains=q)
                    | Q(customer__email__icontains=q)
                    | Q(notes__icontains=q)
                    | Q(inspector__username__icontains=q)
                    | Q(branch__name__icontains=q)
                    | Q(status__icontains=q)
                    | Q(request_date__icontains=q)
                    | Q(scheduled_date__icontains=q)
                    | Q(expected_delivery_date__icontains=q)
                )
        return queryset.select_related(
            "customer", "inspector", "branch", "order__customer__branch"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_size"] = self.get_paginate_by(self.get_queryset())
        from django.db.models import Q

        from accounts.models import Branch

        branch_id = self.request.GET.get("branch")
        status = self.request.GET.get("status")
        from_orders = self.request.GET.get("from_orders")
        is_duplicated = self.request.GET.get("is_duplicated")
        today = timezone.now().date()

        # بناء queryset للداشبورد بنفس منطق الفلترة
        if self.request.user.is_superuser or self.request.user.has_perm(
            "inspections.view_inspection"
        ):
            dashboard_qs = Inspection.objects.all()
        else:
            dashboard_qs = Inspection.objects.filter(
                Q(inspector=self.request.user) | Q(created_by=self.request.user)
            )
        if branch_id:
            dashboard_qs = dashboard_qs.filter(order__customer__branch_id=branch_id)
        if status == "pending" and from_orders == "1":
            dashboard_qs = dashboard_qs.filter(status="pending", is_from_orders=True)
        elif status:
            dashboard_qs = dashboard_qs.filter(status=status)
        if is_duplicated == "1":
            dashboard_qs = dashboard_qs.filter(notes__contains="تكرار من المعاينة رقم:")

        # إحصائيات الداشبورد بناءً على الفلترة
        context["dashboard"] = {
            "total_inspections": dashboard_qs.count(),
            "new_inspections": dashboard_qs.filter(status="pending").count(),
            "scheduled_inspections": dashboard_qs.filter(status="scheduled").count(),
            "successful_inspections": dashboard_qs.filter(status="completed").count(),
            "cancelled_inspections": dashboard_qs.filter(status="cancelled").count(),
            "postponed_by_customer_inspections": dashboard_qs.filter(
                status="postponed_by_customer"
            ).count(),
            "duplicated_inspections": dashboard_qs.filter(
                notes__contains="تكرار من المعاينة رقم:"
            ).count(),
        }
        context["branches"] = Branch.objects.all()
        return context


class InspectionCreateView(LoginRequiredMixin, CreateView):
    model = Inspection
    form_class = InspectionForm
    template_name = "inspections/inspection_form.html"
    success_url = reverse_lazy("inspections:inspection_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        # إضافة الطلب المرتبط إلى النموذج إذا كان موجوداً
        order_id = self.request.GET.get("order_id")
        customer_id = self.request.GET.get("customer_id")
        if order_id:
            from orders.models import Order

            try:
                kwargs["order"] = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                pass
        if customer_id:
            try:
                from customers.models import Customer

                # محاولة البحث بالـ ID أولاً (في حالة كان رقمي)
                if customer_id.isdigit():
                    kwargs["customer"] = Customer.objects.get(id=customer_id)
                else:
                    # البحث بكود العميل إذا لم يكن رقمي
                    kwargs["customer"] = Customer.objects.get(code=customer_id)
            except Exception:
                pass
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_id = self.request.GET.get("customer_id")
        if customer_id:
            try:
                from customers.models import Customer

                # محاولة البحث بالـ ID أولاً (في حالة كان رقمي)
                if customer_id.isdigit():
                    context["customer"] = Customer.objects.get(id=customer_id)
                else:
                    # البحث بكود العميل إذا لم يكن رقمي
                    context["customer"] = Customer.objects.get(code=customer_id)
            except Exception:
                pass
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if not form.instance.inspector:
            form.instance.inspector = self.request.user
        if not form.instance.branch and not self.request.user.is_superuser:
            form.instance.branch = self.request.user.branch

        # حفظ البائع من الطلب المرتبط
        order_id = self.request.GET.get("order_id")
        if order_id:
            from orders.models import Order

            try:
                order = Order.objects.get(id=order_id)
                form.instance.order = order
                form.instance.is_from_orders = True

                # تعيين البائع بشكل صريح من الطلب المرتبط
                if order.salesperson:
                    form.instance.responsible_employee = order.salesperson
                    # تأكد من حفظ المعاينة قبل عرضها

                # نسخ معلومات أخرى من الطلب
                if not form.instance.customer and order.customer:
                    form.instance.customer = order.customer
                if not form.instance.contract_number and order.contract_number:
                    form.instance.contract_number = order.contract_number

            except Order.DoesNotExist:
                pass

        # حفظ المعاينة بشكل سريع
        response = super().form_valid(form)

        # عرض رسالة نجاح فورية
        if form.instance.inspection_file:
            messages.success(
                self.request, "تم إنشاء المعاينة بنجاح وسيتم رفع الملف في الخلفية"
            )
        else:
            messages.success(self.request, "تم إنشاء المعاينة بنجاح")

        # للتأكد من حفظ معلومات البائع، نقوم بتحديثها مرة أخرى بعد الحفظ إذا كانت من طلب
        if (
            order_id
            and hasattr(form.instance, "order")
            and form.instance.order
            and form.instance.order.salesperson
        ):
            if not form.instance.responsible_employee:
                form.instance.responsible_employee = form.instance.order.salesperson
                form.instance.save(update_fields=["responsible_employee"])

        return response


class InspectionDetailView(LoginRequiredMixin, DetailView):
    model = Inspection
    template_name = "inspections/inspection_detail.html"
    context_object_name = "inspection"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("customer", "inspector", "branch", "created_by", "order")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inspection = self.get_object()

        # إضافة ملاحظات العميل إذا كان موجودًا
        if inspection.customer:
            from customers.models import CustomerNote

            context["customer_notes"] = CustomerNote.objects.filter(
                customer=inspection.customer
            ).order_by("-created_at")[:5]

        # تخزين ملاحظات الطلب في سياق الصفحة حتى إذا تم تحميلها بشكل غير متزامن
        if hasattr(inspection, "order") and inspection.order:
            context["order_notes"] = inspection.order.notes

        return context


class InspectionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Inspection
    form_class = InspectionForm
    template_name = "inspections/inspection_form.html"
    success_url = reverse_lazy("inspections:inspection_list")

    def test_func(self):
        inspection = self.get_object()
        user = self.request.user

        # السماح للمديرين والمستخدمين المخولين
        if (
            user.is_superuser
            or user.is_staff
            or user.has_perm("inspections.change_inspection")
        ):
            return True

        # السماح لمنشئ المعاينة أو المعاين المُعيَّن
        if inspection.created_by == user or inspection.inspector == user:
            return True

        # السماح لفنيي المعاينة
        if hasattr(user, "is_inspection_technician") and user.is_inspection_technician:
            return True

        # السماح لمديري الفروع
        if hasattr(user, "is_branch_manager") and user.is_branch_manager:
            return True

        return False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user

        # إضافة الطلب المرتبط إلى النموذج إذا كان موجوداً
        inspection = self.get_object()
        if hasattr(inspection, "order") and inspection.order:
            kwargs["order"] = inspection.order

        return kwargs

    def form_valid(self, form):
        inspection = form.instance
        old_inspection = self.get_object()
        old_status = old_inspection.status

        # Safely get the new status, falling back to the instance's status if not in form
        new_status = form.cleaned_data.get("status", inspection.status)

        # معالجة تحديث عنوان العميل
        update_customer_address = form.cleaned_data.get("update_customer_address")
        if update_customer_address and inspection.customer:
            try:
                old_address = inspection.customer.address
                inspection.customer.address = update_customer_address
                inspection.customer.save(update_fields=["address"])

                # إضافة ملاحظة في المعاينة عن تحديث العنوان
                address_note = f"\n--- تحديث العنوان ---\n"
                address_note += f"العنوان السابق: {old_address or 'غير محدد'}\n"
                address_note += f"العنوان الجديد: {update_customer_address}\n"
                address_note += f"تم التحديث بواسطة: {self.request.user.username}\n"
                address_note += (
                    f"تاريخ التحديث: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
                )
                address_note += f"--- نهاية تحديث العنوان ---\n"

                if inspection.notes:
                    inspection.notes += address_note
                else:
                    inspection.notes = address_note

                # تحديث عنوان التركيب في جدولة التركيب إذا كانت موجودة
                try:
                    from installations.models import InstallationSchedule

                    installation_schedules = InstallationSchedule.objects.filter(
                        order__customer=inspection.customer
                    )
                    for installation in installation_schedules:
                        if installation.location_address != update_customer_address:
                            installation.location_address = update_customer_address
                            installation.save(update_fields=["location_address"])
                except Exception as install_error:
                    print(f"خطأ في تحديث عنوان التركيب: {install_error}")

                messages.success(
                    self.request, "تم تحديث عنوان العميل بنجاح في المعاينات والتركيبات"
                )
            except Exception as e:
                messages.warning(self.request, f"تعذر تحديث عنوان العميل: {str(e)}")

        # Save inspection first to ensure it exists
        # تعيين المستخدم الذي قام بالتغيير للاستخدام في الإشعارات
        inspection._changed_by = self.request.user
        response = super().form_valid(form)

        # إنشاء سجل تغيير الحالة في OrderStatusLog إذا كان هناك طلب مرتبط
        if old_status != new_status and inspection.order:
            try:
                from inspections.models import Inspection
                from orders.models import OrderStatusLog

                # الحصول على أسماء الحالات
                status_dict = dict(Inspection.STATUS_CHOICES)
                old_status_display = status_dict.get(old_status, old_status)
                new_status_display = status_dict.get(new_status, new_status)

                OrderStatusLog.objects.create(
                    order=inspection.order,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=self.request.user,
                    change_type="inspection",
                    notes=f"تغيير حالة المعاينة من {old_status_display} إلى {new_status_display}",
                )
            except Exception as e:
                print(f"خطأ في تسجيل تغيير حالة المعاينة: {e}")

        # إنشاء إشعار لتحديث حالة المعاينة إذا تغيرت
        if old_status != new_status:
            try:
                from notifications.signals import create_notification

                # تحديد نوع الإشعار
                notification_type = "inspection_status_changed"

                # إنشاء عنوان ووصف الإشعار
                title = f"تحديث حالة المعاينة #{inspection.pk}"
                message = f'تم تغيير حالة المعاينة من "{old_status}" إلى "{new_status}" بواسطة {self.request.user.get_full_name() or self.request.user.username}'

                # إضافة معلومات الطلب إذا كان موجوداً
                order_info = ""
                if inspection.order:
                    order_info = f" - الطلب: {inspection.order.order_number}"
                    message += f" (الطلب: {inspection.order.order_number})"

                title += order_info

                # إنشاء الإشعار
                create_notification(
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    related_object=inspection,
                    created_by=self.request.user,
                    extra_data={
                        "old_status": old_status,
                        "new_status": new_status,
                        "changed_by": self.request.user.get_full_name()
                        or self.request.user.username,
                        "inspection_id": inspection.pk,
                        "order_number": (
                            inspection.order.order_number if inspection.order else None
                        ),
                        "customer_name": (
                            inspection.customer.name
                            if inspection.customer
                            else "غير محدد"
                        ),
                    },
                )
            except Exception as e:
                print(f"خطأ في إنشاء إشعار تحديث حالة المعاينة: {e}")

        # التحقق من وجود ملف جديد وإعطاء رسالة مناسبة
        old_file = old_inspection.inspection_file
        new_file = inspection.inspection_file
        if new_file and (not old_file or old_file != new_file):
            messages.success(
                self.request,
                "تم تحديث المعاينة بنجاح وسيتم رفع الملف الجديد في الخلفية",
            )
        else:
            # إضافة رسالة نجاح مبكرة لتحسين تجربة المستخدم
            messages.success(self.request, "تم تحديث المعاينة بنجاح")

        # Try to get order if it exists
        try:
            if inspection.order:
                if new_status == "completed":
                    inspection.order.tracking_status = "processing"
                elif new_status == "scheduled":
                    inspection.order.tracking_status = "processing"
                elif new_status == "cancelled":
                    inspection.order.tracking_status = "pending"
                else:  # pending
                    inspection.order.tracking_status = "pending"

                inspection.order.save()
                messages.success(self.request, "تم تحديث حالة الطلب المرتبط أيضاً")
                return redirect("orders:order_detail", inspection.order.pk)
        except AttributeError:
            # No order associated with this inspection
            pass

        # Handle completion status - let the model handle this via the tracker
        # We don't need to manually set completed_at here anymore
        if new_status == "completed" and old_status != "completed":
            if not hasattr(inspection, "evaluation"):
                return redirect(
                    "inspections:evaluation_create", inspection_pk=inspection.pk
                )
        return response


@login_required
def check_upload_status(request, pk):
    """التحقق من حالة رفع الملف إلى Google Drive"""
    try:
        inspection = get_object_or_404(Inspection, pk=pk)

        # إعادة تحميل البيانات من قاعدة البيانات للتأكد من الحالة الحديثة
        inspection.refresh_from_db()

        # التحقق من وجود الملف في Google Drive إذا لم تكن الحالة محدثة
        if not inspection.is_uploaded_to_drive and inspection.inspection_file:
            # محاولة العثور على الملف في Google Drive
            try:
                from inspections.services.google_drive_service import (
                    get_google_drive_service,
                )

                drive_service = get_google_drive_service()

                if drive_service:
                    # البحث عن الملف بالاسم
                    filename = (
                        inspection.google_drive_file_name
                        or inspection.generate_drive_filename()
                    )
                    files = (
                        drive_service.service.files()
                        .list(
                            q=f"name='{filename}' and trashed=false",
                            fields="files(id, name, webViewLink)",
                        )
                        .execute()
                    )

                    if files.get("files"):
                        # تم العثور على الملف - تحديث البيانات
                        file_info = files["files"][0]
                        inspection.google_drive_file_id = file_info["id"]
                        inspection.google_drive_file_url = file_info["webViewLink"]
                        inspection.is_uploaded_to_drive = True
                        inspection.google_drive_file_name = filename

                        # حفظ التحديثات
                        inspection.save(
                            update_fields=[
                                "google_drive_file_id",
                                "google_drive_file_url",
                                "is_uploaded_to_drive",
                                "google_drive_file_name",
                            ]
                        )

                        # print(f"تم تحديث حالة المعاينة {pk} - الملف موجود في Google Drive")  # معطل لتجنب الرسائل الكثيرة

            except Exception as drive_error:
                print(f"خطأ في التحقق من Google Drive: {str(drive_error)}")

        return JsonResponse(
            {
                "is_uploaded": inspection.is_uploaded_to_drive,
                "google_drive_url": inspection.google_drive_file_url,
                "file_name": inspection.google_drive_file_name,
                "file_id": inspection.google_drive_file_id,
            }
        )
    except Exception as e:
        return JsonResponse({"is_uploaded": False, "error": str(e)})


@login_required
def check_upload_status_by_code(request, inspection_code):
    """التحقق من حالة رفع الملف باستخدام كود المعاينة"""
    try:
        # تحويل كود المعاينة إلى ID
        if "-I" in inspection_code:
            order_number = inspection_code.replace("-I", "")
            inspection = Inspection.objects.filter(
                order__order_number=order_number
            ).first()
            if not inspection:
                raise Http404("المعاينة غير موجودة")
        else:
            inspection_id = inspection_code.replace("#", "").replace("-I", "")
            inspection = get_object_or_404(Inspection, id=inspection_id)

        # استدعاء الدالة الأصلية
        return check_upload_status(request, inspection.pk)
    except Exception as e:
        return JsonResponse({"is_uploaded": False, "error": str(e)})

    def handle_no_permission(self):
        messages.error(self.request, "ليس لديك صلاحية لتعديل هذه المعاينة")
        return redirect("inspections:inspection_list")


class InspectionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Inspection
    success_url = reverse_lazy("inspections:inspection_list")
    template_name = "inspections/inspection_confirm_delete.html"

    def test_func(self):
        inspection = self.get_object()
        return (
            self.request.user.is_superuser or inspection.created_by == self.request.user
        )

    def form_valid(self, form):
        messages.success(self.request, "تم حذف المعاينة بنجاح")
        return super().form_valid(form)

    def handle_no_permission(self):
        messages.error(self.request, "ليس لديك صلاحية لحذف هذه المعاينة")
        return redirect("inspections:inspection_list")


class EvaluationCreateView(LoginRequiredMixin, CreateView):
    form_class = InspectionEvaluationForm
    template_name = "inspections/evaluation_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("instance", None)
        return kwargs

    def form_valid(self, form):
        inspection = get_object_or_404(Inspection, pk=self.kwargs["inspection_pk"])
        notes = form.cleaned_data.get("notes", "")
        user = self.request.user
        created = 0
        with transaction.atomic():
            for criteria in [
                "location",
                "condition",
                "suitability",
                "safety",
                "accessibility",
            ]:
                rating = form.cleaned_data.get(criteria)
                if rating:
                    InspectionEvaluation.objects.create(
                        inspection=inspection,
                        criteria=criteria,
                        rating=rating,
                        notes=notes,
                        created_by=user,
                    )
                    created += 1
        if created:
            messages.success(self.request, f"تم إضافة {created} تقييمات للمعاينة بنجاح")
        else:
            messages.warning(self.request, "لم يتم إضافة أي تقييمات")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(
            "inspections:inspection_detail", kwargs={"pk": self.kwargs["inspection_pk"]}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["inspection"] = get_object_or_404(
            Inspection, pk=self.kwargs["inspection_pk"]
        )
        return context


class InspectionReportCreateView(LoginRequiredMixin, CreateView):
    model = InspectionReport
    form_class = InspectionReportForm
    template_name = "inspections/inspection_report_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        self.object.calculate_statistics()
        messages.success(self.request, "تم إنشاء تقرير المعاينات بنجاح")
        return response

    def get_success_url(self):
        return reverse("inspections:inspection_list")


class NotificationListView(PaginationFixMixin, LoginRequiredMixin, ListView):
    model = InspectionNotification
    template_name = "inspections/notifications/notification_list.html"  # Updated path
    context_object_name = "notifications"
    paginate_by = 10
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def get_queryset(self):
        return InspectionNotification.objects.filter(
            recipient=self.request.user
        ).order_by("-created_at")


class NotificationCreateView(LoginRequiredMixin, CreateView):
    model = InspectionNotification
    form_class = InspectionNotificationForm
    template_name = "inspections/notifications/notification_form.html"  # Updated path

    def form_valid(self, form):
        inspection = get_object_or_404(Inspection, pk=self.kwargs["inspection_pk"])
        form.instance.inspection = inspection
        form.instance.sender = self.request.user
        messages.success(self.request, "تم إرسال الإشعار بنجاح")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "inspections:inspection_detail", kwargs={"pk": self.kwargs["inspection_pk"]}
        )


def mark_notification_read(request, pk):
    notification = get_object_or_404(InspectionNotification, pk=pk)
    if request.user == notification.recipient:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        messages.success(request, "تم تحديث حالة الإشعار")
    return redirect("inspections:notification_list")


@login_required
def iterate_inspection(request, pk):
    """
    Create a new inspection as an iteration of a completed inspection.
    This allows for continued follow-up on completed inspections.
    """
    try:
        # Get the original inspection
        original_inspection = get_object_or_404(Inspection, pk=pk)

        # Verify the inspection is completed
        if original_inspection.status != "completed":
            messages.error(request, _("يمكن فقط تكرار المعاينات المكتملة."))
            return redirect("inspections:inspection_detail", pk=pk)

        # Create a new inspection based on the original
        new_inspection = Inspection(
            customer=original_inspection.customer,
            branch=original_inspection.branch,
            inspector=original_inspection.inspector,
            responsible_employee=original_inspection.responsible_employee,
            is_from_orders=original_inspection.is_from_orders,
            windows_count=original_inspection.windows_count,
            request_date=timezone.now().date(),
            scheduled_date=timezone.now().date()
            + timezone.timedelta(days=2),  # Schedule for 2 days later
            status="pending",
            notes=_(
                "تكرار من المعاينة رقم: {0}\nملاحظات المعاينة السابقة:\n{1}"
            ).format(original_inspection.contract_number, original_inspection.notes),
            order_notes=original_inspection.order_notes,
            created_by=request.user,
            order=original_inspection.order,
        )

        # Generate a new contract number
        new_inspection.contract_number = None  # Will be auto-generated on save
        new_inspection.save()

        messages.success(
            request, _("تم إنشاء معاينة جديدة كتكرار للمعاينة السابقة بنجاح.")
        )
        return redirect("inspections:inspection_detail", pk=new_inspection.pk)

    except Exception as e:
        messages.error(request, _("حدث خطأ أثناء تكرار المعاينة: {0}").format(str(e)))
        return redirect("inspections:inspection_detail", pk=pk)


@login_required
def iterate_inspection_by_code(request, inspection_code):
    """تكرار المعاينة باستخدام كود المعاينة"""
    try:
        # تحويل كود المعاينة إلى ID
        if "-I" in inspection_code:
            order_number = inspection_code.replace("-I", "")
            inspection = Inspection.objects.filter(
                order__order_number=order_number
            ).first()
            if not inspection:
                raise Http404("المعاينة غير موجودة")
        else:
            inspection_id = inspection_code.replace("#", "").replace("-I", "")
            inspection = get_object_or_404(Inspection, id=inspection_id)

        # استدعاء الدالة الأصلية
        return iterate_inspection(request, inspection.pk)
    except Exception as e:
        messages.error(request, f"حدث خطأ: {str(e)}")
        return redirect("inspections:inspection_list")


@login_required
def ajax_duplicate_inspection(request):
    """
    AJAX endpoint for duplicating an inspection from the modal window.
    """
    if request.method == "POST":
        try:
            # Get parameters from request
            inspection_id = request.POST.get("inspection_id")
            scheduled_date = request.POST.get("scheduled_date")
            additional_notes = request.POST.get("additional_notes", "")

            # Validate parameters
            if not inspection_id or not scheduled_date:
                return JsonResponse(
                    {
                        "success": False,
                        "error": _(
                            "معلومات ناقصة. الرجاء تحديد المعاينة وتاريخ التنفيذ."
                        ),
                    }
                )

            # Get the original inspection
            original_inspection = get_object_or_404(Inspection, pk=inspection_id)

            # Verify the inspection is completed
            if original_inspection.status != "completed":
                return JsonResponse(
                    {"success": False, "error": _("يمكن فقط تكرار المعاينات المكتملة.")}
                )

            # Format notes
            notes = _(
                "تكرار من المعاينة رقم: {0}\nملاحظات المعاينة السابقة:\n{1}"
            ).format(original_inspection.contract_number, original_inspection.notes)

            # Add additional notes if provided
            if additional_notes:
                notes += f"\n\n{_('ملاحظات إضافية:')}\n{additional_notes}"

            # Create a new inspection based on the original
            with transaction.atomic():
                new_inspection = Inspection(
                    customer=original_inspection.customer,
                    branch=original_inspection.branch,
                    inspector=original_inspection.inspector,
                    responsible_employee=original_inspection.responsible_employee,
                    is_from_orders=original_inspection.is_from_orders,
                    windows_count=original_inspection.windows_count,
                    request_date=timezone.now().date(),
                    scheduled_date=scheduled_date,  # Use the date from the modal
                    status="pending",
                    notes=notes,
                    order_notes=original_inspection.order_notes,
                    created_by=request.user,
                    order=original_inspection.order,
                )

                # Generate a new contract number
                new_inspection.contract_number = None  # Will be auto-generated on save
                new_inspection.save()

            return JsonResponse(
                {
                    "success": True,
                    "inspection_id": new_inspection.id,
                    "message": _(
                        "تم إنشاء معاينة جديدة كتكرار للمعاينة السابقة بنجاح."
                    ),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    else:
        return JsonResponse({"success": False, "error": _("طريقة الطلب غير مدعومة.")})


@login_required
def ajax_upload_to_google_drive(request):
    """رفع ملف المعاينة إلى Google Drive عبر AJAX"""
    if request.method == "POST":
        try:
            inspection_id = request.POST.get("inspection_id")

            if not inspection_id:
                return JsonResponse(
                    {"success": False, "message": "معرف المعاينة مطلوب"}
                )

            # الحصول على المعاينة
            inspection = get_object_or_404(Inspection, id=inspection_id)

            # التحقق من وجود ملف المعاينة
            if not inspection.inspection_file:
                return JsonResponse(
                    {"success": False, "message": "لا يوجد ملف معاينة للرفع"}
                )

            # التحقق من أن الملف لم يتم رفعه مسبقاً
            if inspection.is_uploaded_to_drive:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "تم رفع هذا الملف مسبقاً إلى Google Drive",
                    }
                )

            # جدولة رفع الملف إلى Google Drive بشكل غير متزامن
            success = inspection.schedule_upload_to_google_drive()

            if not success:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "فشل في جدولة رفع الملف. يرجى المحاولة مرة أخرى.",
                    }
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": "تم جدولة رفع الملف إلى Google Drive. سيتم الرفع في الخلفية.",
                    "data": {
                        "inspection_id": inspection.id,
                        "status": "scheduled",
                        "message": "جاري الرفع في الخلفية...",
                    },
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"خطأ في رفع الملف: {str(e)}"}
            )

    return JsonResponse({"success": False, "message": "طريقة الطلب غير صحيحة"})


# Views للوصول بالكود بدلاً من ID
@login_required
def inspection_detail_by_code(request, inspection_code):
    """عرض تفاصيل المعاينة باستخدام كود المعاينة"""
    # البحث بطريقة محسنة للأداء
    if "-I" in inspection_code:
        order_number = inspection_code.replace("-I", "")
        # البحث عن أول معاينة للطلب
        inspection = (
            Inspection.objects.select_related(
                "customer", "order", "inspector", "branch"
            )
            .filter(order__order_number=order_number)
            .first()
        )
        if not inspection:
            raise Http404("المعاينة غير موجودة")
    else:
        # للأكواد القديمة مثل #4489-I
        inspection_id = inspection_code.replace("#", "").replace("-I", "")
        inspection = get_object_or_404(
            Inspection.objects.select_related(
                "customer", "order", "inspector", "branch"
            ),
            id=inspection_id,
        )

    return InspectionDetailView.as_view()(request, pk=inspection.pk)


@login_required
def inspection_update_by_code(request, inspection_code):
    """تحديث المعاينة باستخدام كود المعاينة"""
    if "-I" in inspection_code:
        order_number = inspection_code.replace("-I", "")
        # البحث عن أول معاينة للطلب (أو الوحيدة إذا كانت واحدة)
        try:
            inspection = Inspection.objects.filter(
                order__order_number=order_number
            ).first()
            if not inspection:
                raise Http404("المعاينة غير موجودة")
        except Inspection.DoesNotExist:
            raise Http404("المعاينة غير موجودة")
    else:
        inspection_id = inspection_code.replace("#", "").replace("-I", "")
        inspection = get_object_or_404(Inspection, id=inspection_id)

    return InspectionUpdateView.as_view()(request, pk=inspection.pk)


@login_required
def inspection_delete_by_code(request, inspection_code):
    """حذف المعاينة باستخدام كود المعاينة"""
    if "-I" in inspection_code:
        order_number = inspection_code.replace("-I", "")
        # البحث عن أول معاينة للطلب
        inspection = Inspection.objects.filter(order__order_number=order_number).first()
        if not inspection:
            raise Http404("المعاينة غير موجودة")
    else:
        inspection_id = inspection_code.replace("#", "").replace("-I", "")
        inspection = get_object_or_404(Inspection, id=inspection_id)

    return InspectionDeleteView.as_view()(request, pk=inspection.pk)


# Views للإعادة التوجيه من ID إلى كود
@login_required
def inspection_detail_redirect(request, pk):
    """إعادة توجيه من ID إلى كود المعاينة"""
    inspection = get_object_or_404(Inspection, pk=pk)
    return redirect(
        "inspections:inspection_detail_by_code",
        inspection_code=inspection.inspection_code,
    )


@login_required
def inspection_update_redirect(request, pk):
    """إعادة توجيه من ID إلى كود المعاينة للتحديث"""
    inspection = get_object_or_404(Inspection, pk=pk)
    return redirect(
        "inspections:inspection_update_by_code",
        inspection_code=inspection.inspection_code,
    )


@login_required
def inspection_delete_redirect(request, pk):
    """إعادة توجيه من ID إلى كود المعاينة للحذف"""
    inspection = get_object_or_404(Inspection, pk=pk)
    return redirect(
        "inspections:inspection_delete_by_code",
        inspection_code=inspection.inspection_code,
    )


@login_required
def inspection_schedule_view(request):
    """عرض جدولة المعاينات حسب التاريخ"""
    # الحصول على التاريخ المحدد أو التاريخ الحالي
    selected_date = request.GET.get("date")
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # الحصول على المعاينات المجدولة فقط لهذا التاريخ
    inspections = (
        Inspection.objects.filter(
            scheduled_date=selected_date, status="scheduled"  # المجدولة فقط
        )
        .select_related(
            "customer", "inspector", "branch", "order", "responsible_employee"
        )
        .order_by("scheduled_time", "created_at")
    )

    # تطبيق فلتر الصلاحيات
    if not request.user.is_superuser:
        inspections = inspections.filter(
            Q(inspector=request.user) | Q(created_by=request.user)
        )

    # إحصائيات التاريخ المحدد
    total_inspections = inspections.count()
    scheduled_inspections = total_inspections  # كلها مجدولة
    pending_inspections = 0  # لا نعرض المعلقة

    # الحصول على التواريخ التي تحتوي على معاينات مجدولة (للتنقل السريع)
    dates_with_inspections = (
        Inspection.objects.filter(
            scheduled_date__isnull=False, status="scheduled"  # المجدولة فقط
        )
        .values_list("scheduled_date", flat=True)
        .distinct()
        .order_by("scheduled_date")
    )

    if not request.user.is_superuser:
        dates_with_inspections = (
            Inspection.objects.filter(
                Q(inspector=request.user) | Q(created_by=request.user),
                scheduled_date__isnull=False,
                status="scheduled",  # المجدولة فقط
            )
            .values_list("scheduled_date", flat=True)
            .distinct()
            .order_by("scheduled_date")
        )

    context = {
        "inspections": inspections,
        "selected_date": selected_date,
        "total_inspections": total_inspections,
        "scheduled_inspections": scheduled_inspections,
        "pending_inspections": pending_inspections,
        "dates_with_inspections": dates_with_inspections,
        "today": timezone.now().date(),
        "prev_date": selected_date - timedelta(days=1),
        "next_date": selected_date + timedelta(days=1),
    }

    return render(request, "inspections/inspection_schedule.html", context)


@login_required
def print_daily_schedule(request):
    """طباعة الجدول اليومي للمعاينات"""
    # الحصول على التاريخ المحدد
    selected_date = request.GET.get("date")
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # الحصول على المعاينات المجدولة فقط لهذا التاريخ
    inspections = (
        Inspection.objects.filter(
            scheduled_date=selected_date, status="scheduled"  # المجدولة فقط
        )
        .select_related(
            "customer", "inspector", "branch", "order", "responsible_employee"
        )
        .order_by("scheduled_time", "created_at")
    )

    # تطبيق فلتر الصلاحيات
    if not request.user.is_superuser:
        inspections = inspections.filter(
            Q(inspector=request.user) | Q(created_by=request.user)
        )

    # تجميع المعاينات حسب المعاين
    inspections_by_inspector = {}
    inspections_without_inspector = []

    for inspection in inspections:
        if inspection.inspector:
            inspector_name = (
                inspection.inspector.get_full_name() or inspection.inspector.username
            )
            if inspector_name not in inspections_by_inspector:
                inspections_by_inspector[inspector_name] = []
            inspections_by_inspector[inspector_name].append(inspection)
        else:
            inspections_without_inspector.append(inspection)

    context = {
        "inspections": inspections,
        "inspections_by_inspector": inspections_by_inspector,
        "inspections_without_inspector": inspections_without_inspector,
        "selected_date": selected_date,
        "total_inspections": inspections.count(),
        "print_date": timezone.now(),
        "user": request.user,
    }

    return render(request, "inspections/print_daily_schedule.html", context)
