from django.urls import path

from . import views, views_decorator

app_name = "external_sales"

urlpatterns = [
    # Department index
    path("", views.ExternalSalesIndexView.as_view(), name="index"),
    # ── Decorator Engineers Department ──────────────────────
    path(
        "decorator/",
        views_decorator.DecoratorDashboardView.as_view(),
        name="decorator_dashboard",
    ),
    path(
        "decorator/engineers/",
        views_decorator.EngineerListView.as_view(),
        name="engineer_list",
    ),
    path(
        "decorator/engineers/<int:pk>/",
        views_decorator.EngineerDetailView.as_view(),
        name="engineer_detail",
    ),
    path(
        "decorator/engineers/<int:pk>/edit/",
        views_decorator.EngineerProfileEditView.as_view(),
        name="engineer_edit",
    ),
    path(
        "decorator/create-profile/<str:customer_code>/",
        views_decorator.CreateEngineerProfileView.as_view(),
        name="create_profile",
    ),
    # Contact log
    path(
        "decorator/engineers/<int:pk>/contact/add/",
        views_decorator.AddContactLogView.as_view(),
        name="add_contact",
    ),
    path(
        "decorator/engineers/<int:pk>/contact/",
        views_decorator.ContactLogListView.as_view(),
        name="contact_list",
    ),
    # Linking
    path(
        "decorator/engineers/<int:pk>/link-customer/",
        views_decorator.LinkCustomerView.as_view(),
        name="link_customer",
    ),
    path(
        "decorator/engineers/<int:pk>/unlink-customer/<int:link_id>/",
        views_decorator.UnlinkCustomerView.as_view(),
        name="unlink_customer",
    ),
    path(
        "decorator/engineers/<int:pk>/link-order/",
        views_decorator.LinkOrderView.as_view(),
        name="link_order",
    ),
    path(
        "decorator/engineers/<int:pk>/unlink-order/<int:link_id>/",
        views_decorator.UnlinkOrderView.as_view(),
        name="unlink_order",
    ),
    # Materials
    path(
        "decorator/engineers/<int:pk>/materials/",
        views_decorator.MaterialInterestView.as_view(),
        name="materials",
    ),
    # Orders filtered view
    path(
        "decorator/orders/",
        views_decorator.DecoratorOrdersView.as_view(),
        name="decorator_orders",
    ),
    # Commission management
    path(
        "decorator/commissions/",
        views_decorator.CommissionsView.as_view(),
        name="commissions",
    ),
    path(
        "decorator/commissions/<int:pk>/approve/",
        views_decorator.ApproveCommissionView.as_view(),
        name="approve_commission",
    ),
    path(
        "decorator/commissions/<int:pk>/pay/",
        views_decorator.MarkCommissionPaidView.as_view(),
        name="pay_commission",
    ),
    # AJAX endpoints
    path(
        "decorator/api/engineer-search/",
        views_decorator.EngineerSearchAjax.as_view(),
        name="api_engineer_search",
    ),
    path(
        "decorator/api/customer-search/",
        views_decorator.CustomerSearchAjax.as_view(),
        name="api_customer_search",
    ),
    path(
        "decorator/api/designer-customer-search/",
        views_decorator.DesignerCustomerSearchAjax.as_view(),
        name="api_designer_customer_search",
    ),
    path(
        "decorator/api/order-search/",
        views_decorator.OrderSearchAjax.as_view(),
        name="api_order_search",
    ),
    path(
        "decorator/api/find-by-code/",
        views_decorator.FindEngineerByCodeAjax.as_view(),
        name="api_find_engineer_by_code",
    ),
    path(
        "decorator/followups/",
        views_decorator.AllUpcomingFollowupsView.as_view(),
        name="all_followups",
    ),
    path(
        "decorator/contacts/all/",
        views_decorator.AllContactLogsView.as_view(),
        name="all_contacts",
    ),
    path(
        "decorator/api/available-orders/<str:customer_code>/",
        views_decorator.AvailableOrdersAjax.as_view(),
        name="api_available_orders",
    ),
    # Chart AJAX
    path(
        "decorator/api/chart/top-revenue/",
        views_decorator.ChartTopByRevenueAjax.as_view(),
        name="chart_top_revenue",
    ),
    path(
        "decorator/api/chart/top-orders/",
        views_decorator.ChartTopByOrdersAjax.as_view(),
        name="chart_top_orders",
    ),
    path(
        "decorator/api/chart/materials/",
        views_decorator.ChartTopMaterialsAjax.as_view(),
        name="chart_materials",
    ),
    path(
        "decorator/api/chart/monthly-activity/",
        views_decorator.ChartMonthlyActivityAjax.as_view(),
        name="chart_monthly_activity",
    ),
    # Export
    path(
        "decorator/export/engineers/",
        views_decorator.ExportEngineersExcelView.as_view(),
        name="export_engineers",
    ),
    path(
        "decorator/engineers/<int:pk>/export/",
        views_decorator.ExportEngineerFullDataView.as_view(),
        name="export_engineer",
    ),
    path(
        "decorator/commissions/export/",
        views_decorator.ExportCommissionsExcelView.as_view(),
        name="export_commissions",
    ),
    # Import
    path(
        "decorator/import/",
        views_decorator.ImportEngineersExcelView.as_view(),
        name="import_engineers",
    ),
    path(
        "decorator/import/template/",
        views_decorator.DownloadImportTemplateView.as_view(),
        name="import_template",
    ),
]
