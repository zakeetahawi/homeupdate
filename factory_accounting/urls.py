"""
Factory Accounting URLs
مسارات حسابات المصنع
"""

from django.urls import path

from . import reports_views, views

app_name = "factory_accounting"

urlpatterns = [
    # API endpoints
    path(
        "api/card/<int:manufacturing_order_id>/",
        views.get_factory_card_data,
        name="get_card_data",
    ),
    path(
        "api/card/<int:factory_card_id>/save/",
        views.save_factory_card_splits,
        name="save_splits",
    ),
    path("api/tailors/", views.get_tailors_list, name="tailors_list"),
    path("api/bulk-pay/", views.api_bulk_pay_cards, name="bulk_pay"),
    # Reports
    path("reports/", reports_views.production_reports, name="reports"),
    path(
        "reports/export/", reports_views.export_production_report, name="export_report"
    ),
]
