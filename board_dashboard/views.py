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

        return context
