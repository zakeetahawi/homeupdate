from django.urls import path

from . import views
from .dashboard_view import ImprovedDashboardView

app_name = "manufacturing"

urlpatterns = [
    path("", ImprovedDashboardView.as_view(), name="dashboard"),
    path("orders/", views.ManufacturingOrderListView.as_view(), name="order_list"),
    path(
        "orders/export/excel/",
        views.export_manufacturing_orders,
        name="export_excel",
    ),
    path("orders/vip/", views.VIPOrdersListView.as_view(), name="vip_orders"),
    path(
        "orders/item-status-report/",
        views.ManufacturingItemStatusReportView.as_view(),
        name="item_status_report",
    ),
    path(
        "orders/create/",
        views.ManufacturingOrderCreateView.as_view(),
        name="order_create",
    ),
    path("fabric-receipt/", views.FabricReceiptView.as_view(), name="fabric_receipt"),
    path(
        "receive-item/<int:item_id>/",
        views.receive_fabric_item,
        name="receive_fabric_item",
    ),
    path("get-bag-number-data/", views.get_bag_number_data, name="get_bag_number_data"),
    path(
        "receive-all-items/<int:order_id>/",
        views.receive_all_fabric_items,
        name="receive_all_fabric_items",
    ),
    path(
        "recent-receipts/", views.recent_fabric_receipts, name="recent_fabric_receipts"
    ),
    # URLs باستخدام كود التصنيع
    path(
        "order/<str:manufacturing_code>/",
        views.manufacturing_order_detail_by_code,
        name="order_detail_by_code",
    ),
    path(
        "order/<int:pk>/material-summary/",
        views.material_summary_view,
        name="material_summary_print",
    ),
    # URLs القديمة مع إعادة توجيه
    path(
        "orders/<int:pk>/",
        views.manufacturing_order_detail_redirect,
        name="order_detail",
    ),
    path(
        "orders/<int:pk>/delete/",
        views.ManufacturingOrderDeleteView.as_view(),
        name="order_delete",
    ),
    path("orders/<int:pk>/print/", views.print_manufacturing_order, name="order_print"),
    path(
        "api/update_status/<int:pk>/",
        views.update_order_status,
        name="update_order_status_api",
    ),
    path(
        "api/update_exit_permit/<int:pk>/",
        views.update_exit_permit,
        name="update_exit_permit_api",
    ),
    path(
        "approval/<int:pk>/",
        views.update_approval_status,
        name="update_approval_status",
    ),
    path("send_reply/<int:pk>/", views.send_reply, name="send_reply"),
    path(
        "send_reply_to_rejection_log/<int:log_id>/",
        views.send_reply_to_rejection_log,
        name="send_reply_to_rejection_log",
    ),
    path("order/<int:pk>/details/", views.get_order_details, name="get_order_details"),
    path(
        "re_approve/<int:pk>/",
        views.re_approve_after_reply,
        name="re_approve_after_reply",
    ),
    path(
        "production-line/<int:line_id>/print/",
        views.ProductionLinePrintView.as_view(),
        name="production_line_print",
    ),
    path(
        "production-line/<int:line_id>/print-template/",
        views.ProductionLinePrintTemplateView.as_view(),
        name="production_line_print_template",
    ),
    path(
        "production-line/<int:line_id>/pdf/",
        views.ProductionLinePDFView.as_view(),
        name="production_line_pdf",
    ),
    path(
        "api/change-production-line/<int:pk>/",
        views.ChangeProductionLineView.as_view(),
        name="change_production_line_api",
    ),
    path(
        "api/production-lines/",
        views.get_production_lines_api,
        name="production_lines_api",
    ),
    # نظام استلام الأقمشة
    path("fabric-receipt/", views.FabricReceiptView.as_view(), name="fabric_receipt"),
    path(
        "fabric-receipt/item/<int:item_id>/receive/",
        views.receive_fabric_item,
        name="receive_fabric_item",
    ),
    path(
        "fabric-receipt/cutting-item/<int:cutting_item_id>/receive/",
        views.receive_fabric_item_by_cutting_item,
        name="receive_fabric_item_by_cutting_item",
    ),
    path(
        "fabric-receipt/order/<int:order_id>/bulk-receive/",
        views.bulk_receive_fabric,
        name="bulk_receive_fabric",
    ),
    path(
        "api/fabric-receipt/order/<int:order_id>/status/",
        views.fabric_receipt_status_api,
        name="fabric_receipt_status_api",
    ),
    path(
        "cutting-orders/<int:cutting_order_id>/receive/",
        views.receive_cutting_order,
        name="receive_cutting_order",
    ),
    path(
        "fabric-receipt/<int:receipt_id>/detail/",
        views.FabricReceiptDetailView.as_view(),
        name="fabric_receipt_detail",
    ),
    path(
        "fabric-receipts/",
        views.FabricReceiptListView.as_view(),
        name="fabric_receipt_list",
    ),
    path(
        "pending-items-report/",
        views.PendingItemsReportView.as_view(),
        name="pending_items_report",
    ),
    path(
        "pending-items/auto-deliver/",
        views.AutoDeliverPendingItemsView.as_view(),
        name="auto_deliver_pending_items",
    ),
    path(
        "deliver-to-production-line/",
        views.deliver_to_production_line,
        name="deliver_to_production_line",
    ),
    path(
        "fix-manufacturing-items/",
        views.fix_manufacturing_order_items,
        name="fix_manufacturing_items",
    ),
    path(
        "cleanup-products-manufacturing/",
        views.cleanup_products_manufacturing_orders,
        name="cleanup_products_manufacturing",
    ),
    path(
        "product-receipt/", views.ProductReceiptView.as_view(), name="product_receipt"
    ),
    path(
        "create-product-receipt/",
        views.create_product_receipt,
        name="create_product_receipt",
    ),
    path(
        "product-receipts-list/",
        views.ProductReceiptsListView.as_view(),
        name="product_receipts_list",
    ),
    path(
        "create-manufacturing-receipt/",
        views.create_manufacturing_receipt,
        name="create_manufacturing_receipt",
    ),
    path(
        "get-cutting-data/<int:manufacturing_order_id>/",
        views.get_cutting_data,
        name="get_cutting_data",
    ),
    path(
        "receive-cutting-order/<int:cutting_order_id>/",
        views.receive_cutting_order_for_manufacturing,
        name="receive_cutting_order_for_manufacturing",
    ),
    path(
        "get-cutting-order-data/<int:cutting_order_id>/",
        views.get_cutting_order_data,
        name="get_cutting_order_data",
    ),
    path(
        "api/sync-items/<int:pk>/",
        views.sync_manufacturing_items,
        name="sync_mfg_items_api",
    ),
]
