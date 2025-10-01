from django.urls import path
from . import views
from .views import InventoryDashboardView
from .dashboard_view_append import optimized_product_detail
from .views_extended import (
    category_list, category_create, category_update, category_delete,
    warehouse_list, warehouse_create, warehouse_update, warehouse_delete, warehouse_detail,
    supplier_list, supplier_create,
    purchase_order_list, purchase_order_create,
    alert_list, alert_resolve, alert_ignore, alert_resolve_multiple
)
from .views_warehouse_locations import (
    warehouse_location_list, warehouse_location_create, warehouse_location_update,
    warehouse_location_delete, warehouse_location_detail
)
from .views_reports import (
    report_list, low_stock_report, stock_movement_report
)
from .views_bulk import (
    product_bulk_upload, bulk_stock_update, download_excel_template
)
from .views_stock_transfer import (
    stock_transfer_list, stock_transfer_create, stock_transfer_detail,
    stock_transfer_edit, stock_transfer_submit, stock_transfer_approve,
    stock_transfer_receive, stock_transfer_cancel, stock_transfer_delete
)
from .views_stock_analysis import (
    product_stock_movement, warehouse_stock_analysis,
    stock_movement_summary, stock_discrepancy_report
)

app_name = 'inventory'

urlpatterns = [
    # Dashboard as main page
    path('', InventoryDashboardView.as_view(), name='dashboard'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/create/', views.product_create, name='product_create'),
    path('product/<int:pk>/update/', views.product_update, name='product_update'),
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('product/<int:product_pk>/transaction/create/', views.transaction_create, name='transaction_create'),
    path('products/search/', views.product_search_api, name='product_search_api'),

    # Categories
    path('categories/', category_list, name='category_list'),
    path('category/create/', category_create, name='category_create'),
    path('category/<int:pk>/update/', category_update, name='category_update'),
    path('category/<int:pk>/delete/', category_delete, name='category_delete'),

    # Stock Transactions
    path('transactions/', views.product_list, name='transaction_list'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Stock Adjustments
    path('adjustments/', views.product_list, name='adjustment_list'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Purchase Orders
    path('purchase-orders/', purchase_order_list, name='purchase_order_list'),
    path('purchase-order/create/', purchase_order_create, name='purchase_order_create'),
    path('purchase-order/<int:pk>/', views.product_list, name='purchase_order_detail'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('purchase-order/<int:pk>/update/', views.product_list, name='purchase_order_update'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('purchase-order/<int:pk>/delete/', views.product_list, name='purchase_order_delete'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('purchase-order/<int:pk>/receive/', views.product_list, name='purchase_order_receive'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Suppliers
    path('suppliers/', supplier_list, name='supplier_list'),
    path('supplier/create/', supplier_create, name='supplier_create'),
    path('supplier/<int:pk>/update/', views.product_list, name='supplier_update'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('supplier/<int:pk>/delete/', views.product_list, name='supplier_delete'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('supplier/<int:pk>/', views.product_list, name='supplier_detail'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Warehouses
    path('warehouses/', warehouse_list, name='warehouse_list'),
    path('warehouse/create/', warehouse_create, name='warehouse_create'),
    path('warehouse/<int:pk>/update/', warehouse_update, name='warehouse_update'),
    path('warehouse/<int:pk>/delete/', warehouse_delete, name='warehouse_delete'),
    path('warehouse/<int:pk>/', warehouse_detail, name='warehouse_detail'),

    # Warehouse Locations
    path('warehouse-locations/', warehouse_location_list, name='warehouse_location_list'),
    path('warehouse-location/create/', warehouse_location_create, name='warehouse_location_create'),
    path('warehouse-location/<int:pk>/update/', warehouse_location_update, name='warehouse_location_update'),
    path('warehouse-location/<int:pk>/delete/', warehouse_location_delete, name='warehouse_location_delete'),
    path('warehouse-location/<int:pk>/', warehouse_location_detail, name='warehouse_location_detail'),

    # Reports
    path('reports/', report_list, name='report_list'),
    path('reports/low-stock/', low_stock_report, name='low_stock_report'),
    path('reports/stock-movement/', stock_movement_report, name='stock_movement_report'),
    path('product/<int:product_id>/detail/', optimized_product_detail, name='optimized_product_detail'),

    # Stock Alerts
    path('alerts/', alert_list, name='alert_list'),
    path('alert/<int:pk>/resolve/', alert_resolve, name='alert_resolve'),
    path('alert/<int:pk>/ignore/', alert_ignore, name='alert_ignore'),
    path('alerts/resolve-multiple/', alert_resolve_multiple, name='alert_resolve_multiple'),

    # Bulk Operations
    path('products/bulk-upload/', product_bulk_upload, name='product_bulk_upload'),
    path('stock/bulk-update/', bulk_stock_update, name='bulk_stock_update'),
    path('download-excel-template/', download_excel_template, name='download_excel_template'),

    # API Endpoints
    path('api/product/<int:pk>/', views.product_api_detail, name='product_api_detail'),
    path('api/products/', views.product_api_list, name='product_api_list'),
    path('api/product-autocomplete/', views.product_api_autocomplete, name='product_api_autocomplete'),

    # Stock Transfers
    path('stock-transfers/', stock_transfer_list, name='stock_transfer_list'),
    path('stock-transfer/create/', stock_transfer_create, name='stock_transfer_create'),
    path('stock-transfer/<int:pk>/', stock_transfer_detail, name='stock_transfer_detail'),
    path('stock-transfer/<int:pk>/edit/', stock_transfer_edit, name='stock_transfer_edit'),
    path('stock-transfer/<int:pk>/submit/', stock_transfer_submit, name='stock_transfer_submit'),
    path('stock-transfer/<int:pk>/approve/', stock_transfer_approve, name='stock_transfer_approve'),
    path('stock-transfer/<int:pk>/receive/', stock_transfer_receive, name='stock_transfer_receive'),
    path('stock-transfer/<int:pk>/cancel/', stock_transfer_cancel, name='stock_transfer_cancel'),
    path('stock-transfer/<int:pk>/delete/', stock_transfer_delete, name='stock_transfer_delete'),

    # Stock Analysis
    path('product/<int:product_id>/stock-movement/', product_stock_movement, name='product_stock_movement'),
    path('warehouse/<int:warehouse_id>/stock-analysis/', warehouse_stock_analysis, name='warehouse_stock_analysis'),
    path('stock-movement-summary/', stock_movement_summary, name='stock_movement_summary'),
    path('stock-discrepancy-report/', stock_discrepancy_report, name='stock_discrepancy_report'),
]

