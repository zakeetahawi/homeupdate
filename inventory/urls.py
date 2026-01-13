from django.urls import path

from . import api_views, views, views_variants, views_warehouse_cleanup
from .dashboard_view_append import optimized_product_detail
from .views import InventoryDashboardView
from .views_bulk import bulk_stock_update, download_excel_template, product_bulk_upload
from .views_bulk_reports import (
    bulk_upload_error_detail,
    bulk_upload_log_list,
    bulk_upload_report,
    latest_bulk_upload_report,
)
from .views_duplicate_check import (
    check_duplicates,
    merge_all_duplicates,
    merge_duplicate,
)
from .views_extended import (
    alert_ignore,
    alert_list,
    alert_resolve,
    alert_resolve_multiple,
    category_create,
    category_delete,
    category_list,
    category_update,
    purchase_order_create,
    purchase_order_list,
    supplier_create,
    supplier_list,
    warehouse_create,
    warehouse_delete,
    warehouse_detail,
    warehouse_list,
    warehouse_update,
)
from .views_reports import low_stock_report, report_list, stock_movement_report
from .views_stock_analysis import (
    product_stock_movement,
    stock_discrepancy_report,
    stock_movement_summary,
    warehouse_stock_analysis,
)
from .views_stock_transfer import (
    get_pending_transfers_for_warehouse,
    get_product_stock,
    get_similar_products,
    get_warehouse_products,
    stock_transfer_approve,
    stock_transfer_bulk,
    stock_transfer_bulk_create,
    stock_transfer_cancel,
    stock_transfer_delete,
    stock_transfer_detail,
    stock_transfer_edit,
    stock_transfer_list,
    stock_transfer_receive,
    stock_transfer_submit,
)
from .views_warehouse_locations import (
    warehouse_location_create,
    warehouse_location_delete,
    warehouse_location_detail,
    warehouse_location_list,
    warehouse_location_update,
)

app_name = "inventory"

urlpatterns = [
    # Dashboard as main page
    path("", InventoryDashboardView.as_view(), name="dashboard"),
    # Products
    path("products/", views.product_list, name="product_list"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("product/create/", views.product_create, name="product_create"),
    path("product/<int:pk>/update/", views.product_update, name="product_update"),
    path("product/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path(
        "product/<int:product_pk>/transaction/create/",
        views.transaction_create,
        name="transaction_create",
    ),
    path("products/search/", views.product_search_api, name="product_search_api"),
    path(
        "api/toggle-price-mode/",
        views.toggle_price_display_mode,
        name="toggle_price_mode",
    ),
    # Categories
    path("categories/", category_list, name="category_list"),
    path("category/create/", category_create, name="category_create"),
    path("category/<int:pk>/update/", category_update, name="category_update"),
    path("category/<int:pk>/delete/", category_delete, name="category_delete"),
    # Stock Transactions
    path(
        "transactions/", views.product_list, name="transaction_list"
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    # Stock Adjustments
    path(
        "adjustments/", views.product_list, name="adjustment_list"
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    # Purchase Orders
    path("purchase-orders/", purchase_order_list, name="purchase_order_list"),
    path("purchase-order/create/", purchase_order_create, name="purchase_order_create"),
    path(
        "purchase-order/<int:pk>/", views.product_list, name="purchase_order_detail"
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path(
        "purchase-order/<int:pk>/update/",
        views.product_list,
        name="purchase_order_update",
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path(
        "purchase-order/<int:pk>/delete/",
        views.product_list,
        name="purchase_order_delete",
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path(
        "purchase-order/<int:pk>/receive/",
        views.product_list,
        name="purchase_order_receive",
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    # Suppliers
    path("suppliers/", supplier_list, name="supplier_list"),
    path("supplier/create/", supplier_create, name="supplier_create"),
    path(
        "supplier/<int:pk>/update/", views.product_list, name="supplier_update"
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path(
        "supplier/<int:pk>/delete/", views.product_list, name="supplier_delete"
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path(
        "supplier/<int:pk>/", views.product_list, name="supplier_detail"
    ),  # مؤقتاً يستخدم نفس صفحة المنتجات
    # Warehouses
    path("warehouses/", warehouse_list, name="warehouse_list"),
    path("warehouse/create/", warehouse_create, name="warehouse_create"),
    path("warehouse/<int:pk>/update/", warehouse_update, name="warehouse_update"),
    path("warehouse/<int:pk>/delete/", warehouse_delete, name="warehouse_delete"),
    path("warehouse/<int:pk>/", warehouse_detail, name="warehouse_detail"),
    path(
        "warehouses/cleanup/",
        views_warehouse_cleanup.warehouse_cleanup_view,
        name="warehouse_cleanup",
    ),
    # Warehouse Locations
    path(
        "warehouse-locations/", warehouse_location_list, name="warehouse_location_list"
    ),
    path(
        "warehouse-location/create/",
        warehouse_location_create,
        name="warehouse_location_create",
    ),
    path(
        "warehouse-location/<int:pk>/update/",
        warehouse_location_update,
        name="warehouse_location_update",
    ),
    path(
        "warehouse-location/<int:pk>/delete/",
        warehouse_location_delete,
        name="warehouse_location_delete",
    ),
    path(
        "warehouse-location/<int:pk>/",
        warehouse_location_detail,
        name="warehouse_location_detail",
    ),
    # Reports
    path("reports/", report_list, name="report_list"),
    path("reports/low-stock/", low_stock_report, name="low_stock_report"),
    path(
        "reports/stock-movement/", stock_movement_report, name="stock_movement_report"
    ),
    path(
        "product/<int:product_id>/detail/",
        optimized_product_detail,
        name="optimized_product_detail",
    ),
    # Stock Alerts
    path("alerts/", alert_list, name="alert_list"),
    path("alert/<int:pk>/resolve/", alert_resolve, name="alert_resolve"),
    path("alert/<int:pk>/ignore/", alert_ignore, name="alert_ignore"),
    path(
        "alerts/resolve-multiple/",
        alert_resolve_multiple,
        name="alert_resolve_multiple",
    ),
    # Bulk Operations
    path("products/bulk-upload/", product_bulk_upload, name="product_bulk_upload"),
    path("stock/bulk-update/", bulk_stock_update, name="bulk_stock_update"),
    path(
        "download-excel-template/",
        download_excel_template,
        name="download_excel_template",
    ),
    # Bulk Upload Reports
    path("bulk-upload-logs/", bulk_upload_log_list, name="bulk_upload_log_list"),
    path(
        "bulk-upload-report/<int:log_id>/",
        bulk_upload_report,
        name="bulk_upload_report",
    ),
    path(
        "latest-bulk-upload-report/",
        latest_bulk_upload_report,
        name="latest_bulk_upload_report",
    ),
    path(
        "latest-bulk-upload-report/<str:upload_type>/",
        latest_bulk_upload_report,
        name="latest_bulk_upload_report_type",
    ),
    path(
        "bulk-upload-error/<int:error_id>/",
        bulk_upload_error_detail,
        name="bulk_upload_error_detail",
    ),
    # Duplicate Products Check & Merge
    path("check-duplicates/", check_duplicates, name="check_duplicates"),
    path("merge-duplicate/<int:product_id>/", merge_duplicate, name="merge_duplicate"),
    path("merge-all-duplicates/", merge_all_duplicates, name="merge_all_duplicates"),
    # API Endpoints
    path("api/product/<int:pk>/", views.product_api_detail, name="product_api_detail"),
    path("api/products/", views.product_api_list, name="product_api_list"),
    path(
        "api/product-autocomplete/",
        views.product_api_autocomplete,
        name="product_api_autocomplete",
    ),
    path("api/barcode-scan/", views.barcode_scan_api, name="barcode_scan_api"),
    # Stock Transfers
    path("stock-transfers/", stock_transfer_list, name="stock_transfer_list"),
    path(
        "stock-transfer/create/", stock_transfer_bulk, name="stock_transfer_create"
    ),  # النموذج الجديد
    path(
        "stock-transfer/create/bulk/",
        stock_transfer_bulk_create,
        name="stock_transfer_bulk_create",
    ),
    path(
        "stock-transfer/<int:pk>/", stock_transfer_detail, name="stock_transfer_detail"
    ),
    path(
        "stock-transfer/<int:pk>/edit/", stock_transfer_edit, name="stock_transfer_edit"
    ),
    path(
        "stock-transfer/<int:pk>/submit/",
        stock_transfer_submit,
        name="stock_transfer_submit",
    ),
    path(
        "stock-transfer/<int:pk>/approve/",
        stock_transfer_approve,
        name="stock_transfer_approve",
    ),
    path(
        "stock-transfer/<int:pk>/receive/",
        stock_transfer_receive,
        name="stock_transfer_receive",
    ),
    path(
        "stock-transfer/<int:pk>/cancel/",
        stock_transfer_cancel,
        name="stock_transfer_cancel",
    ),
    path(
        "stock-transfer/<int:pk>/delete/",
        stock_transfer_delete,
        name="stock_transfer_delete",
    ),
    # Stock Analysis
    path(
        "product/<int:product_id>/stock-movement/",
        product_stock_movement,
        name="product_stock_movement",
    ),
    path(
        "warehouse/<int:warehouse_id>/stock-analysis/",
        warehouse_stock_analysis,
        name="warehouse_stock_analysis",
    ),
    path(
        "stock-movement-summary/", stock_movement_summary, name="stock_movement_summary"
    ),
    path(
        "stock-discrepancy-report/",
        stock_discrepancy_report,
        name="stock_discrepancy_report",
    ),
    # ==================== Product Variants System ====================
    # Base Products
    path("base-products/", views_variants.base_product_list, name="base_product_list"),
    path(
        "base-product/create/",
        views_variants.base_product_create,
        name="base_product_create",
    ),
    path(
        "base-product/<int:pk>/",
        views_variants.base_product_detail,
        name="base_product_detail",
    ),
    path(
        "base-product/<int:pk>/update/",
        views_variants.base_product_update,
        name="base_product_update",
    ),
    path(
        "base-product/<int:pk>/delete/",
        views_variants.base_product_delete,
        name="base_product_delete",
    ),
    path(
        "base-product/<int:pk>/label-card/",
        views_variants.product_label_card,
        name="base_product_label_card",
    ),
    # Variants
    path(
        "base-product/<int:base_product_id>/variant/create/",
        views_variants.variant_create,
        name="variant_create",
    ),
    path(
        "base-product/<int:base_product_id>/variants/quick-create/",
        views_variants.quick_variants_create,
        name="quick_variants_create",
    ),
    path("variant/<int:pk>/", views_variants.variant_detail, name="variant_detail"),
    path(
        "variant/<int:pk>/update/", views_variants.variant_update, name="variant_update"
    ),
    path(
        "variant/<int:pk>/delete/", views_variants.variant_delete, name="variant_delete"
    ),
    # Variant Pricing
    path(
        "base-product/<int:base_product_id>/bulk-price-update/",
        views_variants.bulk_price_update,
        name="bulk_price_update",
    ),
    path(
        "variant/<int:pk>/update-price/",
        views_variants.update_variant_price,
        name="update_variant_price",
    ),
    path(
        "variant/<int:pk>/reset-price/",
        views_variants.reset_variant_price,
        name="reset_variant_price",
    ),
    # Variant Stock
    path(
        "variant/<int:pk>/stock-update/",
        views_variants.variant_stock_update,
        name="variant_stock_update",
    ),
    path(
        "variant/<int:pk>/stock-transfer/",
        views_variants.variant_stock_transfer,
        name="variant_stock_transfer",
    ),
    # Colors
    path("colors/", views_variants.color_list, name="color_list"),
    path("color/create/", views_variants.color_create, name="color_create"),
    path("color/<int:pk>/update/", views_variants.color_update, name="color_update"),
    path("color/<int:pk>/delete/", views_variants.color_delete, name="color_delete"),
    # Migration
    path("migrate-products/", views_variants.migrate_products, name="migrate_products"),
    path(
        "migrate-products/phase1/", views_variants.migrate_phase1, name="migrate_phase1"
    ),
    path(
        "migrate-products/phase2/confirm/",
        views_variants.migrate_phase2_confirm,
        name="migrate_phase2_confirm",
    ),
    path(
        "migrate-products/phase2/", views_variants.migrate_phase2, name="migrate_phase2"
    ),
    path(
        "migrate-products/phase3/confirm/",
        views_variants.migrate_phase3_confirm,
        name="migrate_phase3_confirm",
    ),
    path(
        "migrate-products/phase3/", views_variants.migrate_phase3, name="migrate_phase3"
    ),
    # Variants API
    path(
        "api/base-product/<int:pk>/variants/",
        views_variants.api_base_product_variants,
        name="api_base_product_variants",
    ),
    path(
        "api/variant/<int:pk>/stock/",
        views_variants.api_variant_stock,
        name="api_variant_stock",
    ),
    path(
        "api/variants/search/",
        views_variants.api_search_variants,
        name="api_search_variants",
    ),
    # API Endpoints
    path(
        "api/warehouse-products/", get_warehouse_products, name="api_warehouse_products"
    ),
    path("api/product-stock/", get_product_stock, name="api_product_stock"),
    path("api/similar-products/", get_similar_products, name="api_similar_products"),
    path(
        "api/warehouse/pending-transfers/",
        get_pending_transfers_for_warehouse,
        name="api_pending_transfers",
    ),
    # Real-time API Endpoints
    path(
        "api/dashboard-stats/",
        api_views.dashboard_stats_api,
        name="dashboard_stats_api",
    ),
    path(
        "api/product/<int:product_id>/stock-info/",
        api_views.product_stock_info_api,
        name="product_stock_info_api",
    ),
    path("api/stock-alerts/", api_views.stock_alerts_api, name="stock_alerts_api"),
    path(
        "api/alert/<int:alert_id>/resolve/",
        api_views.resolve_alert_api,
        name="resolve_alert_api",
    ),
    path(
        "api/warehouse-stock-summary/",
        api_views.warehouse_stock_summary_api,
        name="warehouse_stock_summary_api",
    ),
    path(
        "api/warehouse/<int:warehouse_id>/stock-summary/",
        api_views.warehouse_stock_summary_api,
        name="warehouse_stock_summary_id_api",
    ),
    path(
        "api/category-stock-analysis/",
        api_views.category_stock_analysis_api,
        name="category_stock_analysis_api",
    ),
    path(
        "api/notifications/count/",
        api_views.get_stock_notifications_count,
        name="stock_notifications_count_api",
    ),
    # Advanced Analytics API Endpoints
    path(
        "api/inventory-value-report/",
        api_views.inventory_value_report_api,
        name="inventory_value_report_api",
    ),
    path(
        "api/stock-turnover-analysis/",
        api_views.stock_turnover_analysis_api,
        name="stock_turnover_analysis_api",
    ),
    path(
        "api/reorder-recommendations/",
        api_views.reorder_recommendations_api,
        name="reorder_recommendations_api",
    ),
    # Bulk Upload API Endpoints
    path(
        "api/bulk-upload/<int:log_id>/status/",
        api_views.bulk_upload_status_api,
        name="bulk_upload_status_api",
    ),
    path(
        "api/warehouse/manage/",
        api_views.manage_warehouse_api,
        name="manage_warehouse_api",
    ),
    # Stock Transfers API
    path(
        "api/global/pending-transfers/",
        api_views.pending_transfers_api,
        name="pending_transfers_api",
    ),
    # QR Code Generation APIs
    path(
        "api/product/<int:pk>/generate-qr/",
        views.generate_single_qr_api,
        name="generate_single_qr_api",
    ),
    path("api/generate-all-qr/", views.generate_all_qr_api, name="generate_all_qr_api"),
    path("api/generate-qr-pdf/", views.generate_qr_pdf_api, name="generate_qr_pdf_api"),
    # Excel Export
    path(
        "products/export-excel/",
        views.export_products_excel,
        name="export_products_excel",
    ),
]
