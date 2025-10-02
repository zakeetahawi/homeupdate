from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.models import Department
from core.mixins import PaginationFixMixin
from customers.models import Customer
from notifications.models import Notification
from orders.models import Order

from .forms import (
    ComplaintAssignmentForm,
    ComplaintAttachmentForm,
    ComplaintBulkActionForm,
    ComplaintCustomerRatingForm,
    ComplaintEscalationForm,
    ComplaintFilterForm,
    ComplaintForm,
    ComplaintResolutionForm,
    ComplaintStatusUpdateForm,
    ComplaintUpdateForm,
)
from .models import (
    Complaint,
    ComplaintEvaluation,
    ComplaintType,
    ComplaintUpdate,
    ResolutionMethod,
)


class ComplaintDashboardView(LoginRequiredMixin, TemplateView):
    """لوحة تحكم الشكاوى"""

    template_name = "complaints/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # تحسين الاستعلامات بدون كاش لتجنب مشاكل BrokenPipe
        from django.db.models import Case, IntegerField, When

        status_stats = Complaint.objects.aggregate(
            total_complaints=Count("id"),
            new_complaints=Count(
                Case(When(status="new", then=1), output_field=IntegerField())
            ),
            in_progress_complaints=Count(
                Case(When(status="in_progress", then=1), output_field=IntegerField())
            ),
            resolved_complaints=Count(
                Case(When(status="resolved", then=1), output_field=IntegerField())
            ),
            pending_evaluation_complaints=Count(
                Case(
                    When(status="pending_evaluation", then=1),
                    output_field=IntegerField(),
                )
            ),
            closed_complaints=Count(
                Case(When(status="closed", then=1), output_field=IntegerField())
            ),
            overdue_complaints=Count(
                Case(When(status="overdue", then=1), output_field=IntegerField())
            ),
            avg_rating=Avg("customer_rating"),
        )

        # إحصائيات حسب النوع مع تحسين الاستعلام
        complaints_by_type = (
            Complaint.objects.select_related("complaint_type")
            .values("complaint_type__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # إحصائيات حسب الأولوية
        complaints_by_priority = (
            Complaint.objects.values("priority")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # إحصائيات حسب المسؤول مع تحسين الاستعلام
        complaints_by_assignee = (
            Complaint.objects.select_related("assigned_to")
            .exclude(assigned_to__isnull=True)
            .values("assigned_to__first_name", "assigned_to__last_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # الشكاوى الحديثة مع تحسين العلاقات
        recent_complaints = Complaint.objects.select_related(
            "customer", "complaint_type", "assigned_to", "assigned_department"
        ).order_by("-created_at")[:10]

        # الشكاوى المتأخرة مع تحسين الاستعلام
        now = timezone.now()
        overdue_complaints_list = (
            Complaint.objects.filter(
                deadline__lt=now, status__in=["new", "in_progress", "overdue"]
            )
            .select_related(
                "customer", "complaint_type", "assigned_to", "assigned_department"
            )
            .order_by("deadline")[:10]
        )

        # تحديث إحصائيات الشكاوى المتأخرة الفعلية
        actual_overdue_count = Complaint.objects.filter(
            deadline__lt=now, status__in=["new", "in_progress", "overdue"]
        ).count()

        # تحديث حالة الشكاوى المتأخرة
        overdue_to_update = Complaint.objects.filter(
            deadline__lt=now, status__in=["new", "in_progress"]
        )
        if overdue_to_update.exists():
            overdue_to_update.update(status="overdue")
            # إعادة حساب الإحصائيات بعد التحديث
            status_stats = Complaint.objects.aggregate(
                total_complaints=Count("id"),
                new_complaints=Count(
                    Case(When(status="new", then=1), output_field=IntegerField())
                ),
                in_progress_complaints=Count(
                    Case(
                        When(status="in_progress", then=1), output_field=IntegerField()
                    )
                ),
                resolved_complaints=Count(
                    Case(When(status="resolved", then=1), output_field=IntegerField())
                ),
                pending_evaluation_complaints=Count(
                    Case(
                        When(status="pending_evaluation", then=1),
                        output_field=IntegerField(),
                    )
                ),
                closed_complaints=Count(
                    Case(When(status="closed", then=1), output_field=IntegerField())
                ),
                overdue_complaints=Count(
                    Case(When(status="overdue", then=1), output_field=IntegerField())
                ),
                escalated_complaints=Count(
                    Case(When(status="escalated", then=1), output_field=IntegerField())
                ),
                avg_rating=Avg("customer_rating"),
            )

        # إحصائيات الأداء (آخر 30 يوم) مع تحسين الاستعلام
        thirty_days_ago = now - timedelta(days=30)
        performance_stats = Complaint.objects.filter(
            created_at__gte=thirty_days_ago
        ).aggregate(
            new_complaints_30d=Count("id"),
            resolved_complaints_30d=Count(
                Case(
                    When(status="resolved", resolved_at__gte=thirty_days_ago, then=1),
                    output_field=IntegerField(),
                )
            ),
            closed_complaints_30d=Count(
                Case(
                    When(status="closed", closed_at__gte=thirty_days_ago, then=1),
                    output_field=IntegerField(),
                )
            ),
        )

        # إضافة إحصائيات إضافية للأداء
        performance_stats.update(
            {
                "total_resolved_and_closed_30d": (
                    performance_stats["resolved_complaints_30d"]
                    + performance_stats["closed_complaints_30d"]
                ),
                "resolution_rate_30d": (
                    round(
                        (
                            performance_stats["resolved_complaints_30d"]
                            + performance_stats["closed_complaints_30d"]
                        )
                        / max(performance_stats["new_complaints_30d"], 1)
                        * 100,
                        1,
                    )
                    if performance_stats["new_complaints_30d"] > 0
                    else 0
                ),
            }
        )

        # حساب متوسط وقت الحل بشكل محسن
        performance_stats["avg_resolution_time"] = self.calculate_avg_resolution_time()

        # تجميع البيانات للـ context
        dashboard_data = {
            "total_complaints": status_stats["total_complaints"],
            "new_complaints": status_stats["new_complaints"],
            "in_progress_complaints": status_stats["in_progress_complaints"],
            "resolved_complaints": status_stats["resolved_complaints"],
            "pending_evaluation_complaints": status_stats[
                "pending_evaluation_complaints"
            ],
            "closed_complaints": status_stats["closed_complaints"],
            "overdue_complaints": status_stats["overdue_complaints"],
            "escalated_complaints": status_stats.get("escalated_complaints", 0),
            "complaints_by_type": list(complaints_by_type),
            "complaints_by_priority": list(complaints_by_priority),
            "complaints_by_assignee": list(complaints_by_assignee),
            "recent_complaints": recent_complaints,
            "overdue_complaints_list": overdue_complaints_list,
            "avg_rating": round(status_stats["avg_rating"] or 0, 2),
            "performance_stats": performance_stats,
            "actual_overdue_count": actual_overdue_count,
        }

        context.update(dashboard_data)
        return context

    def calculate_avg_resolution_time(self):
        """حساب متوسط وقت الحل بشكل محسن"""
        from django.db.models import Avg, DurationField, ExpressionWrapper, F

        # استخدام استعلام قاعدة البيانات لحساب المتوسط مباشرة
        avg_resolution = (
            Complaint.objects.filter(
                resolved_at__isnull=False, created_at__isnull=False
            )
            .annotate(
                resolution_duration=ExpressionWrapper(
                    F("resolved_at") - F("created_at"), output_field=DurationField()
                )
            )
            .aggregate(avg_duration=Avg("resolution_duration"))["avg_duration"]
        )

        if avg_resolution:
            avg_hours = avg_resolution.total_seconds() / 3600
            return round(avg_hours, 1)

        return 0


class ComplaintListView(PaginationFixMixin, LoginRequiredMixin, ListView):
    """قائمة الشكاوى"""

    model = Complaint
    template_name = "complaints/complaint_list.html"
    context_object_name = "complaints"
    paginate_by = 20
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def get_queryset(self):
        # تحسين الاستعلامات مع تجنب مشاكل الكاش
        queryset = Complaint.objects.select_related(
            "customer",
            "complaint_type",
            "assigned_to",
            "assigned_department",
            "created_by",
            "branch",
            "related_order",
        ).order_by("-created_at")

        # تطبيق صلاحيات الوصول للشكاوى
        queryset = self.apply_complaint_permissions(queryset)

        # تطبيق الفلاتر المحسنة
        form = ComplaintFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("status"):
                queryset = queryset.filter(status=form.cleaned_data["status"])

            if form.cleaned_data.get("priority"):
                queryset = queryset.filter(priority=form.cleaned_data["priority"])

            if form.cleaned_data.get("complaint_type"):
                queryset = queryset.filter(
                    complaint_type=form.cleaned_data["complaint_type"]
                )

            if form.cleaned_data.get("assigned_to"):
                queryset = queryset.filter(assigned_to=form.cleaned_data["assigned_to"])

            if form.cleaned_data.get("assigned_department"):
                queryset = queryset.filter(
                    assigned_department=form.cleaned_data["assigned_department"]
                )

            if form.cleaned_data["date_from"]:
                queryset = queryset.filter(
                    created_at__date__gte=form.cleaned_data["date_from"]
                )

            if form.cleaned_data["date_to"]:
                queryset = queryset.filter(
                    created_at__date__lte=form.cleaned_data["date_to"]
                )

            if form.cleaned_data.get("search"):
                search_term = form.cleaned_data["search"]
                search_query = (
                    Q(complaint_number__icontains=search_term)
                    | Q(customer__name__icontains=search_term)
                    | Q(title__icontains=search_term)
                    | Q(description__icontains=search_term)
                )
                queryset = queryset.filter(search_query)

        # الفلاتر المتقدمة
        customer_name = self.request.GET.get("customer_name")
        if customer_name:
            queryset = queryset.filter(customer__name__icontains=customer_name)

        complaint_id = self.request.GET.get("complaint_id")
        if complaint_id:
            queryset = queryset.filter(id__icontains=complaint_id)

        assigned_to = self.request.GET.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        evaluation_status = self.request.GET.get("evaluation_status")
        if evaluation_status == "needs_evaluation":
            queryset = queryset.filter(status="pending_evaluation")
        elif evaluation_status == "evaluated":
            queryset = queryset.filter(status="closed", evaluation__isnull=False)
        elif evaluation_status == "not_evaluated":
            queryset = queryset.filter(status="closed", evaluation__isnull=True)

        return queryset

    def apply_complaint_permissions(self, queryset):
        """تطبيق صلاحيات الوصول للشكاوى"""
        user = self.request.user

        # مدير النظام يرى جميع الشكاوى
        if user.is_superuser:
            return queryset

        # مدير الشكاوى يرى جميع الشكاوى
        if user.groups.filter(name="Complaints_Managers").exists():
            return queryset

        # مشرف الشكاوى يرى جميع الشكاوى
        if user.groups.filter(name="Complaints_Supervisors").exists():
            return queryset

        # المدراء يرون جميع الشكاوى
        if user.groups.filter(name="Managers").exists():
            return queryset

        # مدير القسم يرى شكاوى قسمه
        if hasattr(user, "managed_departments") and user.managed_departments.exists():
            managed_departments = user.managed_departments.all()
            return queryset.filter(assigned_department__in=managed_departments)

        # المستخدم العادي يرى الشكاوى المعينة إليه أو التي أنشأها
        return queryset.filter(Q(assigned_to=user) | Q(created_by=user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = ComplaintFilterForm(self.request.GET)
        context["bulk_action_form"] = ComplaintBulkActionForm()

        # قائمة المستخدمين للفلاتر المتقدمة
        from django.contrib.auth import get_user_model

        User = get_user_model()
        context["users"] = User.objects.filter(is_active=True).order_by(
            "first_name", "last_name"
        )

        # إضافة معلومات الصلاحيات للسياق
        context["is_admin"] = (
            self.request.user.is_superuser
            or self.request.user.groups.filter(
                name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
            ).exists()
        )

        return context


class AdminComplaintListView(PaginationFixMixin, LoginRequiredMixin, ListView):
    """قائمة الشكاوى للمدراء - وصول كامل لجميع الشكاوى غير المحلولة"""

    model = Complaint
    template_name = "complaints/admin_complaint_list.html"
    context_object_name = "complaints"
    paginate_by = 25
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

    def dispatch(self, request, *args, **kwargs):
        # التحقق من صلاحيات المدير
        if not (
            request.user.is_superuser
            or request.user.groups.filter(
                name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
            ).exists()
        ):
            messages.error(request, "ليس لديك صلاحية للوصول إلى هذه الصفحة")
            return redirect("complaints:complaint_list")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # المدراء يرون جميع الشكاوى غير المحلولة
        queryset = (
            Complaint.objects.select_related(
                "customer", "complaint_type", "assigned_to", "assigned_department"
            )
            .exclude(status__in=["resolved", "closed"])
            .order_by("-created_at", "-priority")
        )

        # تطبيق الفلاتر المحسنة
        form = ComplaintFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("status"):
                queryset = queryset.filter(status=form.cleaned_data["status"])

            if form.cleaned_data.get("priority"):
                queryset = queryset.filter(priority=form.cleaned_data["priority"])

            if form.cleaned_data.get("complaint_type"):
                queryset = queryset.filter(
                    complaint_type=form.cleaned_data["complaint_type"]
                )

            if form.cleaned_data.get("assigned_to"):
                queryset = queryset.filter(assigned_to=form.cleaned_data["assigned_to"])

            if form.cleaned_data.get("assigned_department"):
                queryset = queryset.filter(
                    assigned_department=form.cleaned_data["assigned_department"]
                )

            if form.cleaned_data["date_from"]:
                queryset = queryset.filter(
                    created_at__date__gte=form.cleaned_data["date_from"]
                )

            if form.cleaned_data["date_to"]:
                queryset = queryset.filter(
                    created_at__date__lte=form.cleaned_data["date_to"]
                )

            if form.cleaned_data.get("search"):
                search_term = form.cleaned_data["search"]
                search_query = (
                    Q(complaint_number__icontains=search_term)
                    | Q(customer__name__icontains=search_term)
                    | Q(title__icontains=search_term)
                    | Q(description__icontains=search_term)
                )
                queryset = queryset.filter(search_query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = ComplaintFilterForm(self.request.GET)
        context["bulk_action_form"] = ComplaintBulkActionForm()

        # إحصائيات للمدراء
        all_unresolved = Complaint.objects.exclude(status__in=["resolved", "closed"])
        context["stats"] = {
            "total_unresolved": all_unresolved.count(),
            "urgent_count": all_unresolved.filter(priority="urgent").count(),
            "overdue_count": all_unresolved.filter(deadline__lt=timezone.now()).count(),
            "escalated_count": all_unresolved.filter(status="escalated").count(),
            "unassigned_count": all_unresolved.filter(assigned_to__isnull=True).count(),
        }

        context["is_admin_view"] = True

        return context


class ComplaintReportsView(LoginRequiredMixin, TemplateView):
    """تقارير الشكاوى المتقدمة"""

    template_name = "complaints/reports.html"

    def dispatch(self, request, *args, **kwargs):
        # التحقق من صلاحيات الوصول للتقارير
        if not (
            request.user.is_superuser
            or request.user.groups.filter(
                name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
            ).exists()
        ):
            messages.error(request, "ليس لديك صلاحية للوصول إلى التقارير")
            return redirect("complaints:complaint_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # نموذج الفلترة للتقارير
        context["filter_form"] = ComplaintFilterForm(self.request.GET)

        # إحصائيات عامة
        all_complaints = Complaint.objects.all()
        context["total_complaints"] = all_complaints.count()
        context["resolved_complaints"] = all_complaints.filter(
            status="resolved"
        ).count()
        context["pending_complaints"] = all_complaints.exclude(
            status__in=["resolved", "closed"]
        ).count()

        # إحصائيات حسب الفترة الزمنية
        from datetime import datetime, timedelta

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        context["this_week"] = all_complaints.filter(
            created_at__date__gte=week_ago
        ).count()
        context["this_month"] = all_complaints.filter(
            created_at__date__gte=month_ago
        ).count()

        # إحصائيات حسب الأولوية
        context["priority_stats"] = {
            "urgent": all_complaints.filter(priority="urgent").count(),
            "high": all_complaints.filter(priority="high").count(),
            "medium": all_complaints.filter(priority="medium").count(),
            "low": all_complaints.filter(priority="low").count(),
        }

        # إحصائيات حسب الحالة
        context["status_stats"] = {
            "new": all_complaints.filter(status="new").count(),
            "in_progress": all_complaints.filter(status="in_progress").count(),
            "resolved": all_complaints.filter(status="resolved").count(),
            "closed": all_complaints.filter(status="closed").count(),
            "escalated": all_complaints.filter(status="escalated").count(),
            "overdue": all_complaints.filter(status="overdue").count(),
        }

        # إحصائيات حسب نوع الشكوى
        complaint_types = ComplaintType.objects.annotate(
            complaint_count=Count("complaint")
        ).order_by("-complaint_count")[:10]
        context["type_stats"] = complaint_types

        # متوسط وقت الحل
        resolved_complaints = all_complaints.filter(
            status="resolved", resolved_at__isnull=False
        )
        if resolved_complaints.exists():
            total_resolution_time = sum(
                [
                    (complaint.resolved_at - complaint.created_at).total_seconds()
                    / 3600
                    for complaint in resolved_complaints
                ]
            )
            context["avg_resolution_time"] = round(
                total_resolution_time / resolved_complaints.count(), 2
            )
        else:
            context["avg_resolution_time"] = 0

        # أفضل الموظفين في حل الشكاوى
        from django.contrib.auth import get_user_model

        User = get_user_model()
        top_resolvers = (
            User.objects.annotate(
                resolved_count=Count(
                    "assigned_complaints",
                    filter=Q(assigned_complaints__status="resolved"),
                )
            )
            .filter(resolved_count__gt=0)
            .order_by("-resolved_count")[:5]
        )
        context["top_resolvers"] = top_resolvers

        return context


class ComplaintDetailView(LoginRequiredMixin, DetailView):
    """تفاصيل الشكوى مع تحسين الأداء والكاش"""

    model = Complaint
    template_name = "complaints/complaint_detail.html"
    context_object_name = "complaint"

    def get_object(self):
        """تحسين جلب تفاصيل الشكوى بتقليل الاستعلامات"""
        complaint_id = self.kwargs.get("pk")

        # جلب واحد محسن مع جميع العلاقات
        return get_object_or_404(self.get_queryset(), pk=complaint_id)

    def get_queryset(self):
        """تحسين الاستعلامات باستخدام select_related و prefetch_related"""
        return Complaint.objects.select_related(
            "customer",
            "complaint_type",
            "assigned_to",
            "assigned_department",
            "created_by",
            "branch",
            "related_order",
            "resolution_method",
        ).prefetch_related(
            "updates__created_by",
            "attachments__uploaded_by",
            "notifications__recipient",
            "escalations__escalated_by",
            "escalations__escalated_to",
        )

    def get_context_data(self, **kwargs):
        """تحسين جلب البيانات السياقية مع تقليل الاستعلامات"""
        context = super().get_context_data(**kwargs)

        # إعداد النماذج بناءً على حالة الشكوى
        forms_data = {
            "update_form": ComplaintUpdateForm(),
            "status_form": ComplaintStatusUpdateForm(instance=self.object),
            "assignment_form": ComplaintAssignmentForm(instance=self.object),
            "escalation_form": ComplaintEscalationForm(),
            "attachment_form": ComplaintAttachmentForm(),
        }

        # إضافة نماذج إضافية حسب حالة الشكوى
        if self.object.status == "pending_evaluation":
            forms_data["rating_form"] = ComplaintCustomerRatingForm(
                instance=self.object
            )
        elif self.object.status not in ["resolved", "closed"]:
            forms_data["resolution_form"] = ComplaintResolutionForm(
                instance=self.object
            )

        # تحديث السياق بالنماذج
        context.update(forms_data)

        # جلب البيانات المرتبطة بطريقة محسنة (تم جلبها بالفعل عبر prefetch_related)
        context.update(
            {
                "updates": self.object.updates.all()[:20],  # تحديد عدد التحديثات
                "attachments": self.object.attachments.all()[:10],  # تحديد عدد المرفقات
                "escalations": self.object.escalations.all()[:5],  # تحديد عدد التصعيدات
            }
        )

        # جلب الإشعارات بشكل محدود
        context["notifications"] = self.object.notifications.filter(
            recipient=self.request.user
        )[
            :5
        ]  # تحديد عدد الإشعارات

        # إضافة معلومات الصلاحيات بدون استعلامات إضافية
        user = self.request.user
        context.update(
            {
                "user_can_update": user.has_perm("complaints.change_complaint"),
                "user_can_resolve": user.has_perm("complaints.resolve_complaint"),
                "user_can_escalate": user.has_perm("complaints.escalate_complaint"),
                "user_can_delete": user.has_perm("complaints.delete_complaint"),
                "user_can_assign": user.has_perm("complaints.assign_complaint"),
                "is_admin": user.is_superuser or user.is_staff,
            }
        )

        # إضافة إحصائيات سريعة بدون استعلامات معقدة
        resolution_time = None
        if self.object.resolved_at and self.object.created_at:
            resolution_time = (
                self.object.resolved_at - self.object.created_at
            ).total_seconds() / 3600

        # حساب ما إذا كانت الشكوى متأخرة
        is_overdue = False
        if hasattr(self.object, "deadline") and self.object.deadline:
            is_overdue = self.object.deadline < timezone.now()

        context["complaint_stats"] = {
            "updates_count": len(context["updates"]),
            "attachments_count": len(context["attachments"]),
            "escalations_count": len(context["escalations"]),
            "resolution_time_hours": (
                round(resolution_time, 1) if resolution_time else None
            ),
            "is_overdue": is_overdue,
            "time_since_creation": round(
                (timezone.now() - self.object.created_at).total_seconds() / 3600, 1
            ),
        }

        return context


class ComplaintCreateView(LoginRequiredMixin, CreateView):
    """إنشاء شكوى جديدة"""

    model = Complaint
    form_class = ComplaintForm
    template_name = "complaints/complaint_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request

        # إذا تم تمرير معرف العميل
        customer_id = self.request.GET.get("customer_id")
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                kwargs["customer"] = customer
            except Customer.DoesNotExist:
                pass

        return kwargs

    def form_valid(self, form):
        """حفظ الشكوى مع رسائل تصحيح شاملة ودعم AJAX"""
        print("===== بدء حفظ الشكوى في الخلفية =====")

        # طباعة بيانات النموذج
        print("بيانات النموذج المستلمة:")
        for field_name, field_value in form.cleaned_data.items():
            print(f"  {field_name}: {field_value}")

        # التحقق من المستخدم الحالي
        user_info = f"المستخدم الحالي: {self.request.user.username}"
        user_info += f" (ID: {self.request.user.id})"
        print(user_info)

        try:
            # تعيين المستخدم كمُنشئ للشكوى
            form.instance.created_by = self.request.user
            print(f"تم تعيين منشئ الشكوى: {self.request.user.username}")

            # حفظ الشكوى
            print("جاري حفظ الشكوى...")
            response = super().form_valid(form)
            print(f"تم حفظ الشكوى بنجاح. رقم الشكوى: {self.object.complaint_number}")
            print(f"معرف الشكوى: {self.object.pk}")

            # طباعة تفاصيل الشكوى المحفوظة
            print("تفاصيل الشكوى المحفوظة:")
            print(f"  العنوان: {self.object.title}")
            print(f"  نوع الشكوى: {self.object.complaint_type}")
            print(f"  العميل: {self.object.customer}")
            print(f"  الأولوية: {self.object.priority}")
            print(f"  الموعد النهائي: {self.object.deadline}")
            print(f"  الموظف المسؤول: {self.object.assigned_to}")
            print(f"  القسم المختص: {self.object.assigned_department}")
            print(f"  تاريخ الإنشاء: {self.object.created_at}")

            # التحقق من الطلب المرتبط
            if self.object.related_order:
                print(
                    f"الطلب المرتبط: طلب رقم {self.object.related_order.id}: {self.object.related_order}"
                )
            else:
                print("لا يوجد طلب مرتبط")

            # التحقق من نوع الطلب (AJAX أم عادي)
            if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
                # طلب AJAX - إرسال استجابة JSON
                print("📡 إرسال استجابة AJAX")

                # معالجة العمليات المختلفة
                action = self.request.POST.get("action", "save")
                print(f"العملية المطلوبة: {action}")

                if action == "save_and_new":
                    redirect_url = reverse("complaints:complaint_create")
                else:
                    redirect_url = reverse(
                        "complaints:complaint_detail", kwargs={"pk": self.object.pk}
                    )

                message = (
                    f"تم إنشاء الشكوى بنجاح برقم " f"{self.object.complaint_number}"
                )
                return JsonResponse(
                    {
                        "status": "success",
                        "message": message,
                        "complaint_id": self.object.pk,
                        "complaint_number": self.object.complaint_number,
                        "redirect_url": redirect_url,
                    }
                )
            else:
                # طلب عادي
                # إرسال رسالة نجاح
                message = f"تم إنشاء الشكوى بنجاح برقم {self.object.complaint_number}"
                messages.success(self.request, message)
                print("تم إرسال رسالة النجاح للمستخدم")

                # معالجة العمليات المختلفة
                action = self.request.POST.get("action", "save")
                if action == "save_and_new":
                    return redirect("complaints:complaint_create")

                print("===== تم حفظ الشكوى بنجاح =====")
                return response

        except Exception as e:
            print("===== خطأ في حفظ الشكوى =====")
            print(f"نوع الخطأ: {type(e).__name__}")
            print(f"رسالة الخطأ: {str(e)}")

            # التحقق من نوع الطلب
            if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"حدث خطأ في حفظ الشكوى: {str(e)}",
                        "errors": {},
                    },
                    status=500,
                )
            else:
                # إضافة رسالة خطأ للمستخدم
                messages.error(self.request, f"حدث خطأ في حفظ الشكوى: {str(e)}")

                # إعادة عرض النموذج مع الأخطاء
                return self.form_invalid(form)

    def form_invalid(self, form):
        """التعامل مع أخطاء النموذج مع رسائل تصحيح ودعم AJAX"""
        print("===== أخطاء في النموذج =====")

        # طباعة أخطاء النموذج
        if form.errors:
            print("أخطاء الحقول:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")

        # طباعة أخطاء عامة
        if form.non_field_errors():
            print("أخطاء عامة:")
            for error in form.non_field_errors():
                print(f"  - {error}")

        # طباعة البيانات المرسلة
        print("البيانات المرسلة:")
        for key, value in self.request.POST.items():
            print(f"  {key}: {value}")

        # التحقق من نوع الطلب
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "status": "error",
                    "message": "يوجد أخطاء في النموذج",
                    "errors": form.errors,
                },
                status=400,
            )
        else:
            # إضافة رسالة خطأ للمستخدم
            messages.error(
                self.request, "يوجد أخطاء في النموذج. يرجى تصحيحها والمحاولة مرة أخرى."
            )
            return super().form_invalid(form)

    def get_success_url(self):
        return reverse("complaints:complaint_detail", kwargs={"pk": self.object.pk})


class ComplaintUpdateView(LoginRequiredMixin, UpdateView):
    """تحديث الشكوى - متاح فقط للشكاوى الجديدة"""

    model = Complaint
    form_class = ComplaintForm
    template_name = "complaints/complaint_form.html"

    def dispatch(self, request, *args, **kwargs):
        """التحقق من إمكانية التعديل قبل عرض الصفحة"""
        complaint = self.get_object()

        # منع التعديل بعد بدء الحل (فقط الشكاوى الجديدة يمكن تعديلها)
        if complaint.status != "new":
            messages.error(
                request,
                "لا يمكن تعديل محتوى الشكوى بعد بدء العمل عليها. "
                "يمكنك تغيير الحالة أو الإسناد أو التصعيد من صفحة تفاصيل الشكوى.",
            )
            return redirect("complaints:complaint_detail", pk=complaint.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        # التحقق مرة أخرى من الحالة قبل الحفظ
        if self.object.status != "new":
            messages.error(self.request, "لا يمكن تعديل الشكوى بعد بدء العمل عليها")
            return redirect("complaints:complaint_detail", pk=self.object.pk)

        response = super().form_valid(form)
        messages.success(self.request, "تم تحديث الشكوى بنجاح")
        return response


@login_required
def complaint_status_update(request, pk):
    """تحديث حالة الشكوى مع معالجة تلقائية لبدء العمل"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        form = ComplaintStatusUpdateForm(request.POST, instance=complaint)
        if form.is_valid():
            # حفظ الحالة القديمة قبل التحديث
            old_status = complaint.status
            old_status_display = complaint.get_status_display()

            # إذا كانت الحالة الجديدة هي "in_progress" وكان المستخدم غير مسند، قم بتعيينه
            if (
                form.cleaned_data["status"] == "in_progress"
                and not complaint.assigned_to
            ):
                complaint.assigned_to = request.user

            # Handle resolution method for resolved status
            resolution_method_id = request.POST.get("resolution_method")
            if form.cleaned_data["status"] == "resolved":
                if not resolution_method_id:
                    messages.error(request, "يجب اختيار طريقة الحل عند حل الشكوى")
                    return redirect("complaints:complaint_detail", pk=pk)

                try:
                    resolution_method = ResolutionMethod.objects.get(
                        id=resolution_method_id, is_active=True
                    )
                except ResolutionMethod.DoesNotExist:
                    messages.error(request, "طريقة الحل المحددة غير صحيحة")
                    return redirect("complaints:complaint_detail", pk=pk)

            complaint = form.save()

            # Set resolution method if resolving
            if complaint.status == "resolved" and resolution_method_id:
                complaint.resolution_method = resolution_method
                complaint.save()

            # إنشاء تحديث
            notes = form.cleaned_data.get("notes", "")
            description = f"تم تغيير حالة الشكوى من {old_status_display} إلى {complaint.get_status_display()}"

            if (
                complaint.status == "resolved"
                and hasattr(complaint, "resolution_method")
                and complaint.resolution_method
            ):
                description += f"\nطريقة الحل: {complaint.resolution_method.name}"

            if notes:
                description += f"\nملاحظات: {notes}"

            # إضافة معلومات إضافية لحالات معينة
            if complaint.status == "in_progress":
                description += f"\nبدأ العمل على الشكوى بواسطة: {request.user.get_full_name() or request.user.username}"
                if complaint.assigned_to == request.user:
                    description += "\nتم تعيين الشكوى تلقائياً للمستخدم الحالي"

            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type=(
                    "resolution" if complaint.status == "resolved" else "status_change"
                ),
                title=f"تغيير الحالة إلى {complaint.get_status_display()}",
                description=description,
                old_status=old_status,
                new_status=complaint.status,
                resolution_method=(
                    complaint.resolution_method
                    if complaint.status == "resolved"
                    else None
                ),
                created_by=request.user,
                is_visible_to_customer=True,
            )

            # رسائل نجاح مختلفة حسب الحالة
            if complaint.status == "in_progress":
                success_message = (
                    f"تم بدء العمل على الشكوى رقم {complaint.complaint_number} بنجاح"
                )
            elif complaint.status == "resolved":
                success_message = f"تم حل الشكوى رقم {complaint.complaint_number} بنجاح"
            else:
                success_message = f'تم تحديث حالة الشكوى رقم {complaint.complaint_number} إلى "{complaint.get_status_display()}"'

            messages.success(request, success_message)
            return redirect("complaints:complaint_detail", pk=pk)

    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def start_working_on_complaint(request, pk):
    """بدء العمل على الشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    # التحقق من أن الشكوى في حالة جديدة
    if complaint.status != "new":
        messages.warning(
            request,
            "لا يمكن بدء العمل على هذه الشكوى - الحالة الحالية: "
            + complaint.get_status_display(),
        )
        return redirect("complaints:complaint_detail", pk=pk)

    # تحديث حالة الشكوى إلى قيد المعالجة
    old_status = complaint.status
    complaint.status = "in_progress"

    # تعيين الشكوى للمستخدم الحالي إذا لم تكن مُعيّنة
    if not complaint.assigned_to:
        complaint.assigned_to = request.user

    complaint.save()

    # إنشاء سجل تحديث
    ComplaintUpdate.objects.create(
        complaint=complaint,
        update_type="status_change",
        title="بدء العمل على الشكوى",
        description=f'بدأ {request.user.get_full_name() or request.user.username} العمل على الشكوى\nتم تغيير الحالة من "جديدة" إلى "قيد المعالجة"',
        old_status=old_status,
        new_status="in_progress",
        created_by=request.user,
        is_visible_to_customer=True,
    )

    messages.success(
        request, f"تم بدء العمل على الشكوى رقم {complaint.complaint_number} بنجاح"
    )
    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def complaint_assignment(request, pk):
    """تعيين مسؤول للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        form = ComplaintAssignmentForm(request.POST, instance=complaint)
        if form.is_valid():
            old_assignee = complaint.assigned_to
            complaint = form.save()

            # إنشاء تحديث
            notes = form.cleaned_data.get("assignment_notes", "")
            assignee_name = (
                complaint.assigned_to.get_full_name()
                if complaint.assigned_to
                else "غير محدد"
            )
            description = notes or f"تم تعيين {assignee_name} كمسؤول عن الشكوى"

            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type="assignment",
                title=f"تعيين المسؤول: {assignee_name}",
                description=description,
                created_by=request.user,
                old_assignee=old_assignee,
                new_assignee=complaint.assigned_to,
                is_visible_to_customer=False,
            )

            messages.success(request, "تم تعيين المسؤول بنجاح")
            return redirect("complaints:complaint_detail", pk=pk)

    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def complaint_add_update(request, pk):
    """إضافة تحديث للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        form = ComplaintUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.complaint = complaint
            update.created_by = request.user
            update.save()

            messages.success(request, "تم إضافة التحديث بنجاح")
            return redirect("complaints:complaint_detail", pk=pk)

    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def complaint_escalate(request, pk):
    """تصعيد الشكوى مع تحسين التحقق من الصلاحيات"""
    complaint = get_object_or_404(Complaint, pk=pk)
    user = request.user

    # التحقق من الصلاحيات بشكل شامل
    has_permission = False

    # 1. التحقق من كون المستخدم مشرف النظام
    if user.is_superuser:
        has_permission = True

    # 2. التحقق من المجموعات
    elif user.groups.filter(
        name__in=[
            "Complaints_Managers",
            "Complaints_Supervisors",
            "Managers",
            "Department_Managers",  # إضافة مدراء الأقسام
        ]
    ).exists():
        has_permission = True

    # 3. التحقق من الصلاحيات المباشرة
    elif user.has_perm("complaints.escalate_complaint"):
        has_permission = True

    # 4. التحقق من سجل الصلاحيات المخصص (إذا كان موجوداً)
    try:
        if hasattr(user, "complaint_permissions"):
            user_permissions = user.complaint_permissions
            if user_permissions.is_active and user_permissions.can_escalate_complaints:
                has_permission = True
    except:
        pass

    # 5. التحقق من كون المستخدم هو المسؤول عن الشكوى
    if complaint.assigned_to == user:
        has_permission = True

    if not has_permission:
        messages.error(request, "ليس لديك صلاحية لتصعيد الشكاوى")
        return redirect("complaints:complaint_detail", pk=pk)

    if request.method == "POST":
        form = ComplaintEscalationForm(request.POST)
        if form.is_valid():
            # التحقق من صلاحيات المستخدم المستهدف
            escalated_to = form.cleaned_data["escalated_to"]
            try:
                target_permissions = escalated_to.complaint_permissions
                if (
                    not target_permissions.is_active
                    or not target_permissions.can_receive_escalations
                ):
                    messages.error(
                        request, "المستخدم المحدد لا يمكن تصعيد الشكاوى إليه"
                    )
                    return redirect("complaints:complaint_detail", pk=pk)
            except:
                # إذا لم يكن لديه سجل صلاحيات، نتحقق من المجموعات
                if not (
                    escalated_to.is_superuser
                    or escalated_to.groups.filter(
                        name__in=["Complaints_Managers", "Complaints_Supervisors"]
                    ).exists()
                ):
                    messages.error(
                        request, "المستخدم المحدد لا يمكن تصعيد الشكاوى إليه"
                    )
                    return redirect("complaints:complaint_detail", pk=pk)

            # حفظ الحالة القديمة
            old_status = complaint.status

            # إنشاء سجل تصعيد
            escalation = form.save(commit=False)
            escalation.complaint = complaint
            escalation.escalated_from = complaint.assigned_to
            escalation.escalated_by = request.user
            escalation.save()

            # تحديث حالة الشكوى
            complaint.status = "escalated"
            complaint.save()

            # إنشاء تحديث
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type="escalation",
                title="تصعيد الشكوى",
                description=f"تم تصعيد الشكوى إلى {escalation.escalated_to.get_full_name()}\nسبب التصعيد: {escalation.reason}",
                old_status=old_status,
                new_status="escalated",
                created_by=request.user,
                is_visible_to_customer=True,
            )

            messages.success(request, "تم تصعيد الشكوى بنجاح")
            return redirect("complaints:complaint_detail", pk=pk)

    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def complaint_resolve(request, pk):
    """حل الشكوى وتحويلها لانتظار التقييم"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        form = ComplaintResolutionForm(request.POST, instance=complaint)
        if form.is_valid():
            resolution_description = form.cleaned_data.get(
                "resolution_notes", "تم حل الشكوى"
            )

            # حفظ الحالة القديمة قبل التحديث
            old_status = complaint.status
            old_status_display = complaint.get_status_display()

            # تغيير الحالة إلى انتظار التقييم بدلاً من محلولة مباشرة
            complaint.status = "pending_evaluation"
            complaint.resolved_at = timezone.now()
            complaint.resolved_by = request.user
            complaint.save()

            # إنشاء تحديث
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type="resolution",
                title="تم حل الشكوى - في انتظار التقييم",
                description=f"{resolution_description}\n\nتم حل الشكوى وهي الآن في انتظار تقييم العميل",
                old_status=old_status,
                new_status="pending_evaluation",
                created_by=request.user,
                is_visible_to_customer=True,
            )

            messages.success(
                request,
                f"تم حل الشكوى رقم {complaint.complaint_number} بنجاح وهي الآن في انتظار تقييم العميل",
            )
            return redirect("complaints:complaint_detail", pk=pk)
        else:
            messages.error(request, "حدث خطأ في حل الشكوى. يرجى المحاولة مرة أخرى.")

    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def mark_complaint_as_resolved(request, pk):
    """تحديد الشكوى كمحلولة بعد التقييم"""
    complaint = get_object_or_404(Complaint, pk=pk)

    # التحقق من أن الشكوى في انتظار التقييم أو تم تقييمها
    if complaint.status not in ["pending_evaluation"]:
        messages.warning(
            request, "لا يمكن تطبيق هذا الإجراء على الشكوى في الحالة الحالية"
        )
        return redirect("complaints:complaint_detail", pk=pk)

    # تحديث حالة الشكوى إلى محلولة
    old_status = complaint.status
    complaint.status = "resolved"
    complaint.save()

    # إنشاء سجل تحديث
    ComplaintUpdate.objects.create(
        complaint=complaint,
        update_type="status_change",
        title="تأكيد حل الشكوى",
        description=f"تم تأكيد حل الشكوى بواسطة {request.user.get_full_name() or request.user.username}",
        old_status=old_status,
        new_status="resolved",
        created_by=request.user,
        is_visible_to_customer=True,
    )

    messages.success(request, f"تم تأكيد حل الشكوى رقم {complaint.complaint_number}")
    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def complaint_add_attachment(request, pk):
    """إضافة مرفق للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        form = ComplaintAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.complaint = complaint
            attachment.uploaded_by = request.user
            attachment.save()

            messages.success(request, "تم إضافة المرفق بنجاح")
            return redirect("complaints:complaint_detail", pk=pk)

    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def customer_rating(request, pk):
    """تقييم العميل للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        form = ComplaintCustomerRatingForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save()

            # إنشاء تحديث
            rating_text = dict(Complaint.RATING_CHOICES)[complaint.customer_rating]
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type="customer_response",
                title=f"تقييم العميل: {rating_text}",
                description=complaint.customer_feedback or "تم تقييم الخدمة",
                created_by=request.user,
                is_visible_to_customer=True,
            )

            messages.success(request, "تم حفظ تقييمك بنجاح")
            return redirect("complaints:complaint_detail", pk=pk)

    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def start_action_on_escalated_complaint(request, pk):
    """بدء الإجراء على الشكوى المصعدة (إيقاف التصعيد)"""
    complaint = get_object_or_404(Complaint, pk=pk)

    # التحقق من أن الشكوى في حالة مصعدة
    if complaint.status != "escalated":
        messages.warning(
            request,
            "لا يمكن تطبيق هذا الإجراء - الحالة الحالية: "
            + complaint.get_status_display(),
        )
        return redirect("complaints:complaint_detail", pk=pk)

    # تحديث حالة الشكوى إلى قيد المعالجة
    old_status = complaint.status
    complaint.status = "in_progress"

    # تعيين الشكوى للمستخدم الحالي إذا لم تكن مُعيّنة
    if not complaint.assigned_to:
        complaint.assigned_to = request.user

    complaint.save()

    # إنشاء سجل تحديث
    ComplaintUpdate.objects.create(
        complaint=complaint,
        update_type="status_change",
        title="بدء الإجراء على الشكوى المصعدة",
        description=f'تم بدء الإجراء من قبل {request.user.get_full_name() or request.user.username}\nتم تغيير الحالة من "مصعدة" إلى "قيد المعالجة"',
        old_status=old_status,
        new_status="in_progress",
        created_by=request.user,
        is_visible_to_customer=True,
    )

    messages.success(
        request,
        f"تم بدء الإجراء على الشكوى المصعدة رقم {complaint.complaint_number} بنجاح",
    )
    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def close_complaint(request, pk):
    """إغلاق الشكوى بعد التقييم"""
    complaint = get_object_or_404(Complaint, pk=pk)

    # التحقق من صلاحية المستخدم لإغلاق الشكوى
    if not complaint.can_be_closed_by_user(request.user):
        messages.error(
            request,
            "ليس لديك صلاحية لإغلاق هذه الشكوى. فقط منشئ الشكوى أو المدراء يمكنهم إغلاقها.",
        )
        return redirect("complaints:complaint_detail", pk=pk)

    # التحقق من أن الشكوى محلولة
    if complaint.status != "resolved":
        messages.warning(request, "لا يمكن إغلاق الشكوى - يجب أن تكون محلولة أولاً")
        return redirect("complaints:complaint_detail", pk=pk)

    # تحديث حالة الشكوى إلى مغلقة
    old_status = complaint.status
    complaint.status = "closed"
    complaint.closed_at = timezone.now()
    complaint.closed_by = request.user
    complaint.save()

    # إنشاء سجل تحديث
    ComplaintUpdate.objects.create(
        complaint=complaint,
        update_type="status_change",
        title="إغلاق الشكوى",
        description=f"تم إغلاق الشكوى نهائياً بواسطة {request.user.get_full_name() or request.user.username}",
        old_status=old_status,
        new_status="closed",
        created_by=request.user,
        is_visible_to_customer=True,
    )

    messages.success(
        request, f"تم إغلاق الشكوى رقم {complaint.complaint_number} نهائياً"
    )
    return redirect("complaints:complaint_detail", pk=pk)


@login_required
def customer_complaints(request, customer_id):
    """شكاوى عميل معين"""
    customer = get_object_or_404(Customer, pk=customer_id)

    complaints = (
        Complaint.objects.filter(customer=customer)
        .select_related("complaint_type", "assigned_to")
        .order_by("-created_at")
    )

    # تطبيق ترقيم الصفحات
    paginator = Paginator(complaints, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "customer": customer,
        "complaints": page_obj,
        "page_obj": page_obj,
    }

    return render(request, "complaints/customer_complaints.html", context)


@login_required
def complaints_statistics(request):
    """إحصائيات الشكاوى"""
    # إحصائيات عامة
    stats = {
        "total": Complaint.objects.count(),
        "new": Complaint.objects.filter(status="new").count(),
        "in_progress": Complaint.objects.filter(status="in_progress").count(),
        "resolved": Complaint.objects.filter(status="resolved").count(),
        "overdue": Complaint.objects.filter(status="overdue").count(),
    }

    # إحصائيات حسب النوع
    by_type = list(
        Complaint.objects.values("complaint_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # إحصائيات حسب الشهر (آخر 12 شهر)
    from django.db.models.functions import TruncMonth

    by_month = list(
        Complaint.objects.filter(created_at__gte=timezone.now() - timedelta(days=365))
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    context = {
        "stats": stats,
        "by_type": by_type,
        "by_month": by_month,
    }

    return render(request, "complaints/statistics.html", context)


@login_required
@require_http_methods(["POST"])
def bulk_action(request):
    """الإجراءات المجمعة على الشكاوى"""
    form = ComplaintBulkActionForm(request.POST)
    complaint_ids = request.POST.getlist("complaint_ids")

    if not complaint_ids:
        messages.error(request, "يرجى اختيار شكاوى للتطبيق عليها")
        return redirect("complaints:complaint_list")

    if form.is_valid():
        complaints = Complaint.objects.filter(id__in=complaint_ids)
        action = form.cleaned_data["action"]

        if action == "assign" and form.cleaned_data["assigned_to"]:
            # استخدام save() بدلاً من update() لاستدعاء signals
            assigned_to = form.cleaned_data["assigned_to"]
            count = 0
            for complaint in complaints:
                complaint.assigned_to = assigned_to
                complaint._changed_by = request.user
                complaint.save()
                count += 1
            messages.success(request, f"تم تعيين المسؤول لـ {count} شكوى")

        elif action == "change_status" and form.cleaned_data["status"]:
            complaints.update(status=form.cleaned_data["status"])
            messages.success(request, f"تم تغيير حالة {complaints.count()} شكوى")

        elif action == "change_priority" and form.cleaned_data["priority"]:
            complaints.update(priority=form.cleaned_data["priority"])
            messages.success(request, f"تم تغيير أولوية {complaints.count()} شكوى")

        else:
            messages.error(request, "إجراء غير صحيح")

    return redirect("complaints:complaint_list")


def complaints_analysis(request):
    """تحليل الشكاوى وطرق الحل"""
    from datetime import timedelta

    from django.db.models import Avg, Count, F, Q
    from django.db.models.functions import TruncMonth

    # الحصول على الفترة الزمنية من الطلب
    period = request.GET.get("period", "6months")

    # تحديد تاريخ البداية حسب الفترة
    end_date = timezone.now()
    if period == "1month":
        start_date = end_date - timedelta(days=30)
    elif period == "3months":
        start_date = end_date - timedelta(days=90)
    elif period == "6months":
        start_date = end_date - timedelta(days=180)
    elif period == "1year":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=180)  # افتراضي 6 أشهر

    # الشكاوى في الفترة المحددة
    complaints_in_period = Complaint.objects.filter(
        created_at__gte=start_date, created_at__lte=end_date
    )

    # الشكاوى المحلولة فقط
    resolved_complaints = complaints_in_period.filter(status="resolved")

    # إحصائيات عامة
    total_complaints = complaints_in_period.count()
    total_resolved = resolved_complaints.count()
    resolution_rate = (
        (total_resolved / total_complaints * 100) if total_complaints > 0 else 0
    )

    # تحليل طرق الحل
    resolution_methods_stats = (
        resolved_complaints.values("resolution_method__name")
        .annotate(
            count=Count("id"),
            avg_resolution_time=Avg(F("resolved_at") - F("created_at")),
        )
        .order_by("-count")
    )

    # تحويل وقت الحل إلى ساعات
    for method in resolution_methods_stats:
        if method["avg_resolution_time"]:
            method["avg_resolution_hours"] = (
                method["avg_resolution_time"].total_seconds() / 3600
            )
        else:
            method["avg_resolution_hours"] = 0

    # تحليل الشكاوى حسب النوع وطريقة الحل
    type_resolution_analysis = (
        resolved_complaints.values("complaint_type__name", "resolution_method__name")
        .annotate(count=Count("id"))
        .order_by("complaint_type__name", "-count")
    )

    # تحليل الشكاوى حسب الشهر
    monthly_analysis = (
        complaints_in_period.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total=Count("id"),
            resolved=Count("id", filter=Q(status="resolved")),
            escalated=Count("id", filter=Q(status="escalated")),
            overdue=Count("id", filter=Q(status="overdue")),
        )
        .order_by("month")
    )

    # أكثر طرق الحل فعالية (حسب معدل رضا العملاء)
    customer_satisfaction = (
        resolved_complaints.filter(customer_rating__isnull=False)
        .values("resolution_method__name")
        .annotate(avg_rating=Avg("customer_rating"), count=Count("id"))
        .filter(count__gte=3)
        .order_by("-avg_rating")
    )  # فقط الطرق التي استخدمت 3 مرات على الأقل

    # أسرع طرق الحل
    fastest_methods = (
        resolved_complaints.filter(resolution_method__isnull=False)
        .values("resolution_method__name")
        .annotate(avg_time=Avg(F("resolved_at") - F("created_at")), count=Count("id"))
        .filter(count__gte=3)
        .order_by("avg_time")[:5]
    )

    # تحويل الوقت إلى ساعات
    for method in fastest_methods:
        if method["avg_time"]:
            method["avg_hours"] = method["avg_time"].total_seconds() / 3600
        else:
            method["avg_hours"] = 0

    context = {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "total_complaints": total_complaints,
        "total_resolved": total_resolved,
        "resolution_rate": round(resolution_rate, 1),
        "resolution_methods_stats": resolution_methods_stats,
        "type_resolution_analysis": type_resolution_analysis,
        "monthly_analysis": monthly_analysis,
        "customer_satisfaction": customer_satisfaction,
        "fastest_methods": fastest_methods,
    }

    return render(request, "complaints/analysis.html", context)


@login_required
def notifications_list(request):
    """قائمة إشعارات الشكاوى للمستخدم مع إحصائيات وفلاتر متقدمة."""
    try:
        # استخدام نظام الإشعارات المخصص
        from django.contrib.contenttypes.models import ContentType

        from notifications.models import Notification

        # الحصول على إشعارات الشكاوى للمستخدم الحالي
        complaint_content_type = ContentType.objects.get_for_model(Complaint)
        base_queryset = Notification.objects.filter(
            visible_to=request.user, content_type=complaint_content_type
        ).order_by("-created_at")

        # حساب الإحصائيات
        total_notifications = base_queryset.count()

        # الإشعارات غير المقروءة (التي لا يوجد لها سجل قراءة أو مقروءة كـ False)
        unread_notifications = base_queryset.exclude(
            visibility_records__user=request.user, visibility_records__is_read=True
        ).count()

        # الإشعارات العاجلة (priority عالي)
        urgent_notifications = base_queryset.filter(priority="high").count()

        # إشعارات اليوم
        today_notifications = base_queryset.filter(
            created_at__date=timezone.now().date()
        ).count()

        stats = {
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications,
            "urgent_notifications": urgent_notifications,
            "today_notifications": today_notifications,
        }

    except Exception as e:
        # في حالة حدوث خطأ، نستخدم queryset فارغ
        base_queryset = Notification.objects.none()
        stats = {
            "total_notifications": 0,
            "unread_notifications": 0,
            "urgent_notifications": 0,
            "today_notifications": 0,
        }

    # Apply filters
    queryset = base_queryset
    notification_type = request.GET.get("notification_type")
    status = request.GET.get("status")
    date_range = request.GET.get("date_range")

    if notification_type:
        priority_map = {"urgent": "high", "warning": "medium", "info": "low"}
        if notification_type in priority_map:
            queryset = queryset.filter(priority=priority_map[notification_type])

    if status:
        if status == "read":
            queryset = queryset.filter(is_read=True)
        elif status == "unread":
            queryset = queryset.filter(is_read=False)

    if date_range:
        today = timezone.now().date()
        if date_range == "today":
            queryset = queryset.filter(created_at__date=today)
        elif date_range == "week":
            start_of_week = today - timedelta(days=today.weekday())
            queryset = queryset.filter(created_at__date__gte=start_of_week)
        elif date_range == "month":
            queryset = queryset.filter(
                created_at__month=today.month, created_at__year=today.year
            )

    # Order and paginate
    ordered_queryset = queryset.order_by("-created_at")
    paginator = Paginator(ordered_queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Add notification_type for template styling
    priority_to_type_map = {"high": "urgent", "medium": "warning", "low": "info"}
    for notification in page_obj:
        notification.notification_type = priority_to_type_map.get(
            notification.priority, "info"
        )

    context = {
        "notifications": page_obj,
        "page_obj": page_obj,
        "stats": stats,
        "page_title": "الإشعارات",
    }

    return render(request, "complaints/notifications_list.html", context)


@login_required
@require_http_methods(["POST"])
def mark_notification_as_read(request, notification_id):
    """Marks a single notification as read."""
    notification = get_object_or_404(
        Notification, pk=notification_id, target_users=request.user
    )
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return JsonResponse({"status": "success"})


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_as_read(request):
    """Marks all unread notifications for the user as read."""
    Notification.objects.filter(target_users=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return JsonResponse(
        {"status": "success", "message": "All notifications marked as read."}
    )


@login_required
@require_http_methods(["POST"])
def delete_notification(request, notification_id):
    """Deletes a single notification."""
    notification = get_object_or_404(
        Notification, pk=notification_id, target_users=request.user
    )
    notification.delete()
    return JsonResponse({"status": "success"})


@login_required
@require_http_methods(["POST"])
def notification_bulk_action(request):
    """Handles bulk actions for notifications (mark as read, delete)."""
    action = request.POST.get("action")
    notification_ids = request.POST.getlist("notification_ids[]")

    if not action or not notification_ids:
        return JsonResponse(
            {"status": "error", "message": "Missing action or notification IDs."},
            status=400,
        )

    queryset = Notification.objects.filter(
        pk__in=notification_ids, target_users=request.user
    )

    if action == "mark_as_read":
        updated_count = queryset.update(is_read=True, read_at=timezone.now())
        message = f"{updated_count} notifications marked as read."
    elif action == "delete":
        deleted_count, _ = queryset.delete()
        message = f"{deleted_count} notifications deleted."
    else:
        return JsonResponse(
            {"status": "error", "message": "Invalid action."}, status=400
        )

    return JsonResponse({"status": "success", "message": message})


def ajax_complaint_stats(request):
    """
    AJAX endpoint to get complaint statistics
    Returns JSON response with complaint statistics
    """
    if not request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": "Invalid request"}, status=400)

    # Get filter parameters
    status = request.GET.get("status")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    # Base queryset
    queryset = Complaint.objects.all()

    # Apply filters
    if status:
        queryset = queryset.filter(status=status)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    # Get statistics
    stats = {
        "total": queryset.count(),
        "new": queryset.filter(status="new").count(),
        "in_progress": queryset.filter(status="in_progress").count(),
        "resolved": queryset.filter(status="resolved").count(),
        "overdue": queryset.filter(status="overdue").count(),
        "by_type": list(
            queryset.values("complaint_type__name").annotate(count=Count("id"))
        ),
        "by_status": list(queryset.values("status").annotate(count=Count("id"))),
        "by_date": list(
            queryset.extra(select={"date": "date(created_at)"})
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        ),
    }

    return JsonResponse(stats, safe=False)


class ComplaintEvaluationReportView(LoginRequiredMixin, TemplateView):
    """تقرير تقييمات الشكاوى"""

    template_name = "complaints/evaluation_report.html"

    def dispatch(self, request, *args, **kwargs):
        # التحقق من صلاحيات الوصول للتقارير
        if not (
            request.user.is_superuser
            or request.user.groups.filter(
                name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
            ).exists()
        ):
            messages.error(request, "ليس لديك صلاحية للوصول إلى تقارير التقييمات")
            return redirect("complaints:complaint_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات التقييمات العامة
        evaluations = ComplaintEvaluation.objects.select_related("complaint")

        if evaluations.exists():
            # متوسط التقييمات
            avg_stats = evaluations.aggregate(
                avg_overall=Avg("overall_rating"),
                avg_response_time=Avg("response_time_rating"),
                avg_solution_quality=Avg("solution_quality_rating"),
                avg_staff_behavior=Avg("staff_behavior_rating"),
                total_evaluations=Count("id"),
            )

            # توزيع التقييمات
            rating_distribution = (
                evaluations.values("overall_rating")
                .annotate(count=Count("id"))
                .order_by("overall_rating")
            )

            # التقييمات حسب نوع الشكوى
            by_complaint_type = (
                evaluations.values("complaint__complaint_type__name")
                .annotate(count=Count("id"), avg_rating=Avg("overall_rating"))
                .order_by("-avg_rating")
            )

            # التقييمات الحديثة
            recent_evaluations = evaluations.order_by("-evaluation_date")[:10]

            # نسبة التوصية
            recommendation_stats = evaluations.aggregate(
                total_responses=Count("would_recommend"),
                positive_recommendations=Count(
                    "would_recommend", filter=Q(would_recommend=True)
                ),
                negative_recommendations=Count(
                    "would_recommend", filter=Q(would_recommend=False)
                ),
            )

            if recommendation_stats["total_responses"] > 0:
                recommendation_percentage = (
                    recommendation_stats["positive_recommendations"]
                    / recommendation_stats["total_responses"]
                    * 100
                )
            else:
                recommendation_percentage = 0

            context.update(
                {
                    "avg_stats": avg_stats,
                    "rating_distribution": list(rating_distribution),
                    "by_complaint_type": list(by_complaint_type),
                    "recent_evaluations": recent_evaluations,
                    "recommendation_stats": recommendation_stats,
                    "recommendation_percentage": round(recommendation_percentage, 1),
                    "has_data": True,
                }
            )
        else:
            context["has_data"] = False

        return context


@login_required
def create_evaluation(request, complaint_id):
    """إنشاء تقييم للشكوى"""
    complaint = get_object_or_404(Complaint, pk=complaint_id)

    # التحقق من أن الشكوى محلولة وبحاجة تقييم
    if complaint.status != "pending_evaluation":
        messages.error(request, "هذه الشكوى غير متاحة للتقييم")
        return redirect("complaints:complaint_detail", pk=complaint.pk)

    # التحقق من عدم وجود تقييم مسبق
    if hasattr(complaint, "evaluation"):
        messages.info(request, "تم تقييم هذه الشكوى مسبقاً")
        return redirect("complaints:complaint_detail", pk=complaint.pk)

    if request.method == "POST":
        try:
            # إنشاء التقييم
            evaluation = ComplaintEvaluation.objects.create(
                complaint=complaint,
                overall_rating=int(request.POST.get("overall_rating")),
                response_time_rating=int(request.POST.get("response_time_rating")),
                solution_quality_rating=int(
                    request.POST.get("solution_quality_rating")
                ),
                staff_behavior_rating=int(request.POST.get("staff_behavior_rating")),
                positive_feedback=request.POST.get("positive_feedback", ""),
                negative_feedback=request.POST.get("negative_feedback", ""),
                suggestions=request.POST.get("suggestions", ""),
                would_recommend=request.POST.get("would_recommend") == "true",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            # تحديث الشكوى لتصبح قابلة للإغلاق
            messages.success(request, "تم حفظ التقييم بنجاح. شكراً لك!")

            # إنشاء تحديث للشكوى
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type="customer_response",
                title="تم إضافة تقييم العميل",
                description=f"تم تقييم الشكوى بمتوسط {evaluation.average_rating:.1f}/5",
                created_by=request.user,
                is_visible_to_customer=True,
            )

            return redirect("complaints:complaint_detail", pk=complaint.pk)

        except (ValueError, TypeError) as e:
            messages.error(request, "حدث خطأ في البيانات المدخلة")

    context = {"complaint": complaint}

    return render(request, "complaints/create_evaluation.html", context)


# AJAX Views for smart customer selection and data loading
@login_required
def search_customers(request):
    """البحث الذكي عن العملاء"""
    print("===== بدء البحث عن العملاء =====")

    query = request.GET.get("q", "")
    print(f"مصطلح البحث: '{query}'")
    print(f"طول المصطلح: {len(query)}")

    if len(query) < 2:
        print("مصطلح البحث قصير جداً - إرجاع نتائج فارغة")
        return JsonResponse({"results": []})

    try:
        print("جاري البحث في قاعدة البيانات...")
        customers = Customer.objects.filter(
            Q(name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        ).select_related("branch")[:10]

        print(f"تم العثور على {customers.count()} عميل")

        results = []
        for customer in customers:
            customer_data = {
                "id": customer.id,
                "text": f"{customer.name} - {customer.phone}",
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email or "",
                "address": customer.address or "",
                "branch": customer.branch.name if customer.branch else "",
            }
            results.append(customer_data)
            print(f"  - عميل: {customer.name} (ID: {customer.id})")

        print(f"===== انتهاء البحث - تم إرجاع {len(results)} نتيجة =====")
        return JsonResponse({"results": results})

    except Exception as e:
        print("===== خطأ في البحث عن العملاء =====")
        print(f"نوع الخطأ: {type(e).__name__}")
        print(f"رسالة الخطأ: {str(e)}")
        return JsonResponse(
            {"error": f"حدث خطأ في البحث: {str(e)}", "results": []}, status=500
        )


@login_required
def get_customer_info(request, customer_id):
    """جلب معلومات العميل"""
    try:
        customer = Customer.objects.select_related("branch").get(pk=customer_id)

        data = {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email or "غير محدد",
            "address": customer.address or "غير محدد",
            "branch": customer.branch.name if customer.branch else "غير محدد",
            "customer_type": (
                customer.get_customer_type_display()
                if hasattr(customer, "customer_type")
                else "غير محدد"
            ),
            "status": (
                customer.get_status_display() if hasattr(customer, "status") else "نشط"
            ),
        }

        return JsonResponse(data)
    except Customer.DoesNotExist:
        return JsonResponse({"error": "العميل غير موجود"}, status=404)


@login_required
def get_customer_orders(request, customer_id):
    """جلب طلبات العميل مع رسائل تصحيح"""
    print(f"===== بدء جلب طلبات العميل {customer_id} =====")

    try:
        print(f"البحث عن العميل برقم: {customer_id}")
        customer = Customer.objects.get(pk=customer_id)
        print(f"تم العثور على العميل: {customer.name}")

        print("جاري جلب طلبات العميل...")
        orders = (
            Order.objects.filter(customer=customer)
            .select_related("salesperson", "created_by")
            .order_by("-created_at")[:20]
        )

        print(f"تم العثور على {orders.count()} طلب")

        orders_data = []
        for order in orders:
            print(f"معالجة الطلب {order.id}:")

            # معلومات البائع
            salesperson_name = "غير محدد"
            if order.salesperson:
                salesperson_name = order.salesperson.name
                print(f"  البائع: {salesperson_name}")
            elif hasattr(order, "salesperson_name_raw") and order.salesperson_name_raw:
                salesperson_name = order.salesperson_name_raw
                print(f"  البائع (خام): {salesperson_name}")
            else:
                print("  البائع: غير محدد")

            # معلومات منشئ الطلب
            created_by_name = "غير محدد"
            if hasattr(order, "created_by") and order.created_by:
                first_name = order.created_by.first_name
                last_name = order.created_by.last_name
                full_name = f"{first_name} {last_name}"
                created_by_name = full_name.strip()
                if not created_by_name:
                    created_by_name = order.created_by.username
                print(f"  منشئ الطلب: {created_by_name}")
            else:
                print("  منشئ الطلب: غير محدد")

            # حساب المبلغ الإجمالي
            total_amount = 0
            if hasattr(order, "total_amount") and order.total_amount:
                total_amount = float(order.total_amount)
                print(f"  المبلغ الإجمالي: {total_amount}")
            else:
                print("  المبلغ الإجمالي: 0")

            # حالة الطلب
            order_status = "غير محدد"
            if hasattr(order, "status"):
                order_status = order.get_status_display()
                print(f"  حالة الطلب: {order_status}")
            else:
                print("  حالة الطلب: غير محدد")

            # تاريخ الإنشاء
            created_date = ""
            if order.created_at:
                created_date = order.created_at.strftime("%Y-%m-%d")
                print(f"  تاريخ الإنشاء: {created_date}")

            # وصف الطلب
            description = (
                getattr(order, "description", "")
                or getattr(order, "notes", "")
                or "لا يوجد وصف"
            )
            print(f"  الوصف: {description[:50]}...")

            order_data = {
                "id": order.id,
                "order_number": getattr(order, "order_number", f"طلب #{order.id}"),
                "total_amount": total_amount,
                "status": order_status,
                "created_at": created_date,
                "description": description,
                "salesperson": salesperson_name,
                "created_by": created_by_name,
            }
            orders_data.append(order_data)

        print(f"===== تم جلب {len(orders_data)} طلب بنجاح =====")
        return JsonResponse({"orders": orders_data})

    except Customer.DoesNotExist:
        print(f"===== خطأ: العميل {customer_id} غير موجود =====")
        return JsonResponse({"error": "العميل غير موجود"}, status=404)
    except Exception as e:
        print("===== خطأ في جلب طلبات العميل =====")
        print(f"نوع الخطأ: {type(e).__name__}")
        print(f"رسالة الخطأ: {str(e)}")
        return JsonResponse({"error": f"حدث خطأ في جلب الطلبات: {str(e)}"}, status=500)


@login_required
def get_complaint_type_fields(request, type_id):
    """جلب الحقول المطلوبة لنوع الشكوى مع مراعاة الصلاحيات وإعدادات لوحة التحكم"""
    try:
        complaint_type = get_object_or_404(ComplaintType, id=type_id)

        # قائمة الموظفين المتاحين للتعيين بناءً على إعدادات نوع الشكوى والصلاحيات
        available_staff = []

        # أولاً: التحقق من الموظفين المسؤولين المحددين في نوع الشكوى
        if complaint_type.responsible_staff.exists():
            # استخدام الموظفين المحددين مسبقاً في نوع الشكوى (بغض النظر عن الصلاحيات)
            # لأن المدير حددهم بشكل صريح في لوحة التحكم
            responsible_staff = complaint_type.responsible_staff.filter(
                is_active=True
            ).distinct()

            for user in responsible_staff:
                available_staff.append(
                    {
                        "id": user.id,
                        "name": user.get_full_name() or user.username,
                        "username": user.username,
                        "is_default": user == complaint_type.default_assignee,
                        "department": (
                            user.departments.first().name
                            if user.departments.exists()
                            else None
                        ),
                        "source": "responsible_staff",  # لتتبع مصدر المستخدم
                    }
                )

        # ثانياً: إذا لم يكن هناك موظفين محددين، استخدم موظفي القسم المسؤول
        elif complaint_type.responsible_department:
            from accounts.models import User

            # جلب جميع موظفي القسم النشطين
            dept_staff = User.objects.filter(
                departments=complaint_type.responsible_department, is_active=True
            ).distinct()

            for user in dept_staff:
                # التحقق من الصلاحيات (اختياري للموظفين في القسم المحدد)
                has_permissions = (
                    hasattr(user, "complaint_permissions")
                    and user.complaint_permissions.can_be_assigned_complaints
                )

                available_staff.append(
                    {
                        "id": user.id,
                        "name": user.get_full_name() or user.username,
                        "username": user.username,
                        "is_default": user == complaint_type.default_assignee,
                        "department": complaint_type.responsible_department.name,
                        "source": "department_staff",
                        "has_permissions": has_permissions,
                    }
                )

        # ثالثاً: إذا لم يكن هناك قسم محدد، استخدم المستخدمين المؤهلين فقط
        else:
            from accounts.models import User

            # في هذه الحالة، نتطلب وجود صلاحيات صريحة
            all_qualified_staff = User.objects.filter(
                is_active=True,
                complaint_permissions__can_be_assigned_complaints=True,
                complaint_permissions__is_active=True,
            ).distinct()

            for user in all_qualified_staff:
                available_staff.append(
                    {
                        "id": user.id,
                        "name": user.get_full_name() or user.username,
                        "username": user.username,
                        "is_default": user == complaint_type.default_assignee,
                        "department": (
                            user.departments.first().name
                            if user.departments.exists()
                            else None
                        ),
                        "source": "qualified_staff",
                        "has_permissions": True,
                    }
                )

        # قائمة الأقسام المتاحة (فقط الأقسام النشطة)
        departments = []
        all_departments = Department.objects.filter(is_active=True)
        for dept in all_departments:
            departments.append(
                {
                    "id": dept.id,
                    "name": dept.name,
                    "is_default": dept == complaint_type.responsible_department,
                }
            )

        # تحديد القسم الافتراضي
        default_dept = None
        default_assignee = None
        if complaint_type.responsible_department:
            default_dept = complaint_type.responsible_department.id
        if complaint_type.default_assignee:
            default_assignee = complaint_type.default_assignee.id

        return JsonResponse(
            {
                "success": True,
                "name": complaint_type.name,
                "description": complaint_type.description or "لا يوجد وصف",
                "staff": available_staff,
                "departments": departments,
                "default_department": default_dept,
                "default_assignee": default_assignee,
                "default_priority": complaint_type.default_priority,
                "default_deadline_hours": complaint_type.default_deadline_hours,
                "business_hours_start": complaint_type.business_hours_start.strftime(
                    "%H:%M"
                ),
                "business_hours_end": complaint_type.business_hours_end.strftime(
                    "%H:%M"
                ),
                "working_days": (
                    complaint_type.working_days.split(",")
                    if complaint_type.working_days
                    else []
                ),
                "expected_resolution_hours": getattr(
                    complaint_type,
                    "expected_resolution_hours",
                    complaint_type.default_deadline_hours,
                ),
            }
        )

    except ComplaintType.DoesNotExist:
        return JsonResponse({"error": "نوع الشكوى غير موجود"}, status=404)


@login_required
def get_department_staff(request, department_id):
    """جلب موظفي قسم معين"""
    try:
        from accounts.models import Department, User

        department = get_object_or_404(Department, id=department_id)

        # جلب موظفي القسم
        staff_users = User.objects.filter(
            departments=department, is_active=True
        ).values("id", "first_name", "last_name", "username")

        staff_list = []
        for user in staff_users:
            full_name = f"{user['first_name']} {user['last_name']}".strip()
            if not full_name:
                full_name = user["username"]

            staff_list.append({"id": user["id"], "name": full_name})

        return JsonResponse({"staff": staff_list, "department_name": department.name})

    except Department.DoesNotExist:
        return JsonResponse({"error": "القسم غير موجود"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView

from .models import Complaint, ComplaintType

# Import export functions
from .utils.export import export_complaints_to_csv, export_complaints_to_excel


class ExportForm(forms.Form):
    """نموذج تصدير الشكاوى"""

    EXPORT_CHOICES = [
        ("csv", "تصدير إلى CSV"),
        ("excel", "تصدير إلى Excel"),
    ]

    export_format = forms.ChoiceField(
        choices=EXPORT_CHOICES, label="صيغة التصدير", widget=forms.RadioSelect
    )

    date_from = forms.DateField(
        required=False, label="من تاريخ", widget=forms.DateInput(attrs={"type": "date"})
    )

    date_to = forms.DateField(
        required=False,
        label="إلى تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    status = forms.MultipleChoiceField(
        choices=Complaint.STATUS_CHOICES,
        required=False,
        label="الحالة",
        widget=forms.CheckboxSelectMultiple,
    )

    complaint_type = forms.ModelMultipleChoiceField(
        queryset=ComplaintType.objects.filter(is_active=True),
        required=False,
        label="نوع الشكوى",
        widget=forms.CheckboxSelectMultiple,
    )

    priority = forms.MultipleChoiceField(
        choices=Complaint.PRIORITY_CHOICES,
        required=False,
        label="الأولوية",
        widget=forms.CheckboxSelectMultiple,
    )


@method_decorator(permission_required("complaints.view_complaint"), name="dispatch")
class ExportComplaintsView(FormView):
    """صفحة تصدير الشكاوى"""

    template_name = "complaints/export.html"
    form_class = ExportForm
    success_url = reverse_lazy("complaints:export_complaints")

    def form_valid(self, form):
        queryset = Complaint.objects.all()

        # تطبيق الفلاتر
        if form.cleaned_data["date_from"]:
            queryset = queryset.filter(
                created_at__date__gte=form.cleaned_data["date_from"]
            )

        if form.cleaned_data["date_to"]:
            queryset = queryset.filter(
                created_at__date__lte=form.cleaned_data["date_to"]
            )

        if form.cleaned_data["status"]:
            queryset = queryset.filter(status__in=form.cleaned_data["status"])

        if form.cleaned_data["complaint_type"]:
            queryset = queryset.filter(
                complaint_type__in=form.cleaned_data["complaint_type"]
            )

        if form.cleaned_data["priority"]:
            queryset = queryset.filter(priority__in=form.cleaned_data["priority"])

        # التأكد من وجود نتائج
        if not queryset.exists():
            messages.warning(self.request, "لا توجد شكاوى تطابق معايير البحث")
            return redirect("complaints:export_complaints")

        # تصدير البيانات
        if form.cleaned_data["export_format"] == "csv":
            return export_complaints_to_csv(queryset=queryset)
        else:
            return export_complaints_to_excel(queryset=queryset)
