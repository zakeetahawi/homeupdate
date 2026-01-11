from django.urls import path

from . import api_views, views
from .orders_report_views import orders_report_view

app_name = "reports"

# Main urlpatterns for reports app. Include seller-activity routes alongside the standard CRUD/dashboard routes.
urlpatterns = [
    # Production Reports - تقارير الإنتاج
    path("production/", views.production_reports_list, name="production_reports_list"),
    # Orders Report - تقرير الطلبات
    path("orders/", orders_report_view, name="orders_report"),
    # Seller activity report index/detail/csv
    path(
        "seller-activity/",
        views.seller_customer_activity_index,
        name="seller_customer_activity_index",
    ),
    path(
        "seller-activity/<int:report_id>/",
        views.seller_customer_activity_view,
        name="seller_customer_activity",
    ),
    path(
        "seller-activity/<int:report_id>/export/csv/",
        views.seller_customer_activity_export_csv,
        name="seller_customer_activity_csv",
    ),
    # Regular views
    path("", views.ReportDashboardView.as_view(), name="dashboard"),
    path("list/", views.ReportListView.as_view(), name="report_list"),
    path("create/", views.ReportCreateView.as_view(), name="report_create"),
    path("<int:pk>/", views.ReportDetailView.as_view(), name="report_detail"),
    path("<int:pk>/update/", views.ReportUpdateView.as_view(), name="report_update"),
    path("<int:pk>/delete/", views.ReportDeleteView.as_view(), name="report_delete"),
    path("<int:pk>/save-result/", views.save_report_result, name="save_report_result"),
    path(
        "<int:pk>/schedule/",
        views.ReportScheduleCreateView.as_view(),
        name="schedule_create",
    ),
    path(
        "schedule/<int:pk>/update/",
        views.ReportScheduleUpdateView.as_view(),
        name="schedule_update",
    ),
    path(
        "schedule/<int:pk>/delete/",
        views.ReportScheduleDeleteView.as_view(),
        name="schedule_delete",
    ),
    # API endpoints
    path(
        "api/analytics/data/", api_views.get_analytics_data, name="api_analytics_data"
    ),
    path(
        "api/analytics/latest/",
        api_views.get_latest_analytics,
        name="api_latest_analytics",
    ),
    path(
        "api/kpi/<str:kpi_type>/details/",
        api_views.get_kpi_details,
        name="api_kpi_details",
    ),
]
