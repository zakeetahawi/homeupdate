from django.urls import path

from . import views

app_name = "board_dashboard"

from . import api_views
from .views import BoardDashboardView

urlpatterns = [
    path("", BoardDashboardView.as_view(), name="home"),
    # API Endpoints
    path("api/revenue/", api_views.BoardRevenueAPIView.as_view(), name="api_revenue"),
    path(
        "api/inventory/",
        api_views.BoardInventoryAPIView.as_view(),
        name="api_inventory",
    ),
    path("api/staff/", api_views.BoardStaffAPIView.as_view(), name="api_staff"),
    path("api/finance/", api_views.BoardFinanceAPIView.as_view(), name="api_finance"),
]
