from django.db.models import Q
from django.views.generic import TemplateView

from accounts.models import Branch, User
from inventory.models import Warehouse

from .mixins import BoardAccessMixin
from .models import BoardWidgetSettings


class BoardDashboardView(BoardAccessMixin, TemplateView):
    template_name = "board_dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter Options
        context["branches"] = Branch.objects.filter(is_active=True)
        context["warehouses"] = Warehouse.objects.filter(is_active=True)
        # Salespersons: Users with specific permission or group (Sales, Branch Mgr, Region Mgr)
        context["salespersons"] = User.objects.filter(
            Q(is_salesperson=True)
            | Q(is_branch_manager=True)
            | Q(is_region_manager=True)
            | Q(is_sales_manager=True),
            is_active=True,
        ).distinct()

        # Widget Settings
        widgets = BoardWidgetSettings.objects.filter(is_active=True).order_by("order")
        context["widgets"] = {w.name: w for w in widgets}

        # External Sales Summary (lightweight — for overview tab, server-side)
        try:
            from datetime import date, timedelta

            from django.db.models import Sum

            from external_sales.models import (
                DecoratorEngineerProfile,
                EngineerLinkedOrder,
            )

            today = date.today()
            month_start = today.replace(day=1)
            sixty_days_ago = today - timedelta(days=60)

            context["ext_sales_summary"] = {
                "total_decorator_engineers": DecoratorEngineerProfile.objects.count(),
                "active_engineers": DecoratorEngineerProfile.objects.filter(
                    customer__status="active"
                ).count(),
                "no_contact_engineers": DecoratorEngineerProfile.objects.filter(
                    last_contact_date__lt=sixty_days_ago
                ).count(),
                "pending_commissions_value": EngineerLinkedOrder.objects.filter(
                    commission_status="pending"
                ).aggregate(t=Sum("commission_value"))["t"]
                or 0,
                "new_this_month": DecoratorEngineerProfile.objects.filter(
                    created_at__date__gte=month_start
                )
                .select_related("customer", "customer__branch")
                .order_by("-created_at")[:8],
            }
        except Exception:
            context["ext_sales_summary"] = None

        return context
